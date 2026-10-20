/// Models for the What-If Meal Simulation. Each scenario is a second call to the
/// existing C2 forecast with only the carbohydrate input changed. Nothing here
/// predicts glucose itself.
library;

import 'dart:math' as math;

import 'glucose_models.dart';

/// Lowest carbohydrate amount the simulation slider allows, in grams.
const double whatIfMinCarbsGrams = 0;

/// Smallest upper bound of the slider, in grams. A display range chosen for
/// usability, not a clinical or validated limit: the forecast contract sets no
/// upper bound for nutrition values yet.
const double whatIfBaseMaxCarbsGrams = 200;

/// Upper bound of the carbohydrate slider for a meal with [originalCarbs] grams:
/// at least [whatIfBaseMaxCarbsGrams], and at least twice the original amount so
/// the original meal can always be explored in both directions.
double whatIfMaxCarbsGrams(double originalCarbs) =>
    math.max(whatIfBaseMaxCarbsGrams, (originalCarbs * 2).ceilToDouble());

/// Rice portions offered by the portion selector.
enum RicePortion {
  halfCup('½ cup'),
  oneCup('1 cup'),
  oneAndHalfCups('1½ cups');

  const RicePortion(this.label);

  /// Text shown on the portion option.
  final String label;
}

/// Carbohydrate grams for each rice portion.
///
/// The repository has no verified nutrition data for Sri Lankan rice portions,
/// so this mapping is only a configuration point. Real predictions must not use
/// values that have not been verified against a named nutrition source.
class RicePortionMapping {
  const RicePortionMapping({required this.carbsGramsByPortion});

  /// Carbohydrate grams for each portion. Every [RicePortion] must have a value.
  final Map<RicePortion, double> carbsGramsByPortion;

  /// Carbohydrate grams for [portion].
  double carbsFor(RicePortion portion) {
    final grams = carbsGramsByPortion[portion];
    if (grams == null) {
      throw ArgumentError.value(portion, 'portion', 'No carbohydrate value.');
    }
    return grams;
  }
}

/// The verified portion-to-carbohydrate mapping. Null until supervisors or the
/// nutrition owner supply verified values, so the rice portion selector stays
/// disabled and no portion is turned into a made-up prediction. [INFORMATION
/// REQUIRED: verified nutrition values for rice portions, with a named source.]
const RicePortionMapping? verifiedRicePortionMapping = null;

/// The request for a meal with only its carbohydrate amount changed. Pre-meal
/// glucose and the other nutrition values are kept as entered.
GlucoseForecastRequest whatIfRequest(
  GlucoseForecastRequest baseline,
  double carbs,
) =>
    GlucoseForecastRequest(
      premealGlucose: baseline.premealGlucose,
      calories: baseline.calories,
      carbs: carbs,
      protein: baseline.protein,
      fat: baseline.fat,
      fiber: baseline.fiber,
    );

/// Baseline and scenario forecasts for one comparison, with the requests that
/// produced them.
class WhatIfComparison {
  const WhatIfComparison({
    required this.baselineRequest,
    required this.scenarioRequest,
    required this.baseline,
    required this.scenario,
  });

  final GlucoseForecastRequest baselineRequest;
  final GlucoseForecastRequest scenarioRequest;

  /// Forecast for the meal as entered.
  final GlucoseForecast baseline;

  /// Forecast for the meal with the simulated carbohydrate amount.
  final GlucoseForecast scenario;

  /// Scenario peak minus baseline peak, in mg/dL, from the whole-mg/dL values
  /// shown on screen, so the displayed numbers always reconcile.
  int get peakDifferenceMgDl =>
      scenario.peakGlucose.round() - baseline.peakGlucose.round();

  /// Scenario peak time minus baseline peak time, in minutes. Negative means the
  /// scenario peaks earlier.
  int get peakTimingDifferenceMinutes =>
      scenario.peakMinutes - baseline.peakMinutes;
}
