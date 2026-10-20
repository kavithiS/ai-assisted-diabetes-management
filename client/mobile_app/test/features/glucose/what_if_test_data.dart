/// Fixtures for the What-If Meal Simulation tests. Synthetic values only; none of
/// them are nutrition data or model output.
library;

import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/glucose/glucose_models.dart';
import 'package:mobile_app/features/glucose/what_if_models.dart';

/// A forecast whose highest value is [peak] at index [peakIndex]. Every other
/// point stays below 108 mg/dL, so the peak is unambiguous.
GlucoseForecast forecastWithPeak(double peak, int peakIndex) {
  return GlucoseForecast(
    predictions: [
      for (var i = 0; i < forecastPointCount; i++)
        i == peakIndex ? peak : 100.0 + i * 0.5,
    ],
    horizonMinutes: [for (var i = 0; i < forecastPointCount; i++) (i + 1) * 15],
    unit: 'mg/dL',
    modelName: 'GRU',
    modelVersion: 'test-version',
    disclaimer: 'Research prediction, not a diagnosis.',
  );
}

/// Baseline meal used in the tests: 70 g carbohydrate, as in testMealRequest.
const whatIfBaselineCarbs = 70.0;

/// Test-only portion mapping. These are fixture numbers for exercising the
/// selector, not nutrition data for any rice portion.
const testRicePortionMapping = RicePortionMapping(
  carbsGramsByPortion: {
    RicePortion.halfCup: 40,
    RicePortion.oneCup: 80,
    RicePortion.oneAndHalfCups: 120,
  },
);

/// Records every forecast request and answers with [respond].
class FakeWhatIfApi extends ApiClient {
  FakeWhatIfApi(this._respond);

  final Future<GlucoseForecast> Function(GlucoseForecastRequest request)
      _respond;

  final requests = <GlucoseForecastRequest>[];

  @override
  Future<GlucoseForecast> forecastGlucose(GlucoseForecastRequest request) {
    requests.add(request);
    return _respond(request);
  }
}
