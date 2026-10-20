/// Response models for the C2 post-meal response indicator.
///
/// Mirrors `contracts/dietary_risk/contract.md` (endpoint
/// `POST /api/v1/glucose/dietary-risk`) and the C2 schemas in `schemas.py`.
/// The request is the same as the forecast request ([GlucoseForecastRequest]).
library;

import 'glucose_models.dart';

/// Features of the predicted trajectory. Glucose in mg/dL, times in minutes.
class TrajectoryFeatures {
  const TrajectoryFeatures({
    required this.predictedPeakGlucose,
    required this.predictedPeakMinutes,
    required this.peakChangeFromPremeal,
    required this.maxRise,
    required this.maxRiseRate,
    required this.predictedIauc,
  });

  final double predictedPeakGlucose;
  final int predictedPeakMinutes;

  /// Predicted peak minus pre-meal glucose. Negative if every value is lower.
  final double peakChangeFromPremeal;

  /// Largest predicted increase from any earlier point. Never negative.
  final double maxRise;

  /// Steepest change between consecutive points, mg/dL per minute.
  final double maxRiseRate;

  /// Incremental area above pre-meal glucose, mg/dL x min.
  final double predictedIauc;

  factory TrajectoryFeatures.fromJson(Map<String, dynamic> json) {
    return TrajectoryFeatures(
      predictedPeakGlucose: _readNumber(json, 'predicted_peak_glucose'),
      predictedPeakMinutes: _readNumber(json, 'predicted_peak_minutes').round(),
      peakChangeFromPremeal: _readNumber(json, 'peak_change_from_premeal'),
      maxRise: _readNumber(json, 'max_rise'),
      maxRiseRate: _readNumber(json, 'max_rise_rate'),
      predictedIauc: _readNumber(json, 'predicted_iauc'),
    );
  }
}

/// The research-defined indicator `above_180_within_4h`. Not a diagnosis.
class ResponseIndicator {
  const ResponseIndicator({
    required this.available,
    required this.estimatedAbove180,
    required this.definition,
    required this.evaluationNote,
    required this.modelName,
    required this.modelVersion,
  });

  /// False when the server has no usable classifier. [estimatedAbove180] is then null.
  final bool available;
  final bool? estimatedAbove180;
  final String definition;
  final String? evaluationNote;
  final String? modelName;
  final String? modelVersion;

  factory ResponseIndicator.fromJson(Map<String, dynamic> json) {
    final name = _readString(json, 'name');
    if (name != 'above_180_within_4h') {
      throw FormatException('Unexpected indicator: $name.');
    }
    final status = _readString(json, 'status');
    final estimate = json['estimated_above_180'];
    final available = switch (status) {
      'available' => true,
      'unavailable' => false,
      _ => throw FormatException('Unexpected indicator status: $status.'),
    };
    // An estimate must be present exactly when the indicator is available.
    if (available ? estimate is! bool : estimate != null) {
      throw const FormatException(
          'Indicator estimate does not match its status.');
    }
    return ResponseIndicator(
      available: available,
      estimatedAbove180: estimate as bool?,
      definition: _readString(json, 'definition'),
      evaluationNote: _readOptionalString(json, 'evaluation_note'),
      modelName: _readOptionalString(json, 'model_name'),
      modelVersion: _readOptionalString(json, 'model_version'),
    );
  }
}

class DietaryRiskAssessment {
  const DietaryRiskAssessment({
    required this.predictions,
    required this.horizonMinutes,
    required this.unit,
    required this.features,
    required this.indicator,
    required this.forecastModelName,
    required this.forecastModelVersion,
    required this.disclaimer,
  });

  final List<double> predictions;
  final List<int> horizonMinutes;
  final String unit;
  final TrajectoryFeatures features;
  final ResponseIndicator indicator;
  final String forecastModelName;
  final String forecastModelVersion;
  final String disclaimer;

  /// Parses and checks a response body. Throws [FormatException] if the body
  /// does not match the contract, so the UI never shows partial or made-up data.
  factory DietaryRiskAssessment.fromJson(Map<String, dynamic> json) {
    final predictions = _readNumbers(json, 'predictions');
    final horizons =
        _readNumbers(json, 'horizon_minutes').map((v) => v.round()).toList();
    final unit = _readString(json, 'unit');
    if (predictions.length != forecastPointCount ||
        horizons.length != forecastPointCount) {
      throw const FormatException('Expected 16 predictions and horizons.');
    }
    if (unit != 'mg/dL') {
      throw FormatException('Unexpected unit: $unit.');
    }
    return DietaryRiskAssessment(
      predictions: predictions,
      horizonMinutes: horizons,
      unit: unit,
      features:
          TrajectoryFeatures.fromJson(_readObject(json, 'trajectory_features')),
      indicator:
          ResponseIndicator.fromJson(_readObject(json, 'response_indicator')),
      forecastModelName: _readString(json, 'forecast_model_name'),
      forecastModelVersion: _readString(json, 'forecast_model_version'),
      disclaimer: _readString(json, 'disclaimer'),
    );
  }
}

Map<String, dynamic> _readObject(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! Map<String, dynamic>) {
    throw FormatException('Field "$key" must be an object.');
  }
  return value;
}

double _readNumber(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! num || !value.isFinite) {
    throw FormatException('Field "$key" must be a finite number.');
  }
  return value.toDouble();
}

List<double> _readNumbers(Map<String, dynamic> json, String key) {
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

String _readString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! String) {
    throw FormatException('Field "$key" must be a string.');
  }
  return value;
}

String? _readOptionalString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value != null && value is! String) {
    throw FormatException('Field "$key" must be a string or null.');
  }
  return value as String?;
}
