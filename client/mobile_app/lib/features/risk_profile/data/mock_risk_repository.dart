// UNVERIFIED: written without the Flutter SDK; run `flutter analyze` before use.

import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import 'risk_repository.dart';

/// Demo-only repository. Screens must show a visible "Demo data" banner when it is used.
///
/// It returns one fixed answer shaped like the contract example, whatever the input.
/// It runs no model and applies no rules, so no model logic lives in the app.
class MockRiskRepository implements RiskRepository {
  const MockRiskRepository();

  @override
  bool get isDemoData => true;

  @override
  Future<RiskAssessment> assess(RiskProfile profile) async =>
      RiskAssessment.fromJson(_demoHighResult);

  static const String _disclaimer =
      'Statistical risk estimate for self-management support. '
      'This is not a diagnosis and does not replace medical advice.';

  static const Map<String, dynamic> _demoHighResult = {
    'status': 'ok',
    'disclaimer': _disclaimer,
    'risk_category': 'High',
    'referral': 'DEMO DATA. Because the estimate is in the High band, please arrange a '
        'blood test and a check-up with a doctor or a diabetes clinic.',
    'feature_set': 'with_glucose',
    'model_used': 'demo',
    'model_version': 'demo',
    'data_complete': true,
    'imputed_fields': <String>[],
    'explanation': {
      'shap': [
        {
          'feature': 'hypertensive',
          'readable': 'diagnosed high blood pressure',
          'factor_type': 'medical history',
          'value': 1.0,
          'shap': 0.2646,
          'direction': 'increases risk',
        },
      ],
      'lime': [
        {
          'rule': 'hypertensive > 0.00',
          'feature': 'hypertensive',
          'readable': 'diagnosed high blood pressure',
          'factor_type': 'medical history',
          'value': 1.0,
          'weight': 0.2863,
          'direction': 'increases risk',
        },
      ],
      'lime_fidelity': 0.6888,
      'agreement': {
        'shap_top': ['hypertensive'],
        'lime_top': ['hypertensive'],
        'shared': ['hypertensive'],
        'overlap_ratio': 1.0,
        'meets_target': true,
      },
      'explanation_quality': 'consistent',
      'explanation_text': 'DEMO DATA. Your estimated risk band is High. These are '
          "contributions to the model's estimate, not medical causes.",
    },
  };
}
