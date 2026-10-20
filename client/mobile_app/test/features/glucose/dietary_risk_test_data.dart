/// Synthetic `/api/v1/glucose/dietary-risk` response bodies for tests.
library;

/// A contract-shaped body. [estimate] is used only when [available] is true.
Map<String, dynamic> dietaryRiskJson(
        {bool available = true, bool estimate = true}) =>
    {
      'predictions': List<double>.generate(16, (i) => 120.0 + 5 * i),
      'horizon_minutes': List<int>.generate(16, (i) => (i + 1) * 15),
      'unit': 'mg/dL',
      'trajectory_features': <String, dynamic>{
        'predicted_peak_glucose': 195.0,
        'predicted_peak_minutes': 240,
        'peak_change_from_premeal': 85.0,
        'max_rise': 85.0,
        'max_rise_rate': 0.67,
        'predicted_iauc': 10500.0,
      },
      'response_indicator': <String, dynamic>{
        'name': 'above_180_within_4h',
        'status': available ? 'available' : 'unavailable',
        'estimated_above_180': available ? estimate : null,
        'definition': 'Test definition.',
        'evaluation_note': available ? 'Synthetic evaluation note.' : null,
        'model_name': available ? 'XGBoost' : null,
        'model_version': available ? 'xgb-test' : null,
      },
      'forecast_model_name': 'GRU',
      'forecast_model_version': 'gru-test',
      'disclaimer': 'Research estimates, not a medical diagnosis.',
    };
