/// Request and response models for the C2 glucose forecast.
///
/// Mirrors `contracts/glucose_forecast/contract.md` (endpoint
/// `POST /api/v1/glucose/forecast`) and the C2 schemas in `schemas.py`.
library;

/// Number of forecast points the model returns (15-minute steps to 240 minutes).
const int forecastPointCount = 16;

class GlucoseForecastRequest {
  const GlucoseForecastRequest({
    required this.premealGlucose,
    required this.calories,
    required this.carbs,
    required this.protein,
    required this.fat,
    required this.fiber,
  });

  /// Current pre-meal glucose, mg/dL.
  final double premealGlucose;

  /// Meal energy, kcal.
  final double calories;

  /// Meal carbohydrates, g.
  final double carbs;

  /// Meal protein, g.
  final double protein;

  /// Meal fat, g.
  final double fat;

  /// Meal fibre, g.
  final double fiber;

  Map<String, Object> toJson() => {
        'premeal_glucose': premealGlucose,
        'calories': calories,
        'carbs': carbs,
        'protein': protein,
        'fat': fat,
        'fiber': fiber,
      };
}

class GlucoseForecast {
  const GlucoseForecast({
    required this.predictions,
    required this.horizonMinutes,
    required this.unit,
    required this.modelName,
    required this.modelVersion,
    required this.disclaimer,
  });

  /// Predicted glucose at each horizon, mg/dL. Index matches [horizonMinutes].
  final List<double> predictions;

  /// Forecast horizons in minutes after the meal: 15, 30, ..., 240.
  final List<int> horizonMinutes;

  final String unit;
  final String modelName;
  final String modelVersion;
  final String disclaimer;

  /// Index of the highest predicted value (the earliest one if several are equal).
  int get peakIndex {
    var best = 0;
    for (var i = 1; i < predictions.length; i++) {
      if (predictions[i] > predictions[best]) best = i;
    }
    return best;
  }

  /// Highest predicted glucose, mg/dL.
  double get peakGlucose => predictions[peakIndex];

  /// Minutes after the meal at which [peakGlucose] is predicted.
  int get peakMinutes => horizonMinutes[peakIndex];

  /// Parses and checks a response body. Throws [FormatException] if the body
  /// does not match the contract, so the UI never shows partial or made-up data.
  factory GlucoseForecast.fromJson(Map<String, dynamic> json) {
    final predictions = _readNumbers(json, 'predictions');
    final horizons =
        _readNumbers(json, 'horizon_minutes').map((v) => v.round()).toList();
    final unit = _readString(json, 'unit');
    final modelName = _readString(json, 'model_name');
    final modelVersion = _readString(json, 'model_version');
    final disclaimer = _readString(json, 'disclaimer');

    if (predictions.length != forecastPointCount) {
      throw FormatException(
          'Expected $forecastPointCount predictions, got ${predictions.length}.');
    }
    if (horizons.length != forecastPointCount) {
      throw FormatException(
          'Expected $forecastPointCount horizons, got ${horizons.length}.');
    }
    if (unit != 'mg/dL') {
      throw FormatException('Unexpected unit: $unit.');
    }

    return GlucoseForecast(
      predictions: predictions,
      horizonMinutes: horizons,
      unit: unit,
      modelName: modelName,
      modelVersion: modelVersion,
      disclaimer: disclaimer,
    );
  }

  static List<double> _readNumbers(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is! List) {
      throw FormatException('Field "$key" must be a list.');
    }
    return value.map((item) {
      if (item is! num || !item.isFinite) {
        throw FormatException('Field "$key" contains a non-numeric value.');
      }
      return item.toDouble();
    }).toList();
  }

  static String _readString(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is! String) {
      throw FormatException('Field "$key" must be a string.');
    }
    return value;
  }
}

/// Form validation rules. These match the C2 backend (`schemas.py`): glucose
/// must be a positive finite number and nutrition values non-negative. The
/// contract leaves further domain limits open, so none are added here.
String? validatePremealGlucose(String? input) {
  final value = _parseFinite(input);
  if (value == null) {
    return input == null || input.trim().isEmpty
        ? 'Enter your pre-meal glucose.'
        : 'Enter a valid number.';
  }
  if (value <= 0) {
    return 'Pre-meal glucose must be greater than 0 mg/dL.';
  }
  return null;
}

String? validateNutrient(String? input, {required String label}) {
  final value = _parseFinite(input);
  if (value == null) {
    return input == null || input.trim().isEmpty
        ? 'Enter $label.'
        : 'Enter a valid number.';
  }
  if (value < 0) {
    return '$label cannot be negative.';
  }
  return null;
}

double? _parseFinite(String? input) {
  if (input == null) return null;
  final value = double.tryParse(input.trim());
  if (value == null || !value.isFinite) return null;
  return value;
}
