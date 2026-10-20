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
    await tester.tap(find.text('Analyze Meal'));
    await tester.pumpAndSettle();
  }

  // After showFoodReview we are on the recognition step.
  // openPortions advances: recognition → foods → portions.
  Future<void> openPortions(WidgetTester tester) async {
    await tester.tap(find.text('Confirm Detected Foods'));
    await tester.pumpAndSettle();
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
    // 'Review Photo' is hidden until both a photo and a meal type are selected.
    expect(find.widgetWithText(FilledButton, 'Review Photo'), findsNothing);
    await tester.tap(find.text('Upload Image'));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(FilledButton, 'Review Photo'), findsNothing);
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

  testWidgets('recognition shows foods without confidence values',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    expect(find.text('Detected Foods'), findsOneWidget);
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
    expect(find.text('300 kcal', findRichText: true), findsOneWidget);
  });

  testWidgets('removing a food updates nutrition totals', (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await tester.tap(find.text('Confirm Detected Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.close).first);
    await tester.pumpAndSettle();
    expect(find.text('Test Food A'), findsNothing);
    await tester.tap(find.text('Confirm Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Nutrition'));
    await tester.pumpAndSettle();
    expect(find.text('100 kcal', findRichText: true), findsOneWidget);
  });

  testWidgets('chip-based portions rescale nutrients', (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await openPortions(tester);
    // Test Food A is 150 g; Larger chip = 225 g (1.5×)
    await tester.tap(find.text('Larger (225 g)'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Nutrition'));
    await tester.pumpAndSettle();
    // 200 kcal × 1.5 + 100 kcal = 400 kcal
    expect(find.text('400 kcal', findRichText: true), findsOneWidget);
  });

  testWidgets('food editor shows category chips and saves a name change',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await tester.tap(find.text('Confirm Detected Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.edit_outlined).first);
    await tester.pumpAndSettle();
    expect(find.text('Edit Food'), findsOneWidget);
    await tester.tap(find.text('Rice'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save Changes'));
    await tester.pumpAndSettle();
    expect(find.text('Confirm Detected Foods'), findsOneWidget);
  });

  testWidgets('glycemic profile and recommendation screens are reachable',
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
    expect(find.text('GLYCEMIC LOAD'), findsOneWidget);
    await tester.tap(find.text('Continue to Meal Summary'));
    await tester.pumpAndSettle();
    expect(find.text('Meal Analysis Complete'), findsOneWidget);
    await tester.tap(find.text('View Portion Recommendation'));
    await tester.pumpAndSettle();
    expect(find.text('Portion Recommendation'), findsOneWidget);
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
    await tester.tap(find.text('Analyze Meal'));
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

    expect(find.textContaining('Meal Saved'), findsOneWidget);
    expect(find.text('Meal saved to your history.'), findsOneWidget);
    expect(savedBody['meal_type'], 'lunch');
    expect(savedBody['eaten_at'] as String, matches(RegExp(r'[+-]\d\d:\d\d$')),
        reason: 'the server rejects times without a UTC offset');
    expect(savedBody['items'], hasLength(2));
    expect(savedBody.toString(), isNot(contains('confidence')));
    expect(savedBody.toString(), isNot(contains('image')));
  });

  /// Like the trained model's answer: real table values, one food with no table entry.
  Map<String, dynamic> realAnalysisWithUnknownFood() {
    final json = mockAnalysisJson();
    final items = json['items'] as List<dynamic>;
    (items[0] as Map<String, dynamic>)
      ..['label'] = 'white_rice'
      ..['nutrition_source'] = {'source': 'MRI_SL_FCDB', 'source_food_id': 'SL_6'};
    (items[1] as Map<String, dynamic>)
      ..['label'] = 'brinjal_dish'
      ..['nutrition'] = {
        for (final k in [
          'energy_kcal', 'carbohydrate_g', 'sugars_g', 'dietary_fiber_g',
          'protein_g', 'fat_g', 'sodium_mg'
        ])
          k: null,
      }
      ..['nutrition_source'] = null;
    json['totals'] = {
      for (final k in (json['totals'] as Map<String, dynamic>).keys) k: null,
    };
    return json;
  }

  testWidgets('a food without nutrition data gives "Not available", never 0',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(realAnalysisWithUnknownFood()), 200));
    expect(find.text('AI matched 2 Sri Lankan dishes'), findsOneWidget);
    expect(find.text('White rice'), findsOneWidget);
    expect(find.text('Brinjal dish'), findsOneWidget);
    expect(find.textContaining('Demo data'), findsNothing);
    expect(find.textContaining('Portions are not measured'), findsOneWidget);

    await openNutrition(tester);
    expect(find.textContaining('No nutrition data for Brinjal dish'), findsOneWidget);
    expect(find.text('Not available', findRichText: true), findsNWidgets(4));
    expect(find.text('0 g'), findsNothing);
    expect(find.textContaining('0 kcal', findRichText: true), findsNothing);
  });

  testWidgets('removing the unknown food shows the totals of the rest',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(realAnalysisWithUnknownFood()), 200));
    await tester.tap(find.text('Confirm Detected Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.close).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Confirm Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Nutrition'));
    await tester.pumpAndSettle();
    expect(find.text('200 kcal', findRichText: true), findsOneWidget);
    expect(find.textContaining('No nutrition data'), findsNothing);
  });

  testWidgets('no invented glycemic values, recommendations or confidence',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await openNutrition(tester);
    expect(find.text('Moderate'), findsNothing);
    await tester.tap(find.text('View Nutrition Details'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Glycemic Profile'));
    await tester.pumpAndSettle();
    expect(find.text('18.6'), findsNothing);
    expect(find.text('Medium'), findsNothing);
    await tester.tap(find.text('Continue to Meal Summary'));
    await tester.pumpAndSettle();
    expect(find.textContaining('18.6'), findsNothing);
    expect(find.textContaining('Confidence'), findsNothing);
    await tester.tap(find.text('View Portion Recommendation'));
    await tester.pumpAndSettle();
    expect(find.textContaining('cup rice'), findsNothing);
    expect(find.text('Portion recommendations are not available yet.'),
        findsOneWidget);
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
    await tester.tap(find.text('Analyze Meal'));
    await tester.pumpAndSettle();
    expect(find.text('The photo could not be read. Please take a new photo.'),
        findsOneWidget);
    expect(find.text('decoder failed'), findsNothing);
    expect(find.text('Scan Meal'), findsOneWidget);
  });
}
