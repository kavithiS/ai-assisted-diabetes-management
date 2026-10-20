/// A scripted [ApiClient] for glucose tests. No network access.
library;

import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/glucose/dietary_risk_models.dart';
import 'package:mobile_app/features/glucose/glucose_models.dart';

import 'dietary_risk_test_data.dart';

GlucoseForecast testForecast() => GlucoseForecast(
      predictions: List<double>.generate(16, (i) => 110.0 + i),
      horizonMinutes: List<int>.generate(16, (i) => (i + 1) * 15),
      unit: 'mg/dL',
      modelName: 'GRU',
      modelVersion: 'test-version',
      disclaimer: 'Research prediction, not a diagnosis.',
    );

DietaryRiskAssessment testAssessment(
        {bool available = true, bool estimate = true}) =>
    DietaryRiskAssessment.fromJson(
        dietaryRiskJson(available: available, estimate: estimate));

class FakeGlucoseApi extends ApiClient {
  FakeGlucoseApi({
    Future<GlucoseForecast> Function()? forecast,
    Future<DietaryRiskAssessment> Function()? assess,
  })  : _forecast = forecast ?? (() async => testForecast()),
        _assess = assess ?? (() async => testAssessment());

  Future<GlucoseForecast> Function() _forecast;
  Future<DietaryRiskAssessment> Function() _assess;

  final forecastRequests = <GlucoseForecastRequest>[];
  final assessRequests = <GlucoseForecastRequest>[];

  set onForecast(Future<GlucoseForecast> Function() respond) =>
      _forecast = respond;

  set onAssess(Future<DietaryRiskAssessment> Function() respond) =>
      _assess = respond;

  @override
  Future<GlucoseForecast> forecastGlucose(GlucoseForecastRequest request) {
    forecastRequests.add(request);
    return _forecast();
  }

  @override
  Future<DietaryRiskAssessment> assessDietaryRisk(
      GlucoseForecastRequest request) {
    assessRequests.add(request);
    return _assess();
  }
}

const testMealValues = ['110', '600', '70', '25', '20', '8'];

const testMealRequest = GlucoseForecastRequest(
  premealGlucose: 110,
  calories: 600,
  carbs: 70,
  protein: 25,
  fat: 20,
  fiber: 8,
);
