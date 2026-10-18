import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/features/glucose/glucose_models.dart';

Map<String, dynamic> validResponse() => {
      'predictions': List<double>.generate(16, (i) => 100.0 + i),
      'horizon_minutes': List<int>.generate(16, (i) => (i + 1) * 15),
      'unit': 'mg/dL',
      'model_name': 'GRU',
      'model_version': 'test-version',
      'disclaimer': 'Research prediction.',
    };

void main() {
  group('GlucoseForecastRequest', () {
    test('serialises to the snake_case contract fields', () {
      const request = GlucoseForecastRequest(
        premealGlucose: 110,
        calories: 600,
        carbs: 70,
        protein: 25,
        fat: 20,
        fiber: 8,
      );

      expect(request.toJson(), {
        'premeal_glucose': 110.0,
        'calories': 600.0,
        'carbs': 70.0,
        'protein': 25.0,
        'fat': 20.0,
        'fiber': 8.0,
      });
    });
  });

  group('GlucoseForecast.fromJson', () {
    test('parses a valid 16-point response', () {
      final forecast = GlucoseForecast.fromJson(validResponse());

      expect(forecast.predictions, hasLength(16));
      expect(forecast.predictions.first, 100.0);
      expect(forecast.horizonMinutes.first, 15);
      expect(forecast.horizonMinutes.last, 240);
      expect(forecast.unit, 'mg/dL');
      expect(forecast.modelName, 'GRU');
      expect(forecast.modelVersion, 'test-version');
      expect(forecast.disclaimer, 'Research prediction.');
    });

    test('rejects a prediction list of the wrong length', () {
      final json = validResponse()..['predictions'] = <double>[100, 101];

      expect(() => GlucoseForecast.fromJson(json), throwsFormatException);
    });

    test('rejects a horizon list of the wrong length', () {
      final json = validResponse()..['horizon_minutes'] = <int>[15, 30];

      expect(() => GlucoseForecast.fromJson(json), throwsFormatException);
    });

    test('rejects an unexpected unit', () {
      final json = validResponse()..['unit'] = 'mmol/L';

      expect(() => GlucoseForecast.fromJson(json), throwsFormatException);
    });

    test('rejects non-numeric prediction values', () {
      final json = validResponse()
        ..['predictions'] = List<Object>.filled(16, 'high');

      expect(() => GlucoseForecast.fromJson(json), throwsFormatException);
    });

    test('rejects a missing field', () {
      final json = validResponse()..remove('model_version');

      expect(() => GlucoseForecast.fromJson(json), throwsFormatException);
    });
  });

  group('GlucoseForecast peak', () {
    test('finds the highest prediction and its horizon', () {
      final json = validResponse()
        ..['predictions'] = <double>[
          120, 135, 150, 162, 171.6, 168, 160, 150, //
          140, 132, 126, 121, 118, 116, 115, 114,
        ];
      final forecast = GlucoseForecast.fromJson(json);

      expect(forecast.peakIndex, 4);
      expect(forecast.peakGlucose, 171.6);
      expect(forecast.peakMinutes, 75);
    });

    test('uses the earliest horizon when the highest value repeats', () {
      final json = validResponse()
        ..['predictions'] =
            List<double>.generate(16, (i) => i < 3 ? 140.0 + i : 142.0);
      final forecast = GlucoseForecast.fromJson(json);

      expect(forecast.peakMinutes, 45);
    });

    test('reports the first horizon for a falling forecast', () {
      final json = validResponse()
        ..['predictions'] = List<double>.generate(16, (i) => 180.0 - i);
      final forecast = GlucoseForecast.fromJson(json);

      expect(forecast.peakGlucose, 180.0);
      expect(forecast.peakMinutes, 15);
    });
  });

  group('validatePremealGlucose', () {
    test('requires a value', () {
      expect(validatePremealGlucose(null), 'Enter your pre-meal glucose.');
      expect(validatePremealGlucose('   '), 'Enter your pre-meal glucose.');
    });

    test('rejects non-numeric input', () {
      expect(validatePremealGlucose('abc'), 'Enter a valid number.');
      expect(validatePremealGlucose('Infinity'), 'Enter a valid number.');
    });

    test('rejects zero and negative values', () {
      expect(validatePremealGlucose('0'),
          'Pre-meal glucose must be greater than 0 mg/dL.');
      expect(validatePremealGlucose('-5'),
          'Pre-meal glucose must be greater than 0 mg/dL.');
    });

    test('accepts a positive decimal', () {
      expect(validatePremealGlucose('112.5'), isNull);
    });
  });

  group('validateNutrient', () {
    test('requires a value', () {
      expect(validateNutrient('', label: 'Protein'), 'Enter Protein.');
    });

    test('rejects non-numeric input', () {
      expect(validateNutrient('lots', label: 'Fat'), 'Enter a valid number.');
    });

    test('rejects negative values but allows zero', () {
      expect(
          validateNutrient('-1', label: 'Fibre'), 'Fibre cannot be negative.');
      expect(validateNutrient('0', label: 'Fibre'), isNull);
    });
  });
}
