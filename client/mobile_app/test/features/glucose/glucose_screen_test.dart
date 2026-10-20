import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/glucose/glucose_models.dart';
import 'package:mobile_app/features/glucose/glucose_screen.dart';

GlucoseForecast _forecast() => GlucoseForecast(
      predictions: List<double>.generate(16, (i) => 110.0 + i),
      horizonMinutes: List<int>.generate(16, (i) => (i + 1) * 15),
      unit: 'mg/dL',
      modelName: 'GRU',
      modelVersion: 'test-version',
      disclaimer: 'Research prediction, not a diagnosis.',
    );

/// Fake client that records calls and answers with a scripted future.
class _FakeApiClient extends ApiClient {
  _FakeApiClient(this._respond);

  final Future<GlucoseForecast> Function(GlucoseForecastRequest request)
      _respond;
  int calls = 0;
  GlucoseForecastRequest? lastRequest;

  @override
  Future<GlucoseForecast> forecastGlucose(GlucoseForecastRequest request) {
    calls++;
    lastRequest = request;
    return _respond(request);
  }
}

Future<void> _pumpScreen(WidgetTester tester, ApiClient client) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: GlucoseScreen(apiClient: client)),
    ),
  );
}

/// Fills the six form fields in order: pre-meal, calories, carbs, protein, fat, fibre.
Future<void> _fillForm(WidgetTester tester, List<String> values) async {
  final fields = find.byType(TextFormField);
  for (var i = 0; i < values.length; i++) {
    await tester.enterText(fields.at(i), values[i]);
  }
  await tester.pump();
}

final _submitButton = find.widgetWithText(FilledButton, 'Get 4-hour estimate');

/// The form is taller than the default test surface, so scroll the button into view first.
Future<void> _tapSubmit(WidgetTester tester) async {
  await tester.ensureVisible(_submitButton);
  await tester.pump();
  await tester.tap(_submitButton);
}

/// Scroll offset of the screen's own scroll view (not the text fields' inner scrollables).
double _scrollOffset(WidgetTester tester) {
  final scrollable = find
      .descendant(
          of: find.byType(SingleChildScrollView),
          matching: find.byType(Scrollable))
      .first;
  return tester.state<ScrollableState>(scrollable).position.pixels;
}

/// Taps submit and returns the scroll offset just before and after the response settles.
Future<(double, double)> _submitAndMeasureScroll(WidgetTester tester) async {
  await tester.ensureVisible(_submitButton);
  await tester.pump();
  final before = _scrollOffset(tester);
  await tester.tap(_submitButton);
  await tester.pumpAndSettle();
  return (before, _scrollOffset(tester));
}

void main() {
  testWidgets('scrolls the results into view after a successful forecast',
      (tester) async {
    final client = _FakeApiClient((_) async => _forecast());
    await _pumpScreen(tester, client);

    // enterText leaves the last field (fibre) focused, as on a device.
    await _fillForm(tester, ['110', '600', '70', '25', '20', '8']);
    final (before, after) = await _submitAndMeasureScroll(tester);

    expect(after, greaterThan(before));
    final screen = tester.getRect(find.byType(Scaffold));
    final heading =
        tester.getRect(find.text('Estimated glucose, next 4 hours'));
    expect(
      screen.contains(heading.topLeft) && screen.contains(heading.bottomRight),
      isTrue,
      reason: 'Results heading $heading should be inside the screen $screen.',
    );

    final fibre = tester.widget<EditableText>(find.descendant(
        of: find.byType(TextFormField).at(5),
        matching: find.byType(EditableText)));
    expect(fibre.focusNode.hasFocus, isTrue,
        reason: 'Scrolling to the results should not move focus.');
  });

  testWidgets('does not auto-scroll when validation fails', (tester) async {
    final client = _FakeApiClient((_) async => _forecast());
    await _pumpScreen(tester, client);

    final (before, after) = await _submitAndMeasureScroll(tester);

    expect(client.calls, 0);
    expect(after, before);
  });

  testWidgets('does not auto-scroll when the request fails', (tester) async {
    final client = _FakeApiClient(
      (_) async => throw const ApiException(
          'The glucose model is unavailable right now. Try again later.'),
    );
    await _pumpScreen(tester, client);

    await _fillForm(tester, ['110', '600', '70', '25', '20', '8']);
    final (before, after) = await _submitAndMeasureScroll(tester);

    expect(find.byIcon(Icons.error_outline), findsOneWidget);
    expect(after, before);
  });

  testWidgets(
      'shows validation errors and sends nothing when the form is empty',
      (tester) async {
    final client = _FakeApiClient((_) async => _forecast());
    await _pumpScreen(tester, client);

    await _tapSubmit(tester);
    await tester.pump();

    expect(find.text('Enter your pre-meal glucose.'), findsOneWidget);
    expect(find.text('Enter Calories.'), findsOneWidget);
    expect(client.calls, 0);
  });

  testWidgets('rejects a zero pre-meal glucose before calling the API',
      (tester) async {
    final client = _FakeApiClient((_) async => _forecast());
    await _pumpScreen(tester, client);

    await _fillForm(tester, ['0', '600', '70', '25', '20', '8']);
    await _tapSubmit(tester);
    await tester.pump();

    expect(find.text('Pre-meal glucose must be greater than 0 mg/dL.'),
        findsOneWidget);
    expect(client.calls, 0);
  });

  testWidgets('shows a loading state while the request is in flight',
      (tester) async {
    final completer = Completer<GlucoseForecast>();
    final client = _FakeApiClient((_) => completer.future);
    await _pumpScreen(tester, client);

    await _fillForm(tester, ['110', '600', '70', '25', '20', '8']);
    await _tapSubmit(tester);
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('Getting estimate…'), findsOneWidget);
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull);

    completer.complete(_forecast());
    await tester.pumpAndSettle();

    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('sends the entered values and displays the returned predictions',
      (tester) async {
    final client = _FakeApiClient((_) async => _forecast());
    await _pumpScreen(tester, client);

    await _fillForm(tester, ['110', '600', '70.5', '25', '20', '8']);
    await _tapSubmit(tester);
    await tester.pumpAndSettle();

    final sent = client.lastRequest!;
    expect(sent.premealGlucose, 110);
    expect(sent.carbs, 70.5);
    expect(sent.fiber, 8);

    expect(find.text('Estimated glucose, next 4 hours'), findsOneWidget);

    // The 16 values are in a collapsed section; expand it to read them.
    expect(find.text('+15 min'), findsNothing);
    await tester.ensureVisible(find.text('All 16 estimates'));
    await tester.tap(find.text('All 16 estimates'));
    await tester.pumpAndSettle();

    expect(find.text('+15 min'), findsOneWidget);
    expect(find.text('110 mg/dL'), findsOneWidget); // first prediction, 110.0
    expect(find.text('+4h'), findsOneWidget);
    expect(find.text('125 mg/dL'), findsOneWidget); // last prediction, 110 + 15
    expect(find.text('Research prediction, not a diagnosis.'), findsOneWidget);
    expect(find.text(glucoseDisclaimer), findsOneWidget);
    expect(find.text(glucoseResultsReminder), findsOneWidget);
  });

  testWidgets('shows the research disclaimer before any request',
      (tester) async {
    final client = _FakeApiClient((_) async => _forecast());
    await _pumpScreen(tester, client);

    expect(find.textContaining('Research prototype only'), findsOneWidget);
    expect(find.textContaining('diagnosis, treatment or insulin dosing'),
        findsOneWidget);
    expect(client.calls, 0);
  });

  testWidgets('shows the estimated peak value and when it occurs',
      (tester) async {
    final peaked = GlucoseForecast(
      predictions: [
        120, 135, 150, 162, 171.6, 168, 160, 150, //
        140, 132, 126, 121, 118, 116, 115, 114,
      ],
      horizonMinutes: List<int>.generate(16, (i) => (i + 1) * 15),
      unit: 'mg/dL',
      modelName: 'GRU',
      modelVersion: 'test-version',
      disclaimer: 'Research prediction, not a diagnosis.',
    );
    final client = _FakeApiClient((_) async => peaked);
    await _pumpScreen(tester, client);

    await _fillForm(tester, ['110', '600', '70', '25', '20', '8']);
    await _tapSubmit(tester);
    await tester.pumpAndSettle();

    expect(find.text('Highest estimate: 172 mg/dL'), findsOneWidget);
    expect(find.text('At +1h 15min after the meal'), findsOneWidget);
  });

  testWidgets('ignores repeated taps while a request is running',
      (tester) async {
    final completer = Completer<GlucoseForecast>();
    final client = _FakeApiClient((_) => completer.future);
    await _pumpScreen(tester, client);

    await _fillForm(tester, ['110', '600', '70', '25', '20', '8']);
    await _tapSubmit(tester);
    await tester.pump();
    await tester.tap(find.byType(FilledButton), warnIfMissed: false);
    await tester.pump();

    expect(client.calls, 1);
    completer.complete(_forecast());
    await tester.pumpAndSettle();
  });

  testWidgets('shows the API error message and no results', (tester) async {
    final client = _FakeApiClient(
      (_) async => throw const ApiException(
          'The glucose model is unavailable right now. Try again later.'),
    );
    await _pumpScreen(tester, client);

    await _fillForm(tester, ['110', '600', '70', '25', '20', '8']);
    await _tapSubmit(tester);
    await tester.pumpAndSettle();

    expect(
        find.text(
            'The glucose model is unavailable right now. Try again later.'),
        findsOneWidget);
    expect(find.text('Estimated glucose, next 4 hours'), findsNothing);
    expect(find.byIcon(Icons.error_outline), findsOneWidget);
  });
}
