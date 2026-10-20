import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/features/glucose/dietary_risk_models.dart';

import 'dietary_risk_test_data.dart';

void main() {
  group('DietaryRiskAssessment.fromJson', () {
    test('parses an available indicator and trajectory features', () {
      final result = DietaryRiskAssessment.fromJson(dietaryRiskJson());

      expect(result.predictions, hasLength(16));
      expect(result.horizonMinutes.first, 15);
      expect(result.features.predictedPeakGlucose, 195);
      expect(result.features.predictedPeakMinutes, 240);
      expect(result.features.peakChangeFromPremeal, 85);
      expect(result.features.maxRise, 85);
      expect(result.features.maxRiseRate, 0.67);
      expect(result.features.predictedIauc, 10500);
      expect(result.indicator.available, isTrue);
      expect(result.indicator.estimatedAbove180, isTrue);
      expect(result.indicator.modelVersion, 'xgb-test');
      expect(result.forecastModelVersion, 'gru-test');
    });

    test('parses an unavailable indicator without an estimate', () {
      final result =
          DietaryRiskAssessment.fromJson(dietaryRiskJson(available: false));

      expect(result.indicator.available, isFalse);
      expect(result.indicator.estimatedAbove180, isNull);
      expect(result.indicator.modelVersion, isNull);
      expect(result.indicator.evaluationNote, isNull);
    });

    Map<String, dynamic> indicatorOf(Map<String, dynamic> json) =>
        json['response_indicator'] as Map<String, dynamic>;
    Map<String, dynamic> featuresOf(Map<String, dynamic> json) =>
        json['trajectory_features'] as Map<String, dynamic>;

    final invalid = <String, void Function(Map<String, dynamic>)>{
      'available without an estimate': (json) =>
          indicatorOf(json)['estimated_above_180'] = null,
      'unavailable with an estimate': (json) => indicatorOf(json)
        ..['status'] = 'unavailable'
        ..['estimated_above_180'] = true,
      'an estimate that is not a boolean': (json) =>
          indicatorOf(json)['estimated_above_180'] = 'yes',
      'an unknown status': (json) => indicatorOf(json)['status'] = 'maybe',
      'an unknown indicator name': (json) =>
          indicatorOf(json)['name'] = 'risk_score',
      'a missing feature': (json) => featuresOf(json).remove('max_rise'),
      'a non-numeric feature': (json) =>
          featuresOf(json)['predicted_peak_glucose'] = '195',
      'a missing features object': (json) => json.remove('trajectory_features'),
      'too few predictions': (json) => json['predictions'] = [100.0],
      'another unit': (json) => json['unit'] = 'mmol/L',
      'a non-string model version': (json) =>
          indicatorOf(json)['model_version'] = 3,
    };

    invalid.forEach((description, mutate) {
      test('rejects a body with $description', () {
        final json = dietaryRiskJson();
        mutate(json);

        expect(
            () => DietaryRiskAssessment.fromJson(json), throwsFormatException);
      });
    });
  });
}
