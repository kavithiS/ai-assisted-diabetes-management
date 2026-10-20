import 'package:flutter/widgets.dart';

import '../../core/api_client.dart';
import 'glucose_models.dart';
import 'what_if_models.dart';

/// State of the What-If Meal Simulation: the simulated carbohydrate amount and
/// the last comparison.
///
/// Moving the slider only changes [scenarioCarbs]. The forecast API is called
/// once per [runComparison], so a slider drag never sends requests. A comparison
/// stays visible but is marked stale once the slider or the entered meal changes.
class WhatIfSession extends ChangeNotifier {
  /// Simulated carbohydrate amount in grams, or null until the user moves the
  /// slider. Null means the original amount is used.
  double? scenarioCarbs;

  bool loading = false;
  String? error;
  WhatIfComparison? comparison;
  int _sequence = 0;

  /// Sets the simulated carbohydrate amount. Makes no API request.
  void setScenarioCarbs(double carbs) {
    if (scenarioCarbs == carbs) return;
    scenarioCarbs = carbs;
    notifyListeners();
  }

  /// The carbohydrate amount to simulate for a meal that has [originalCarbs],
  /// kept within the slider range. The slider, the comparison and the stale
  /// check all use this value, so they always agree.
  double carbsFor(double originalCarbs) {
    final carbs = scenarioCarbs ?? originalCarbs;
    return carbs
        .clamp(whatIfMinCarbsGrams, whatIfMaxCarbsGrams(originalCarbs))
        .toDouble();
  }

  /// Whether [comparison] no longer matches the entered meal and the slider.
  bool isStale(GlucoseForecastRequest? baseline, double carbs) {
    final current = comparison;
    if (current == null) return false;
    return baseline != current.baselineRequest ||
        carbs != current.scenarioRequest.carbs;
  }

  /// Requests the baseline and the scenario forecasts together. Clears any
  /// previous comparison, as the forecast page does. Only the latest request
  /// may store a result.
  Future<bool> runComparison(
    ApiClient client,
    GlucoseForecastRequest baseline,
    double carbs,
  ) async {
    final sequence = ++_sequence;
    final scenario = whatIfRequest(baseline, carbs);
    loading = true;
    error = null;
    comparison = null;
    notifyListeners();
    try {
      final results = await Future.wait([
        client.forecastGlucose(baseline),
        client.forecastGlucose(scenario),
      ]);
      if (sequence != _sequence) return false;
      comparison = WhatIfComparison(
        baselineRequest: baseline,
        scenarioRequest: scenario,
        baseline: results[0],
        scenario: results[1],
      );
      return true;
    } on ApiException catch (failure) {
      if (sequence != _sequence) return false;
      error = failure.message;
      return false;
    } finally {
      if (sequence == _sequence) {
        loading = false;
        notifyListeners();
      }
    }
  }
}
