import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/risk_profile/data/mock_risk_repository.dart';
import 'package:mobile_app/features/risk_profile/data/risk_api.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_assessment.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_presets.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_profile.dart';

void main() {
  test('profile JSON uses contract field names and leaves out unanswered fields', () {
    const profile = RiskProfile(age: 58, bmi: 27.8, systolicBp: 150, diastolicBp: 95);

    expect(profile.toJson(), {
      'schema_version': '0.2',
      'age': 58.0,
      'bmi': 27.8,
      'systolic_bp': 150.0,
      'diastolic_bp': 95.0,
    });
  });

  test('ok assessment parses band, referral and explanation', () {
    final assessment = RiskAssessment.fromJson({
      'status': 'ok',
      'disclaimer': 'This is not a diagnosis.',
      'risk_category': 'High',
      'referral': 'Please see a doctor.',
      'data_complete': true,
      'imputed_fields': <String>[],
      'explanation': {
        'shap': [
          {
            'feature': 'bmi',
            'readable': 'body mass index (BMI)',
            'factor_type': 'modifiable',
            'value': 27.8,
            'shap': 0.03,
            'direction': 'increases risk',
          },
        ],
        'lime': <Map<String, dynamic>>[],
        'lime_fidelity': 0.69,
        'agreement': {
          'shap_top': ['bmi'],
          'lime_top': <String>[],
          'shared': <String>[],
          'overlap_ratio': 0.0,
          'meets_target': false,
        },
        'explanation_quality': 'check',
        'explanation_text': 'Your estimated risk band is High.',
      },
    });

    expect(assessment.status, AssessmentStatus.ok);
    expect(assessment.band, RiskBand.high);
    expect(assessment.referral, 'Please see a doctor.');
    expect(assessment.explanation!.shap.single.feature, 'bmi');
  });

  test('insufficient_data has no band and lists the missing fields', () {
    final assessment = RiskAssessment.fromJson({
      'status': 'insufficient_data',
      'disclaimer': 'This is not a diagnosis.',
      'missing_critical_fields': ['systolic_bp', 'diastolic_bp'],
    });

    expect(assessment.status, AssessmentStatus.insufficientData);
    expect(assessment.band, isNull);
    expect(assessment.missingCriticalFields, ['systolic_bp', 'diastolic_bp']);
  });

  test('mock repository is flagged as demo data', () async {
    const repository = MockRiskRepository();
    final assessment = await repository.assess(const RiskProfile());

    expect(repository.isDemoData, isTrue);
    expect(assessment.status, AssessmentStatus.ok);
  });

  test('presets send exactly the Python examples (ml/predict.py) to the model', () {
    // The model fields equal EXAMPLE_PATIENT and LOW_RISK_PATIENT from the server code;
    // the lifestyle answers only feed the DHS and the recommendations.
    const lifestyle = {
      'physical_activity',
      'smoker',
      'medication_adherence',
      'cholesterol_level',
      'kidney_disease',
      'liver_disease',
      'weight_change_kg',
    };
    Map<String, Object?> modelPart(Map<String, Object?> json) =>
        Map.fromEntries(json.entries.where((e) => !lifestyle.contains(e.key)));

    expect(higherRiskPreset.profile.toJson()['physical_activity'], 'low');
    expect(modelPart(higherRiskPreset.profile.toJson()), {
      'schema_version': '0.2',
      'age': 58.0,
      'sex_male': 1,
      'bmi': 27.8,
      'systolic_bp': 150.0,
      'diastolic_bp': 95.0,
      'pulse_rate': 84.0,
      'glucose_mmol': 9.8,
      'family_history_diabetes': 1,
      'family_history_hypertension': 1,
      'hypertensive': 1,
      'cardiovascular_disease': 0,
      'stroke': 0,
    });
    expect(modelPart(lowerRiskPreset.profile.toJson()), {
      'schema_version': '0.2',
      'age': 29.0,
      'sex_male': 0,
      'bmi': 21.5,
      'systolic_bp': 112.0,
      'diastolic_bp': 72.0,
      'pulse_rate': 72.0,
      'glucose_mmol': 5.4,
      'family_history_diabetes': 0,
      'family_history_hypertension': 0,
      'hypertensive': 0,
      'cardiovascular_disease': 0,
      'stroke': 0,
    });
    expect(missingBmiPreset.profile.toJson().containsKey('bmi'), isFalse);
  });

  test('DHS and recommendations are parsed', () {
    final assessment = RiskAssessment.fromJson({
      'status': 'ok',
      'disclaimer': 'This is not a diagnosis.',
      'risk_category': 'Moderate',
      'dhs': {
        'score': 64.5,
        'today_score': 70.0,
        'previous_score': 59.0,
        'components': {'stable': 0.6, 'behaviour': 0.8, 'glycemic': null, 'uncertainty': 0.0},
        'items': [
          {
            'factor': 'smoker',
            'label': 'Smoking',
            'value': 0,
            'item_score': 1.0,
            'group': 'behaviour',
          },
        ],
        'provisional': true,
        'note': 'Provisional.',
      },
      'recommendations': [
        {
          'id': 'activity',
          'factor': 'physical_activity',
          'title': 'Increase physical activity',
          'trigger': 'Physical activity answered as low or moderate',
          'raised_estimate': false,
          'window': 'your latest answers',
          'action': 'Walk more.',
          'review_status': 'provisional - pending clinician review',
        },
      ],
    });
    expect(assessment.dhs!.score, 64.5);
    expect(assessment.dhs!.previousScore, 59.0);
    expect(assessment.dhs!.items.single.itemScore, 1.0);
    expect(assessment.dhs!.provisional, isTrue);
    expect(assessment.recommendations.single.seekCare, isNull);
  });

  test('researcher-only debug block is parsed apart from the patient fields', () {
    final assessment = RiskAssessment.fromJson({
      'status': 'ok',
      'disclaimer': 'This is not a diagnosis.',
      'risk_category': 'High',
      'debug': {
        'risk_probability': 0.5657,
        'risk_percent': 56.6,
        'thresholds': {'low_max': 0.0259, 'high_min': 0.1345},
      },
    });
    expect(assessment.researcherInfo!.riskProbability, 0.5657);
    expect(assessment.researcherInfo!.thresholds['high_min'], 0.1345);
  });

  test('live API only targets the gateway route', () {
    expect(RiskApi().assessUri.path, '/api/v1/risk/assess');
    expect(RiskApi().isDemoData, isFalse);
  });
}
