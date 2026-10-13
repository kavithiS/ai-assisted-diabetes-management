import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/meal_scan/data/meal_api.dart';
import 'package:mobile_app/features/meal_scan/meal_scan_screen.dart';

import 'meal_scan_test_data.dart';

void main() {
  Widget screenWith(MockClientHandler handler) => MaterialApp(
        home: Scaffold(
          body: MealScanScreen(
            api: MealApi(
              apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
              httpClient: MockClient(handler),
            ),
            pickImage: (_) async => tinyPng,
          ),
        ),
      );

  // A tall phone-sized view, so the lazily built result list renders every card.
  void useTallView(WidgetTester tester) {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
  }

  Future<void> pickPhotoAndMealType(WidgetTester tester) async {
    await tester.tap(find.text('Gallery'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Lunch'));
    await tester.pumpAndSettle();
  }

  Future<void> tapAnalyse(WidgetTester tester) async {
    await tester.ensureVisible(find.text('Analyse meal'));
    await tester.tap(find.text('Analyse meal'));
    await tester.pumpAndSettle();
  }

  bool analyseEnabled(WidgetTester tester) =>
      tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Analyse meal')).onPressed !=
      null;

  testWidgets('Analyse is disabled until a photo and a meal type are chosen', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(screenWith((_) async => http.Response('', 500)));

    expect(analyseEnabled(tester), isFalse);
    await tester.tap(find.text('Gallery'));
    await tester.pumpAndSettle();
    expect(analyseEnabled(tester), isFalse);
    await tester.tap(find.text('Dinner'));
    await tester.pumpAndSettle();
    expect(analyseEnabled(tester), isTrue);
  });

  testWidgets('shows foods, totals and the mock banner, but never confidence', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(
      screenWith((_) async => http.Response(jsonEncode(mockAnalysisJson()), 200)),
    );
    await pickPhotoAndMealType(tester);
    await tapAnalyse(tester);

    expect(find.textContaining('Demo data'), findsOneWidget);
    expect(find.text('Test Food A'), findsOneWidget);
    expect(find.text('Test Food B'), findsOneWidget);
    expect(find.text('300 kcal'), findsOneWidget);
    // Unknown sugars total is shown as unknown, not as zero.
    expect(find.text('Not available'), findsOneWidget);
    // Confidence values from the response (0.87, 0.65, 0.42) must not appear in any form.
    for (final hidden in ['87', '0.87', '65', '0.65', '42', '0.42', 'confidence', 'Confidence']) {
      expect(find.textContaining(hidden), findsNothing, reason: 'found "$hidden"');
    }
  });

  testWidgets('removing a food recalculates the totals', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(
      screenWith((_) async => http.Response(jsonEncode(mockAnalysisJson()), 200)),
    );
    await pickPhotoAndMealType(tester);
    await tapAnalyse(tester);

    await tester.tap(find.byTooltip('Remove Test Food A'));
    await tester.pumpAndSettle();

    expect(find.text('Test Food A'), findsNothing);
    // Only Test Food B remains: 100 kcal, and its sugars are known (1 g).
    expect(find.text('100 kcal'), findsWidgets);
    expect(find.text('Not available'), findsNothing);
  });

  testWidgets('an API error returns to capture with a friendly message', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(screenWith((_) async => http.Response(
          jsonEncode({
            'error': {'code': 'IMAGE_UNREADABLE', 'message': 'decoder failed', 'details': []},
          }),
          422,
        )));
    await pickPhotoAndMealType(tester);
    await tapAnalyse(tester);

    expect(find.text('The photo could not be read. Please take a new photo.'), findsOneWidget);
    expect(find.text('decoder failed'), findsNothing);
    expect(find.text('Analyse meal'), findsOneWidget);
  });
}
