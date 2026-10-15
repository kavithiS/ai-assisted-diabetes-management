import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/meal_history/data/meal_history_api.dart';
import 'package:mobile_app/features/meal_scan/data/meal_api.dart';
import 'package:mobile_app/features/meal_scan/meal_scan_screen.dart';

import 'meal_scan_test_data.dart';

void main() {
  Widget screenWith(MockClientHandler handler, {MealHistoryApi? historyApi}) =>
      MaterialApp(
        home: Scaffold(
          body: MealScanScreen(
            api: MealApi(
              apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
              httpClient: MockClient(handler),
            ),
            historyApi: historyApi,
            pickImage: (_) async => tinyPng,
          ),
        ),
      );

  void useTallView(WidgetTester tester) {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
  }

  Future<void> pickPhotoAndMealType(WidgetTester tester) async {
    await tester.tap(find.text('Upload Image'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Lunch'));
    await tester.pumpAndSettle();
  }

  Future<void> showFoodReview(
      WidgetTester tester, MockClientHandler handler) async {
    await tester.pumpWidget(screenWith(handler));
    await pickPhotoAndMealType(tester);
    await tester.tap(find.text('Review Photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Analyse meal'));
    await tester.pumpAndSettle();
  }

  Future<void> openPortions(WidgetTester tester) async {
    await tester.tap(find.text('Confirm Foods'));
    await tester.pumpAndSettle();
    expect(find.text('Confirm Portions'), findsOneWidget);
  }

  Future<void> openNutrition(WidgetTester tester) async {
    await openPortions(tester);
    await tester.tap(find.text('Continue to Nutrition'));
    await tester.pumpAndSettle();
    expect(find.text('Nutrition Analysis'), findsOneWidget);
  }

  testWidgets('scan requires a photo and meal type before review',
      (tester) async {
    useTallView(tester);
    await tester.pumpWidget(screenWith((_) async => http.Response('', 500)));
    expect(
        tester
            .widget<FilledButton>(
                find.widgetWithText(FilledButton, 'Review Photo'))
            .onPressed,
        isNull);
    await tester.tap(find.text('Upload Image'));
    await tester.pumpAndSettle();
    expect(
        tester
            .widget<FilledButton>(
                find.widgetWithText(FilledButton, 'Review Photo'))
            .onPressed,
        isNull);
    await tester.tap(find.text('Dinner'));
    await tester.pumpAndSettle();
    expect(
        tester
            .widget<FilledButton>(
                find.widgetWithText(FilledButton, 'Review Photo'))
            .onPressed,
        isNotNull);
  });

  testWidgets('photo review can return to scan', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(screenWith((_) async => http.Response('', 500)));
    await pickPhotoAndMealType(tester);
    await tester.tap(find.text('Review Photo'));
    await tester.pumpAndSettle();
    expect(find.text('Retake Photo'), findsOneWidget);
    await tester.tap(find.text('Retake Photo'));
    await tester.pumpAndSettle();
    expect(find.text('Scan Meal'), findsOneWidget);
  });

  testWidgets(
      'recognition shows foods without confidence and unknown nutrients stay unknown',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    expect(find.text('Meal Review'), findsOneWidget);
    expect(find.text('Test Food A'), findsOneWidget);
    expect(find.text('Test Food B'), findsOneWidget);
    expect(find.textContaining('Demo data'), findsOneWidget);
    for (final hidden in [
      '87',
      '0.87',
      '65',
      '0.65',
      '42',
      '0.42',
      'confidence',
      'Confidence'
    ]) {
      expect(find.textContaining(hidden), findsNothing,
          reason: 'found "$hidden"');
    }
    await openNutrition(tester);
    expect(find.text('300 kcal'), findsOneWidget);
    expect(find.text('Not available'), findsWidgets);
  });

  testWidgets('removing a food updates nutrition totals', (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await tester.tap(find.byTooltip('Remove Test Food A'));
    await tester.pumpAndSettle();
    expect(find.text('Test Food A'), findsNothing);
    await openNutrition(tester);
    expect(find.text('100 kcal'), findsOneWidget);
    expect(find.text('Not available'), findsOneWidget);
  });

  testWidgets('editing portions rescales nutrients and rejects invalid grams',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await openPortions(tester);
    await tester.enterText(find.byType(TextField).first, '300');
    await tester.tap(find.text('Set').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Nutrition'));
    await tester.pumpAndSettle();
    expect(find.text('500 kcal'), findsOneWidget);
    expect(find.text('Not available'), findsWidgets);
  });

  testWidgets('portion amount validation reports invalid values',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await openPortions(tester);
    await tester.enterText(find.byType(TextField).first, '0');
    await tester.tap(find.text('Set').first);
    await tester.pumpAndSettle();
    expect(find.text('Enter an amount above 0 g.'), findsOneWidget);
    await tester.enterText(find.byType(TextField).first, '5000');
    await tester.tap(find.text('Set').first);
    await tester.pumpAndSettle();
    expect(find.text('Enter an amount up to 2000 g.'), findsOneWidget);
    expect(find.text('Estimate: 150 g'), findsOneWidget);
  });

  testWidgets('food editor can remove and re-add a nutrient field',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await tester.tap(find.byTooltip('Edit Test Food A'));
    await tester.pumpAndSettle();
    expect(find.text('Edit Food'), findsOneWidget);
    await tester.tap(find.byTooltip('Remove Dietary fibre (g)'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Add nutrient'));
    await tester.pumpAndSettle();
    expect(find.text('Dietary fibre (g)'), findsOneWidget);
    await tester.tap(find.text('Save Changes'));
    await tester.pumpAndSettle();
    expect(find.text('Meal Review'), findsOneWidget);
  });

  testWidgets(
      'glycemic measures and recommendations show unavailable when absent',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await openNutrition(tester);
    await tester.tap(find.text('View Nutrition Details'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Glycemic Profile'));
    await tester.pumpAndSettle();
    expect(find.text('Glycemic Profile'), findsOneWidget);
    expect(find.text('Glycemic load'), findsOneWidget);
    expect(find.text('Not available'), findsWidgets);
    await tester.tap(find.text('Continue to Meal Summary'));
    await tester.pumpAndSettle();
    expect(find.text('Meal Summary'), findsOneWidget);
    await tester.tap(find.text('View Portion Recommendation'));
    await tester.pumpAndSettle();
    expect(find.text('Portion Recommendation'), findsOneWidget);
    expect(find.text('Profile-based portion suggestion'), findsOneWidget);
  });

  testWidgets('meal summary saves foods through meal history API',
      (tester) async {
    useTallView(tester);
    late Map<String, dynamic> savedBody;
    final historyApi = MealHistoryApi(
      apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
      httpClient: MockClient((request) async {
        savedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(
            jsonEncode({
              'id': 4,
              'eaten_at': '2026-10-16T12:00:00+05:30',
              'meal_type': 'lunch',
              'note': null,
              'items': [],
              'totals': {
                'energy_kcal': 300,
                'carbohydrate_g': 45,
                'sugars_g': null,
                'dietary_fiber_g': 5,
                'protein_g': 13,
                'fat_g': 7,
                'sodium_mg': 310,
              },
            }),
            201);
      }),
    );
    await tester.pumpWidget(screenWith(
      (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200),
      historyApi: historyApi,
    ));
    await pickPhotoAndMealType(tester);
    await tester.tap(find.text('Review Photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Analyse meal'));
    await tester.pumpAndSettle();
    await openNutrition(tester);
    await tester.tap(find.text('View Nutrition Details'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Glycemic Profile'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Meal Summary'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save Meal'));
    await tester.pumpAndSettle();

    expect(find.text('Meal Saved'), findsOneWidget);
    expect(find.text('Meal saved to your demo meal history.'), findsOneWidget);
    expect(savedBody['meal_type'], 'lunch');
    expect(savedBody['items'], hasLength(2));
    expect(savedBody.toString(), isNot(contains('confidence')));
    expect(savedBody.toString(), isNot(contains('image')));
  });

  testWidgets('API errors return to scan with a friendly message',
      (tester) async {
    useTallView(tester);
    await tester.pumpWidget(screenWith((_) async => http.Response(
          jsonEncode({
            'error': {
              'code': 'IMAGE_UNREADABLE',
              'message': 'decoder failed',
              'details': [],
            },
          }),
          422,
        )));
    await pickPhotoAndMealType(tester);
    await tester.tap(find.text('Review Photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Analyse meal'));
    await tester.pumpAndSettle();
    expect(find.text('The photo could not be read. Please take a new photo.'),
        findsOneWidget);
    expect(find.text('decoder failed'), findsNothing);
    expect(find.text('Scan Meal'), findsOneWidget);
  });
}
