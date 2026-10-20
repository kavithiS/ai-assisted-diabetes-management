import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/glucose/glucose_models.dart';
import 'package:mobile_app/features/glucose/glucose_screen.dart';
import 'package:mobile_app/features/glucose/glucose_session.dart';
import 'package:mobile_app/features/glucose/what_if_models.dart';
import 'package:mobile_app/features/glucose/what_if_screen.dart';
import 'package:mobile_app/features/glucose/what_if_session.dart';

import 'fake_glucose_api.dart';
import 'what_if_test_data.dart';

/// Baseline answers with a 150 mg/dL peak at +60 min. Any other carbohydrate
/// amount answers with a 172 mg/dL peak at +90 min.
Future<GlucoseForecast> _respondByCarbs(GlucoseForecastRequest request) async {
  return request.carbs == whatIfBaselineCarbs
      ? forecastWithPeak(150, 3)
      : forecastWithPeak(172, 5);
}

Future<void> _pump(
  WidgetTester tester, {
  required FakeWhatIfApi api,
  GlucoseSession? session,
  WhatIfSession? whatIf,
  RicePortionMapping? mapping,
  bool fillInputs = true,
}) async {
  tester.view.physicalSize = const Size(400, 2600);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final glucose = session ?? GlucoseSession();
  if (fillInputs) {
    for (var i = 0; i < testMealValues.length; i++) {
      glucose.controllers[i].text = testMealValues[i];
    }
  }
  await tester.pumpWidget(MaterialApp(
    home: Scaffold(
      body: WhatIfScreen(
        session: glucose,
        whatIf: whatIf ?? WhatIfSession(),
        apiClient: api,
        ricePortionMapping: mapping,
      ),
    ),
  ));
}

/// Finds a Text.rich by its full plain text, e.g. '150 mg/dL'.
Finder _rich(String plainText) => find.byWidgetPredicate(
      (widget) => widget is RichText && widget.text.toPlainText() == plainText,
    );

Slider _slider(WidgetTester tester) =>
    tester.widget<Slider>(find.byType(Slider));

/// Moves the slider as a user drag would, without a gesture. Only the screen's
/// onChanged handler is exercised.
Future<void> _moveSlider(WidgetTester tester, double value) async {
  _slider(tester).onChanged!(value);
  await tester.pump();
}

Future<void> _compare(WidgetTester tester) async {
  final button = find.widgetWithText(FilledButton, 'Compare scenario');
  await tester.ensureVisible(button);
  await tester.tap(button);
  await tester.pumpAndSettle();
}

void main() {
  group('rendering', () {
    testWidgets('shows the header, disclaimer and the original meal',
        (tester) async {
      await _pump(tester, api: FakeWhatIfApi(_respondByCarbs));

      expect(find.text('What-If Meal Simulation'), findsOneWidget);
      expect(
        find.text(
            'Explore how changing the meal could affect the estimated glucose response.'),
        findsOneWidget,
      );
      expect(find.text(glucoseDisclaimer), findsOneWidget);
      expect(find.text('Original meal'), findsOneWidget);
      expect(find.text('70 g'), findsOneWidget);
      expect(_rich('70 g simulated'), findsOneWidget);
      expect(find.text('Rice portion (optional)'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Compare scenario'),
          findsOneWidget);
    });

    testWidgets('starts the slider at the original carbohydrate amount',
        (tester) async {
      await _pump(tester, api: FakeWhatIfApi(_respondByCarbs));

      expect(_slider(tester).value, whatIfBaselineCarbs);
      expect(_slider(tester).max, 200);
    });

    testWidgets('shows no comparison before the user asks for one',
        (tester) async {
      await _pump(tester, api: FakeWhatIfApi(_respondByCarbs));

      expect(find.text('Current meal vs what-if meal'), findsNothing);
      expect(find.text(whatIfStaleMessage), findsNothing);
    });

    testWidgets('explains the limitations of the simulation', (tester) async {
      await _pump(tester, api: FakeWhatIfApi(_respondByCarbs));

      expect(find.text('About this simulation'), findsOneWidget);
      for (final point in whatIfExplanationPoints) {
        expect(find.text(point), findsOneWidget);
      }
    });
  });

  group('carbohydrate slider', () {
    testWidgets('shows the simulated amount immediately and sends no request',
        (tester) async {
      final api = FakeWhatIfApi(_respondByCarbs);
      await _pump(tester, api: api);

      await _moveSlider(tester, 150);

      expect(_rich('150 g simulated'), findsOneWidget);
      expect(_slider(tester).value, 150);
      expect(api.requests, isEmpty);
    });

    testWidgets('rounds to a tenth of a gram', (tester) async {
      final api = FakeWhatIfApi(_respondByCarbs);
      await _pump(tester, api: api);

      await _moveSlider(tester, 52.34);

      expect(_rich('52.3 g simulated'), findsOneWidget);
    });
  });

  group('rice portion', () {
    testWidgets('options are disabled and explained when nothing is verified',
        (tester) async {
      await _pump(tester, api: FakeWhatIfApi(_respondByCarbs));

      for (final portion in RicePortion.values) {
        final chip = tester
            .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, portion.label));
        expect(chip.onSelected, isNull, reason: portion.label);
      }
      expect(find.text(whatIfRiceUnavailableMessage), findsOneWidget);
    });

    testWidgets('a verified mapping sets the carbohydrate amount',
        (tester) async {
      final api = FakeWhatIfApi(_respondByCarbs);
      await _pump(tester, api: api, mapping: testRicePortionMapping);

      await tester.tap(find.widgetWithText(ChoiceChip, '1 cup'));
      await tester.pump();

      expect(_slider(tester).value, 80);
      expect(_rich('80 g simulated'), findsOneWidget);
      expect(
        tester
            .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, '1 cup'))
            .selected,
        isTrue,
      );
      expect(find.text(whatIfRiceUnavailableMessage), findsNothing);
      expect(api.requests, isEmpty);
    });

    testWidgets('moving the slider away from a portion clears its selection',
        (tester) async {
      await _pump(tester,
          api: FakeWhatIfApi(_respondByCarbs), mapping: testRicePortionMapping);
      await tester.tap(find.widgetWithText(ChoiceChip, '1½ cups'));
      await tester.pump();

      await _moveSlider(tester, 95);

      expect(
        tester
            .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, '1½ cups'))
            .selected,
        isFalse,
      );
    });
  });

  group('comparison', () {
    testWidgets('requests the original and the what-if meal', (tester) async {
      final api = FakeWhatIfApi(_respondByCarbs);
      await _pump(tester, api: api);
      await _moveSlider(tester, 100);

      await _compare(tester);

      expect(api.requests, [
        testMealRequest,
        whatIfRequest(testMealRequest, 100),
      ]);
      // Only the carbohydrate input differs; the rest of the meal is preserved.
      final scenario = api.requests[1];
      expect(scenario.premealGlucose, testMealRequest.premealGlucose);
      expect(scenario.calories, testMealRequest.calories);
    });

    testWidgets('shows both peaks, their times and the differences',
        (tester) async {
      await _pump(tester, api: FakeWhatIfApi(_respondByCarbs));
      await _moveSlider(tester, 100);

      await _compare(tester);

      expect(find.text('Current meal vs what-if meal'), findsOneWidget);
      expect(_rich('150 mg/dL'), findsOneWidget);
      expect(_rich('172 mg/dL'), findsOneWidget);
      expect(find.text('Peak at +1h'), findsOneWidget);
      expect(find.text('Peak at +1h 30min'), findsOneWidget);
      expect(find.text('+22 mg/dL'), findsOneWidget);
      expect(find.text('30 min later'), findsOneWidget);
      expect(find.text('Estimates only. Values are rounded to whole mg/dL.'),
          findsOneWidget);
    });

    testWidgets('the peak difference uses the whole mg/dL values shown',
        (tester) async {
      final api = FakeWhatIfApi((request) async => request.carbs == 70
          ? forecastWithPeak(150.4, 3)
          : forecastWithPeak(172.6, 3));
      await _pump(tester, api: api);
      await _moveSlider(tester, 100);

      await _compare(tester);

      expect(_rich('150 mg/dL'), findsOneWidget);
      expect(_rich('173 mg/dL'), findsOneWidget);
      expect(find.text('+23 mg/dL'), findsOneWidget);
      expect(find.text('Same time'), findsOneWidget);
    });

    testWidgets('shows the legend for both series', (tester) async {
      await _pump(tester, api: FakeWhatIfApi(_respondByCarbs));
      await _moveSlider(tester, 100);

      await _compare(tester);

      // Each name appears in its peak tile and in the chart legend.
      expect(find.text('Current meal'), findsNWidgets(2));
      expect(find.text('What-if meal'), findsNWidgets(2));
    });

    testWidgets('shows no hardcoded demo results', (tester) async {
      await _pump(tester, api: FakeWhatIfApi(_respondByCarbs));
      await _moveSlider(tester, 100);

      await _compare(tester);

      expect(find.textContaining('155'), findsNothing);
      expect(find.textContaining('Moderate response'), findsNothing);
    });

    testWidgets('labels the model output and the observed inputs',
        (tester) async {
      await _pump(tester, api: FakeWhatIfApi(_respondByCarbs));
      await _moveSlider(tester, 100);

      await _compare(tester);

      expect(find.text('Model estimate'), findsNWidgets(2));
      expect(find.text('Model: GRU (test-version)'), findsOneWidget);
    });

    testWidgets('a comparison with the same peak shows no difference',
        (tester) async {
      await _pump(tester,
          api: FakeWhatIfApi((request) async => forecastWithPeak(150, 3)));
      await _moveSlider(tester, 100);

      await _compare(tester);

      expect(find.text('+0 mg/dL'), findsNothing);
      expect(find.text('0 mg/dL'), findsOneWidget);
      expect(find.text('Same time'), findsOneWidget);
    });
  });

  group('loading and errors', () {
    testWidgets('shows a loading state while both forecasts are running',
        (tester) async {
      final gate = Completer<void>();
      final api = FakeWhatIfApi((request) async {
        await gate.future;
        return _respondByCarbs(request);
      });
      await _pump(tester, api: api);
      await _moveSlider(tester, 100);

      final button = find.widgetWithText(FilledButton, 'Compare scenario');
      await tester.ensureVisible(button);
      await tester.tap(button);
      await tester.pump();

      expect(find.text('Comparing…'), findsOneWidget);
      expect(find.text('Calculating the two estimates…'), findsOneWidget);
      expect(
        tester
            .widget<FilledButton>(
                find.widgetWithText(FilledButton, 'Comparing…'))
            .onPressed,
        isNull,
        reason: 'A second comparison cannot start while one is running.',
      );

      gate.complete();
      await tester.pumpAndSettle();

      expect(find.text('Comparing…'), findsNothing);
      expect(find.text('Current meal vs what-if meal'), findsOneWidget);
    });

    testWidgets('shows the model error and no comparison', (tester) async {
      await _pump(
        tester,
        api: FakeWhatIfApi((request) async => throw const ApiException(
              'The glucose model is unavailable right now. Try again later.',
              statusCode: 503,
            )),
      );
      await _moveSlider(tester, 100);

      await _compare(tester);

      expect(find.text('Could not compare the meals'), findsOneWidget);
      expect(
        find.text(
            'The glucose model is unavailable right now. Try again later.'),
        findsOneWidget,
      );
      expect(find.text('Current meal vs what-if meal'), findsNothing);
    });

    testWidgets('shows a network failure the same way', (tester) async {
      await _pump(
        tester,
        api: FakeWhatIfApi((request) async => throw const ApiException(
              'Cannot reach the DiaCare server. Make sure the backend is running and the address is correct.',
            )),
      );

      await _compare(tester);

      expect(find.text('Could not compare the meals'), findsOneWidget);
      expect(find.textContaining('Cannot reach the DiaCare server'),
          findsOneWidget);
    });

    testWidgets('a retry after an error replaces the message with results',
        (tester) async {
      var failNext = true;
      final api = FakeWhatIfApi((request) async {
        if (failNext) {
          failNext = false;
          throw const ApiException('Temporary failure.');
        }
        return _respondByCarbs(request);
      });
      await _pump(tester, api: api);
      await _moveSlider(tester, 100);

      await _compare(tester);
      expect(find.text('Temporary failure.'), findsOneWidget);

      await _compare(tester);
      expect(find.text('Temporary failure.'), findsNothing);
      expect(_rich('172 mg/dL'), findsOneWidget);
    });
  });

  group('missing baseline inputs', () {
    testWidgets('asks for the meal instead of showing the simulation',
        (tester) async {
      final api = FakeWhatIfApi(_respondByCarbs);
      await _pump(tester, api: api, fillInputs: false);

      expect(find.text(whatIfNoInputsMessage), findsOneWidget);
      expect(find.byType(Slider), findsNothing);
      expect(
          find.widgetWithText(FilledButton, 'Compare scenario'), findsNothing);
      expect(api.requests, isEmpty);
    });

    testWidgets('an invalid pre-meal glucose counts as missing',
        (tester) async {
      final glucose = GlucoseSession();
      await _pump(tester,
          api: FakeWhatIfApi(_respondByCarbs),
          session: glucose,
          fillInputs: false);
      for (var i = 1; i < testMealValues.length; i++) {
        glucose.controllers[i].text = testMealValues[i];
      }
      glucose.premeal.text = '0';
      await tester.pump();

      expect(find.text(whatIfNoInputsMessage), findsOneWidget);
      expect(find.byType(Slider), findsNothing);
    });
  });

  group('stale comparison', () {
    testWidgets(
        'moving the slider marks the comparison stale without a request',
        (tester) async {
      final api = FakeWhatIfApi(_respondByCarbs);
      await _pump(tester, api: api);
      await _compare(tester);

      await _moveSlider(tester, 120);

      expect(find.text(whatIfStaleMessage), findsOneWidget);
      expect(find.text('Current meal vs what-if meal'), findsOneWidget);
      expect(api.requests, hasLength(2));
    });

    testWidgets('editing the meal marks the comparison stale', (tester) async {
      final glucose = GlucoseSession();
      await _pump(tester,
          api: FakeWhatIfApi(_respondByCarbs), session: glucose);
      await _compare(tester);

      glucose.premeal.text = '95';
      await tester.pump();

      expect(find.text(whatIfStaleMessage), findsOneWidget);
    });

    testWidgets('comparing again clears the stale state', (tester) async {
      final api = FakeWhatIfApi(_respondByCarbs);
      await _pump(tester, api: api);
      await _compare(tester);
      await _moveSlider(tester, 120);

      await _compare(tester);

      expect(find.text(whatIfStaleMessage), findsNothing);
      expect(api.requests, hasLength(4));
      expect(api.requests.last, whatIfRequest(testMealRequest, 120));
    });
  });
}
