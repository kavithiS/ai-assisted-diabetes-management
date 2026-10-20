import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/glucose/glucose_models.dart';
import 'package:mobile_app/features/glucose/what_if_models.dart';
import 'package:mobile_app/features/glucose/what_if_session.dart';

import 'fake_glucose_api.dart';
import 'what_if_test_data.dart';

void main() {
  group('slider bounds', () {
    test('use the 200 g base range for a typical meal', () {
      expect(whatIfMaxCarbsGrams(70), 200);
      expect(whatIfMaxCarbsGrams(0), 200);
    });

    test('extend to twice the original amount for a large meal', () {
      expect(whatIfMaxCarbsGrams(150), 300);
      expect(whatIfMaxCarbsGrams(120.5), 241);
    });

    test('minimum is zero grams, the lowest value the API accepts', () {
      expect(whatIfMinCarbsGrams, 0);
    });
  });

  group('whatIfRequest', () {
    test('changes only the carbohydrate input', () {
      final scenario = whatIfRequest(testMealRequest, 45);

      expect(scenario.carbs, 45);
      expect(scenario.premealGlucose, testMealRequest.premealGlucose);
      expect(scenario.calories, testMealRequest.calories);
      expect(scenario.protein, testMealRequest.protein);
      expect(scenario.fat, testMealRequest.fat);
      expect(scenario.fiber, testMealRequest.fiber);
    });

    test('leaves the baseline request unchanged', () {
      whatIfRequest(testMealRequest, 45);

      expect(testMealRequest.carbs, 70);
    });
  });

  group('rice portion mapping', () {
    test('is not configured, so no portion values exist yet', () {
      expect(verifiedRicePortionMapping, isNull);
    });

    test('returns the configured grams for a portion', () {
      expect(testRicePortionMapping.carbsFor(RicePortion.oneCup), 80);
    });

    test('throws for a portion with no configured value', () {
      const partial = RicePortionMapping(
        carbsGramsByPortion: {RicePortion.halfCup: 40},
      );

      expect(() => partial.carbsFor(RicePortion.oneCup), throwsArgumentError);
    });
  });

  group('WhatIfComparison', () {
    WhatIfComparison compare(
        GlucoseForecast baseline, GlucoseForecast scenario) {
      return WhatIfComparison(
        baselineRequest: testMealRequest,
        scenarioRequest: whatIfRequest(testMealRequest, 100),
        baseline: baseline,
        scenario: scenario,
      );
    }

    test('peak difference is scenario peak minus baseline peak', () {
      final comparison = compare(
        forecastWithPeak(150, 3),
        forecastWithPeak(172, 5),
      );

      expect(comparison.peakDifferenceMgDl, 22);
    });

    test('peak difference is negative when the scenario peaks lower', () {
      final comparison = compare(
        forecastWithPeak(150, 3),
        forecastWithPeak(131, 3),
      );

      expect(comparison.peakDifferenceMgDl, -19);
    });

    test('peak difference uses the whole mg/dL values shown on screen', () {
      // 150.4 shows as 150 and 172.6 as 173, so the difference shown is 23.
      final comparison = compare(
        forecastWithPeak(150.4, 3),
        forecastWithPeak(172.6, 3),
      );

      expect(comparison.peakDifferenceMgDl, 23);
    });

    test('timing difference is scenario peak time minus baseline peak time',
        () {
      // Baseline peaks at index 3 (+60 min); scenario at index 5 (+90 min).
      final later = compare(
        forecastWithPeak(150, 3),
        forecastWithPeak(172, 5),
      );
      final earlier = compare(
        forecastWithPeak(172, 5),
        forecastWithPeak(150, 3),
      );

      expect(later.peakTimingDifferenceMinutes, 30);
      expect(earlier.peakTimingDifferenceMinutes, -30);
    });

    test('timing difference is zero when both peaks are at the same time', () {
      final comparison = compare(
        forecastWithPeak(150, 3),
        forecastWithPeak(160, 3),
      );

      expect(comparison.peakTimingDifferenceMinutes, 0);
    });
  });

  group('WhatIfSession', () {
    test('uses the original carbohydrate amount until the slider moves', () {
      final session = WhatIfSession();

      expect(session.carbsFor(70), 70);
      session.setScenarioCarbs(45);
      expect(session.carbsFor(70), 45);
    });

    test('keeps the simulated amount within the slider range', () {
      final session = WhatIfSession()..setScenarioCarbs(300);

      // The original meal's range is 200 g here, so 300 g is clamped.
      expect(session.carbsFor(70), 200);
      session.dispose();
    });

    test('a comparison is stale once the meal or the amount changes', () async {
      final api = FakeWhatIfApi((request) async => forecastWithPeak(150, 3));
      final session = WhatIfSession();
      await session.runComparison(api, testMealRequest, 100);

      expect(session.isStale(testMealRequest, 100), isFalse);
      expect(session.isStale(testMealRequest, 60), isTrue);
      expect(
        session.isStale(
          const GlucoseForecastRequest(
            premealGlucose: 95,
            calories: 600,
            carbs: 70,
            protein: 25,
            fat: 20,
            fiber: 8,
          ),
          100,
        ),
        isTrue,
      );
      session.dispose();
    });

    test('ignores an earlier comparison that finishes after a newer one',
        () async {
      final first = Future<GlucoseForecast>.delayed(
          const Duration(milliseconds: 50), () => forecastWithPeak(150, 3));
      var calls = 0;
      final api = FakeWhatIfApi((request) {
        calls++;
        // The first pair of calls is slow; the second pair answers at once.
        if (calls <= 2) return first;
        return Future.value(forecastWithPeak(160, 4));
      });
      final session = WhatIfSession();

      final slow = session.runComparison(api, testMealRequest, 100);
      await session.runComparison(api, testMealRequest, 90);
      await slow;

      expect(session.comparison?.scenarioRequest.carbs, 90);
      expect(session.loading, isFalse);
      session.dispose();
    });

    test('stores the API error message and no comparison', () async {
      final api = FakeWhatIfApi(
        (request) async => throw const ApiException('Model unavailable.'),
      );
      final session = WhatIfSession();

      final succeeded = await session.runComparison(api, testMealRequest, 100);

      expect(succeeded, isFalse);
      expect(session.error, 'Model unavailable.');
      expect(session.comparison, isNull);
      session.dispose();
    });
  });
}
