import 'package:mobile_app/features/risk_profile/data/risk_repository.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_assessment.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_profile.dart';
import 'package:mobile_app/features/risk_profile/domain/service_status.dart';

/// Shaped like the real C3 answer for the higher-risk preset (contract 0.1), including
/// the researcher-only `debug` block, so tests can prove patient screens hide it.
Map<String, dynamic> okJson({String band = 'High', Map<String, dynamic>? debug}) => {
      'status': 'ok',
      'disclaimer': 'Statistical risk estimate for self-management support. '
          'This is not a diagnosis and does not replace medical advice.',
      'risk_category': band,
      if (band == 'High') 'referral': 'Please arrange a blood test and a check-up.',
      'feature_set': 'with_glucose',
      'model_used': 'random_forest',
      'model_version': '2026-10-10',
      'data_complete': false,
      'imputed_fields': ['pulse_rate'],
      'explanation': {
        'shap': [
          {
            'feature': 'glucose_mmol',
            'readable': 'blood glucose',
            'factor_type': 'modifiable',
            'value': 9.8,
            'shap': 0.31,
            'direction': 'increases risk',
          },
          {
            'feature': 'age',
            'readable': 'age',
            'factor_type': 'not modifiable',
            'value': 58.0,
            'shap': 0.08,
            'direction': 'increases risk',
          },
          {
            'feature': 'bmi',
            'readable': 'body mass index (BMI)',
            'factor_type': 'modifiable',
            'value': 27.8,
            'shap': -0.02,
            'direction': 'decreases risk',
          },
        ],
        'lime': [
          {
            'rule': 'glucose_mmol > 6.10',
            'feature': 'glucose_mmol',
            'readable': 'blood glucose',
            'factor_type': 'modifiable',
            'value': 9.8,
            'weight': 0.28,
            'direction': 'increases risk',
          },
        ],
        'lime_fidelity': 0.6888,
        'agreement': {
          'shap_top': ['age', 'bmi', 'glucose_mmol', 'hypertensive', 'pulse_rate'],
          'lime_top': ['age', 'bmi', 'diastolic_bp', 'glucose_mmol', 'hypertensive'],
          'shared': ['age', 'bmi', 'glucose_mmol', 'hypertensive'],
          'overlap_ratio': 0.8,
          'meets_target': true,
        },
        'explanation_quality': 'consistent',
        'explanation_text': 'Your estimated risk band is High.',
      },
      if (debug != null) 'debug': debug,
    };

const debugJson = {
  'risk_probability': 0.5657,
  'risk_percent': 56.6,
  'thresholds': {'low_max': 0.0259, 'high_min': 0.1345},
};

/// Repository with scripted answers: each call takes the next item (a JSON map, or an
/// exception to throw).
class FakeRiskRepository implements RiskRepository {
  FakeRiskRepository(this.answers, {this.modelLoaded = true, this.statusError});

  final List<Object> answers;
  final bool modelLoaded;

  /// When set, status() throws it (gateway unreachable).
  Exception? statusError;
  int statusCalls = 0;
  final List<RiskProfile> sent = [];

  @override
  bool get isDemoData => false;

  @override
  Future<RiskAssessment> assess(RiskProfile profile) async {
    sent.add(profile);
    final answer = answers.length > 1 ? answers.removeAt(0) : answers.first;
    if (answer is Exception) throw answer;
    return RiskAssessment.fromJson(answer as Map<String, dynamic>);
  }

  @override
  Future<ServiceStatus> status() async {
    statusCalls += 1;
    if (statusError != null) throw statusError!;
    return ServiceStatus(modelLoaded: modelLoaded);
  }
}
