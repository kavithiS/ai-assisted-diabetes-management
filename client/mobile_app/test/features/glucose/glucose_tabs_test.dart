import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/features/glucose/dietary_risk_screen.dart';
import 'package:mobile_app/features/glucose/glucose_screen.dart';
import 'package:mobile_app/features/glucose/glucose_tabs.dart';
import 'package:mobile_app/features/glucose/what_if_models.dart';

import 'fake_glucose_api.dart';

Future<void> _pumpTabs(WidgetTester tester, FakeGlucoseApi api) async {
  await tester.pumpWidget(MaterialApp(
    home: Scaffold(body: GlucoseTabs(apiClient: api)),
  ));
}

Future<void> _fillForecastForm(WidgetTester tester, List<String> values) async {
  final fields = find.byType(TextFormField);
  for (var i = 0; i < values.length; i++) {
    await tester.enterText(fields.at(i), values[i]);
  }
  await tester.pump();
}

Future<void> _getForecast(WidgetTester tester) async {
  final button = find.widgetWithText(FilledButton, 'Get 4-hour estimate');
  await tester.ensureVisible(button);
  await tester.tap(button);
  await tester.pumpAndSettle();
}

Future<void> _openTab(WidgetTester tester, String label) async {
  await tester.tap(find.text(label));
  await tester.pumpAndSettle();
}

List<String> _fieldTexts(WidgetTester tester) => tester
    .widgetList<TextFormField>(find.byType(TextFormField))
    .map((field) => field.controller!.text)
    .toList();

void main() {
  testWidgets('switching tabs keeps the inputs and the forecast',
      (tester) async {
    await _pumpTabs(tester, FakeGlucoseApi());
    await _fillForecastForm(tester, testMealValues);
    await _getForecast(tester);
    expect(find.text('Estimated glucose, next 4 hours'), findsOneWidget);

    await _openTab(tester, 'Dietary risk');
    expect(find.text('Dynamic Dietary Risk'), findsOneWidget);
    await _openTab(tester, '4-hour forecast');

    expect(_fieldTexts(tester), testMealValues);
    expect(find.text('Estimated glucose, next 4 hours'), findsOneWidget);
  });

  testWidgets('both functions use the meal entered once on the forecast tab',
      (tester) async {
    final api = FakeGlucoseApi();
    await _pumpTabs(tester, api);
    await _fillForecastForm(tester, testMealValues);
    await _getForecast(tester);

    await _openTab(tester, 'Dietary risk');
    expect(find.byType(TextFormField), findsNothing);
    final assess = find.widgetWithText(FilledButton, 'Assess this meal');
    await tester.ensureVisible(assess);
    await tester.tap(assess);
    await tester.pumpAndSettle();

    expect(api.forecastRequests, [testMealRequest]);
    expect(api.assessRequests, [testMealRequest]);
    expect(find.text('Predicted peak glucose'), findsOneWidget);
  });

  testWidgets('dietary results survive switching tabs', (tester) async {
    await _pumpTabs(tester, FakeGlucoseApi());
    await _fillForecastForm(tester, testMealValues);
    await _getForecast(tester);
    await _openTab(tester, 'Dietary risk');
    final assess = find.widgetWithText(FilledButton, 'Assess this meal');
    await tester.ensureVisible(assess);
    await tester.tap(assess);
    await tester.pumpAndSettle();

    await _openTab(tester, '4-hour forecast');
    await _openTab(tester, 'Dietary risk');

    expect(find.text('Predicted peak glucose'), findsOneWidget);
    expect(find.text('Risk Interpretation'), findsOneWidget);
  });

  testWidgets('editing an input marks both results stale', (tester) async {
    await _pumpTabs(tester, FakeGlucoseApi());
    await _fillForecastForm(tester, testMealValues);
    await _getForecast(tester);
    await _openTab(tester, 'Dietary risk');
    final assess = find.widgetWithText(FilledButton, 'Assess this meal');
    await tester.ensureVisible(assess);
    await tester.tap(assess);
    await tester.pumpAndSettle();

    await _openTab(tester, '4-hour forecast');
    await tester.enterText(find.byType(TextFormField).at(2), '95');
    await tester.pump();
    expect(find.text(glucoseStaleForecastMessage), findsOneWidget);
    expect(find.text('Estimated glucose, next 4 hours'), findsOneWidget,
        reason: 'The previous forecast stays visible, marked stale.');

    await _openTab(tester, 'Dietary risk');
    expect(find.text(dietaryRiskStaleMessage), findsOneWidget);
    expect(find.text(dietaryRiskNoForecastMessage), findsOneWidget);

    await _openTab(tester, '4-hour forecast');
    await _getForecast(tester);
    expect(find.text(glucoseStaleForecastMessage), findsNothing);
  });

  testWidgets(
      'the What-if simulation tab uses the meal entered on the forecast tab',
      (tester) async {
    final api = FakeGlucoseApi();
    await _pumpTabs(tester, api);
    await _fillForecastForm(tester, testMealValues);

    await _openTab(tester, 'What-if simulation');
    expect(find.text('What-If Meal Simulation'), findsOneWidget);
    expect(find.byType(TextFormField), findsNothing);

    tester.widget<Slider>(find.byType(Slider)).onChanged!(40);
    await tester.pump();
    final compare = find.widgetWithText(FilledButton, 'Compare scenario');
    await tester.ensureVisible(compare);
    await tester.tap(compare);
    await tester.pumpAndSettle();

    expect(api.forecastRequests,
        [testMealRequest, whatIfRequest(testMealRequest, 40)]);
    expect(find.text('Current meal vs what-if meal'), findsOneWidget);
  });

  testWidgets('the guidance button opens the forecast tab', (tester) async {
    await _pumpTabs(tester, FakeGlucoseApi());
    await _openTab(tester, 'Dietary risk');
    expect(find.text(dietaryRiskNoInputsMessage), findsOneWidget);

    await tester.tap(find.text('Go to 4-hour forecast'));
    await tester.pumpAndSettle();

    expect(find.text('Current pre-meal glucose (mg/dL)'), findsOneWidget);
  });
}
