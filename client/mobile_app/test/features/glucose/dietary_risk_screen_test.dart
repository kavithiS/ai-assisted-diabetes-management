import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/glucose/dietary_risk_models.dart';
import 'package:mobile_app/features/glucose/dietary_risk_screen.dart';
import 'package:mobile_app/features/glucose/glucose_session.dart';

import 'fake_glucose_api.dart';

/// A session with the test meal entered and, optionally, a forecast for it.
Future<GlucoseSession> _session({bool withForecast = true}) async {
  final session = GlucoseSession();
  for (var i = 0; i < testMealValues.length; i++) {
    session.controllers[i].text = testMealValues[i];
  }
  if (withForecast) {
    await session.runForecast(FakeGlucoseApi(), session.currentRequest!);
  }
  return session;
}

Future<void> _pump(
    WidgetTester tester, GlucoseSession session, ApiClient client) async {
  await tester.pumpWidget(MaterialApp(
    home:
        Scaffold(body: DietaryRiskScreen(session: session, apiClient: client)),
  ));
}

final _assessButton = find.widgetWithText(FilledButton, 'Assess this meal');

Future<void> _assess(WidgetTester tester) async {
  await tester.ensureVisible(_assessButton);
  await tester.tap(_assessButton);
  await tester.pumpAndSettle();
}

Iterable<String> _allText(WidgetTester tester) => tester
    .widgetList<Text>(find.byType(Text))
    .map((text) => text.data ?? text.textSpan?.toPlainText() ?? '');

void main() {
  testWidgets('asks for inputs on the forecast tab when none are entered',
      (tester) async {
    final session = GlucoseSession();
    final api = FakeGlucoseApi();
    await _pump(tester, session, api);

    expect(find.text('Dynamic Dietary Risk'), findsOneWidget);
    expect(find.text(dietaryRiskNoInputsMessage), findsOneWidget);
    expect(_assessButton, findsNothing);
    expect(find.byType(TextFormField), findsNothing,
        reason: 'Meal inputs are entered only on the forecast tab.');
    expect(api.assessRequests, isEmpty);
  });

  testWidgets('asks for a 4-hour estimate when no current forecast exists',
      (tester) async {
    final session = await _session(withForecast: false);
    await _pump(tester, session, FakeGlucoseApi());

    expect(find.text(dietaryRiskNoForecastMessage), findsOneWidget);
    expect(_assessButton, findsNothing);
  });

  testWidgets('a stale forecast also blocks a new assessment', (tester) async {
    final session = await _session();
    session.carbs.text = '95';
    await _pump(tester, session, FakeGlucoseApi());

    expect(find.text(dietaryRiskNoForecastMessage), findsOneWidget);
    expect(_assessButton, findsNothing);
  });

  testWidgets('renders the redesigned page from the actual API response',
      (tester) async {
    final session = await _session();
    final api = FakeGlucoseApi();
    await _pump(tester, session, api);

    await _assess(tester);

    expect(api.assessRequests, [testMealRequest]);
    // Summary card: no status badge, only the real predicted peak and timing.
    expect(find.text('Predicted peak glucose'), findsOneWidget);
    expect(find.text('Reached 4h after the meal'), findsOneWidget);
    expect(find.text('POST-MEAL RESPONSE INDICATOR · XGBOOST'), findsNothing);
    expect(find.text('Flagged'), findsNothing);
    expect(find.text('Not flagged'), findsNothing);
    // Metrics from trajectory_features.
    expect(find.text('DIETARY METRICS'), findsOneWidget);
    expect(find.text('+4h'), findsOneWidget);
    expect(find.text('+85 mg/dL'), findsOneWidget);
    expect(find.text('85 mg/dL'), findsOneWidget);
    expect(find.text('+0.7 mg/dL per min'), findsOneWidget);
    expect(find.text('10,500 mg/dL·min'), findsOneWidget);
    // The meal's entered values.
    expect(find.text("THIS MEAL'S INPUTS"), findsOneWidget);
    expect(find.text('110 mg/dL'), findsOneWidget);
    expect(find.text('600 kcal'), findsOneWidget);
    expect(find.text('70 g'), findsOneWidget);
    expect(find.text('8 g'), findsOneWidget);
    // Interpretation.
    expect(find.text('Risk Interpretation'), findsOneWidget);
    expect(find.text(dietaryRiskExplanation), findsOneWidget);
    expect(find.text(dietaryRiskDisclaimer), findsOneWidget);
    expect(find.text(dietaryRiskDataNote), findsOneWidget);
    expect(find.text(dietaryRiskNotIncludedNote), findsOneWidget);
    expect(
        find.textContaining('Forecast model: GRU (gru-test)'), findsOneWidget);
  });

  testWidgets('shows no invented score, probability, GI or GL values',
      (tester) async {
    final session = await _session();
    await _pump(tester, session, FakeGlucoseApi());
    await _assess(tester);

    for (final text in _allText(tester)) {
      expect(text, isNot(contains('/100')));
      expect(text, isNot(contains('%')));
      expect(text.toLowerCase(), isNot(contains('probab')));
      expect(text, isNot(contains('Moderate')));
    }
    expect(find.text('Meal GI'), findsNothing);
    expect(find.text('Meal GL'), findsNothing);
    expect(find.text('Cumulative daily carbohydrates'), findsNothing);
  });

  testWidgets(
      'the interpretation never describes a flagged or unflagged result',
      (tester) async {
    final session = await _session();
    await _pump(tester, session, FakeGlucoseApi());
    await _assess(tester);

    for (final text in _allText(tester)) {
      expect(text.toLowerCase(), isNot(contains('flag')));
      expect(text, isNot(contains('above 180 mg/dL within')));
      expect(text.toLowerCase(), isNot(contains('separate model')));
      expect(text.toLowerCase(), isNot(contains('classifier')));
    }
  });

  testWidgets(
      'shows the same trajectory explanation when no reading is flagged',
      (tester) async {
    final session = await _session();
    await _pump(tester, session,
        FakeGlucoseApi(assess: () async => testAssessment(estimate: false)));
    await _assess(tester);

    expect(find.text('Predicted peak glucose'), findsOneWidget);
    expect(find.text('Flagged'), findsNothing);
    expect(find.text(dietaryRiskExplanation), findsOneWidget);
  });

  testWidgets('shows an unavailable indicator without inventing a result',
      (tester) async {
    final session = await _session();
    await _pump(tester, session,
        FakeGlucoseApi(assess: () async => testAssessment(available: false)));
    await _assess(tester);

    expect(find.text('Flagged'), findsNothing);
    expect(find.text('Not flagged'), findsNothing);
    expect(find.textContaining('classifier'), findsNothing);
    // The interpretation still explains the displayed trajectory.
    expect(find.text(dietaryRiskExplanation), findsOneWidget);
    // The predicted response is still real and shown.
    expect(find.text('Predicted peak glucose'), findsOneWidget);
  });

  testWidgets('shows the API error message and no results', (tester) async {
    final session = await _session();
    await _pump(
        tester,
        session,
        FakeGlucoseApi(
            assess: () async => throw const ApiException(
                'The glucose model is unavailable right now.',
                statusCode: 503)));
    await _assess(tester);

    expect(find.text('The glucose model is unavailable right now.'),
        findsOneWidget);
    expect(find.text('Risk Interpretation'), findsNothing);
    expect(find.text('Flagged'), findsNothing);
  });

  testWidgets('shows a loading state and ignores repeated taps',
      (tester) async {
    final session = await _session();
    final completer = Completer<DietaryRiskAssessment>();
    final api = FakeGlucoseApi(assess: () => completer.future);
    await _pump(tester, session, api);

    await tester.ensureVisible(_assessButton);
    await tester.tap(_assessButton);
    await tester.pump();

    expect(find.text('Assessing meal…'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, 'Assessing meal…'),
        warnIfMissed: false);
    await tester.pump();
    expect(api.assessRequests, hasLength(1));

    completer.complete(testAssessment());
    await tester.pumpAndSettle();
    expect(find.text('Predicted peak glucose'), findsOneWidget);
    expect(find.text('Assess this meal again'), findsOneWidget);
  });

  testWidgets('marks results stale after an input change until reassessed',
      (tester) async {
    final session = await _session();
    final api = FakeGlucoseApi();
    await _pump(tester, session, api);
    await _assess(tester);
    expect(find.text(dietaryRiskStaleMessage), findsNothing);

    // The meal is edited on the forecast tab.
    session.carbs.text = '95';
    await tester.pump();

    expect(find.text(dietaryRiskStaleMessage), findsOneWidget);
    expect(find.text('Predicted peak glucose'), findsOneWidget,
        reason: 'Previous results stay visible, marked stale.');
    expect(find.text(dietaryRiskNoForecastMessage), findsOneWidget);
    expect(find.text('Assess this meal again'), findsNothing);

    // A new forecast for the edited meal, then a new assessment.
    await session.runForecast(api, session.currentRequest!);
    await tester.pump();
    await tester.ensureVisible(find.text('Assess this meal again'));
    await tester.tap(find.text('Assess this meal again'));
    await tester.pumpAndSettle();

    expect(find.text(dietaryRiskStaleMessage), findsNothing);
    expect(api.assessRequests.last.carbs, 95);
    expect(find.text('95 g'), findsOneWidget);
  });
}
