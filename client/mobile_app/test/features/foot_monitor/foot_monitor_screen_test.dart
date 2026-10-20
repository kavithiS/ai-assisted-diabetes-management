import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/foot_monitor/data/foot_api.dart';
import 'package:mobile_app/features/foot_monitor/foot_monitor_screen.dart';

import 'foot_test_data.dart';

void main() {
  Widget screenWith(MockClientHandler handler) => MaterialApp(
        home: Scaffold(
          body: FootMonitorScreen(
            api: FootApi(
              apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
              httpClient: MockClient(handler),
            ),
            pickImage: (_) async => tinyPng,
          ),
        ),
      );

  void useTallView(WidgetTester tester) {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
  }

  Future<void> pickAndAnalyse(WidgetTester tester) async {
    await tester.tap(find.text('Gallery'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Analyse Photo'));
    await tester.pumpAndSettle();
  }

  testWidgets('analyse is disabled until a photo is chosen', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(screenWith((_) async => http.Response('{}', 200)));

    final button = tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Analyse Photo'));
    expect(button.onPressed, isNull);
    expect(find.text('No photo yet'), findsOneWidget);

    await tester.tap(find.text('Gallery'));
    await tester.pumpAndSettle();

    final enabled =
        tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Analyse Photo'));
    expect(enabled.onPressed, isNotNull);
  });

  testWidgets('shows the risk band and recommendations, never a score', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(
        screenWith((_) async => http.Response(jsonEncode(footAnalysisJson()), 200)));

    await pickAndAnalyse(tester);

    expect(find.text('Estimated risk: High'), findsOneWidget);
    expect(find.text('Test recommendation one'), findsOneWidget);
    expect(find.text('Test disclaimer'), findsOneWidget);
    expect(find.textContaining('Demo result'), findsOneWidget);
    expect(find.textContaining('%'), findsNothing);
    expect(find.textContaining('confidence'), findsNothing);
  });

  testWidgets('a low band shows its message and no demo notice for a real model',
      (tester) async {
    useTallView(tester);
    await tester.pumpWidget(screenWith((_) async => http.Response(
        jsonEncode(footAnalysisJson(riskBand: 'Low', isMock: false)), 200)));

    await pickAndAnalyse(tester);

    expect(find.text('Estimated risk: Low'), findsOneWidget);
    expect(find.textContaining('No signs of concern'), findsOneWidget);
    expect(find.textContaining('Demo result'), findsNothing);
  });

  testWidgets('an API error returns to capture with a friendly message', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(screenWith((_) async => http.Response(
        jsonEncode({
          'error': {'code': 'IMAGE_UNREADABLE', 'message': 'x', 'details': []},
          'request_id': null,
        }),
        422)));

    await pickAndAnalyse(tester);

    expect(find.text('Analyse Photo'), findsOneWidget);
    expect(find.text('The photo could not be read. Please take a new photo.'), findsOneWidget);
  });

  testWidgets('scan again resets the screen', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(
        screenWith((_) async => http.Response(jsonEncode(footAnalysisJson()), 200)));
    await pickAndAnalyse(tester);

    await tester.tap(find.text('Scan Again'));
    await tester.pumpAndSettle();

    expect(find.text('No photo yet'), findsOneWidget);
  });
}
