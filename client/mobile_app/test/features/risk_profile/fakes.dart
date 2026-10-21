import 'package:mobile_app/features/risk_profile/data/risk_repository.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_assessment.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_profile.dart';
import 'package:mobile_app/features/risk_profile/domain/server_history.dart';
import 'package:mobile_app/features/risk_profile/domain/service_status.dart';

/// Shaped like the real C3 answer for the higher-risk preset (contract 0.2), including
/// the DHS, recommendations and the researcher-only `debug` block, so tests can prove
/// patient screens hide it.
Map<String, dynamic> okJson({
  String band = 'High',
  Map<String, dynamic>? debug,
  double dhs = 58.2,
}) =>
    {
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
        // Wording exactly as the real C3 server sends it (ml/explain.py), so the
        // removed-terms test catches any server text that reaches a patient screen.
        'explanation_quality':
            'check: SHAP and LIME agree weakly or the LIME fit is poor; treat factors with care',
        'explanation_text': 'Your estimated risk band is High. Factors you can work on that raised '
            "it: blood glucose. These are contributions to the model's estimate, not medical "
            'causes. Discuss any concerns with a healthcare professional.',
      },
      'dhs': {
        'score': dhs,
        'today_score': dhs,
        'components': {
          'stable': 0.554,
          'behaviour': 0.625,
          'glycemic': null,
          'uncertainty': 0.0,
        },
        'items': [
          {
            'factor': 'physical_activity',
            'label': 'Physical activity',
            'value': 'low',
            'item_score': 0.0,
            'group': 'behaviour',
          },
          {
            'factor': 'cholesterol_level',
            'label': 'Cholesterol',
            'value': 'borderline_high',
            'item_score': 0.5,
            'group': 'clinical marker',
          },
          {
            'factor': 'smoker',
            'label': 'Smoking',
            'value': 0,
            'item_score': 1.0,
            'group': 'behaviour',
          },
        ],
        'provisional': true,
        'note': 'Provisional Diabetic Health Score: weights pending clinician review.',
      },
      'recommendations': [
        {
          'id': 'activity',
          'factor': 'physical_activity',
          'title': 'Increase physical activity',
          'trigger': 'Physical activity answered as low or moderate',
          'raised_estimate': false,
          'window': 'your latest answers',
          'action': 'Build up step by step to at least 150 minutes of moderate activity a week.',
          'current': 'Low activity',
          'target': '150 min of moderate activity per week (WHO guideline)',
          'review_status': 'provisional - pending clinician review',
        },
        {
          'id': 'cholesterol',
          'factor': 'cholesterol_level',
          'title': 'Review your cholesterol with your doctor',
          'trigger': "Body mass index raised the model's estimate",
          'raised_estimate': false,
          'window': 'your latest answers',
          'action': 'Choose fewer fried and fatty foods.',
          'seek_care': 'Discuss your cholesterol result with your doctor.',
          'review_status': 'provisional - pending clinician review',
        },
      ],
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
  FakeRiskRepository(
    this.answers, {
    this.modelLoaded = true,
    this.statusError,
    this.serverHistory = const [],
    this.historyError,
  });

  /// Saved results the fake server returns, or an error to throw instead.
  List<ServerHistoryItem> serverHistory;
  Exception? historyError;
  int deleteCalls = 0;

  /// How many what-if previews were sent without saving.
  int unsaved = 0;

  final List<Object> answers;
  final bool modelLoaded;

  /// When set, status() throws it (gateway unreachable).
  Exception? statusError;
  int statusCalls = 0;
  final List<RiskProfile> sent = [];

  @override
  bool get isDemoData => false;

  @override
  Future<RiskAssessment> assess(RiskProfile profile, {bool save = true}) async {
    sent.add(profile);
    if (!save) unsaved += 1;
    final answer = answers.length > 1 ? answers.removeAt(0) : answers.first;
    if (answer is Exception) throw answer;
    return RiskAssessment.fromJson(answer as Map<String, dynamic>);
  }

  @override
  Future<List<ServerHistoryItem>> history() async {
    if (historyError != null) throw historyError!;
    return serverHistory;
  }

  @override
  Future<int> deleteMyRecords() async {
    deleteCalls += 1;
    final count = serverHistory.length;
    serverHistory = const [];
    return count;
  }

  @override
  Future<ServiceStatus> status() async {
    statusCalls += 1;
    if (statusError != null) throw statusError!;
    return ServiceStatus(modelLoaded: modelLoaded);
  }
}
