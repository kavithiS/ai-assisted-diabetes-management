import 'dart:async';
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

  Future<void> finishAnalysis(WidgetTester tester) async {
    await tester.pump();
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 250));
    }
    await tester.pump(const Duration(milliseconds: 350));
    await tester.pumpAndSettle();
  }

  Future<void> showFoodReview(
      WidgetTester tester, MockClientHandler handler) async {
    await tester.pumpWidget(screenWith(handler));
    await pickPhotoAndMealType(tester);
    await tester.tap(find.text('Review Photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Analyze Meal'));
    await finishAnalysis(tester);
  }

  // After showFoodReview we are on the recognition step.
  // openPortions advances: recognition → foods → portions.
  Future<void> openPortions(WidgetTester tester) async {
    final demoButton = find.text('Review Demo Foods');
    await tester.tap(demoButton.evaluate().isNotEmpty
        ? demoButton
        : find.text('Review Detected Foods'));
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

  testWidgets('analysis waits for the response before ticking and leaving',
      (tester) async {
    useTallView(tester);
    final response = Completer<http.Response>();
    await tester.pumpWidget(screenWith((_) => response.future));
    await pickPhotoAndMealType(tester);
    await tester.tap(find.text('Review Photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Analyze Meal'));
    await tester.pump();
    await tester.pump(const Duration(seconds: 3));

    expect(find.text('Analysing Your Meal'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle_outline), findsNothing);
    expect(find.text('Demo Analysis'), findsNothing);

    response.complete(http.Response(jsonEncode(mockAnalysisJson()), 200));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 250));
    expect(find.byIcon(Icons.check_circle_outline), findsOneWidget);
    await finishAnalysis(tester);
    expect(find.text('Demo Analysis'), findsOneWidget);
  });

  testWidgets('system back from photo review returns to scan', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(screenWith((_) async => http.Response('', 500)));
    await pickPhotoAndMealType(tester);
    await tester.tap(find.text('Review Photo'));
    await tester.pumpAndSettle();

    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();

    expect(find.text('Scan Meal'), findsOneWidget);
    expect(find.text('Review Meal'), findsNothing);
  });

  testWidgets('back from detected foods returns to scan', (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));

    expect(find.text('Demo Analysis'), findsOneWidget);
    expect(find.byTooltip('Back'), findsOneWidget);
    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();

    expect(find.text('Scan Meal'), findsOneWidget);
    expect(find.text('Demo Analysis'), findsNothing);
  });

  testWidgets('recognition shows foods without confidence values',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    expect(find.text('Demo Analysis'), findsOneWidget);
    expect(find.text('Test Food A'), findsOneWidget);
    expect(find.text('Test Food B'), findsOneWidget);
    expect(find.textContaining('Demo analysis'), findsNWidgets(2));
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
    await tester.tap(find.text('Review Demo Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.close).first);
    await tester.pumpAndSettle();
    expect(find.text('Test Food A'), findsNothing);
    await tester.tap(find.text('Confirm Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Nutrition'));
    await tester.pumpAndSettle();
    expect(find.text('100 kcal', findRichText: true), findsWidgets);
  });

  testWidgets('nutrition details show source and close-match warning',
      (tester) async {
    useTallView(tester);
    final json = mockAnalysisJson();
    (json['meta'] as Map<String, dynamic>)['warnings'] = [
      "'Test Food A': nutrition from table entry SL_70 (close match: Beans Curry; the recipe may differ)",
    ];
    await showFoodReview(
        tester, (_) async => http.Response(jsonEncode(json), 200));
    await openNutrition(tester);
    await tester.tap(find.text('Demo analysis — values are placeholders'));
    await tester.pumpAndSettle();
    expect(find.textContaining('close match: Beans Curry'), findsOneWidget);
    await tester.tap(find.text('View Nutrition Details'));
    await tester.pumpAndSettle();
    expect(
        find.textContaining('Source: Placeholder (demo data)'), findsWidgets);
    expect(find.textContaining('close match: Beans Curry'), findsOneWidget);
    expect(find.text('Fibre'), findsWidgets);
    expect(find.text('Sugars'), findsWidgets);
    expect(find.text('Sodium'), findsWidgets);
    expect(find.text('Not available'), findsWidgets);
  });

  testWidgets('chip-based portions rescale nutrients', (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await openPortions(tester);
    // Presets always use the original 150 g, even after another preset.
    await tester.tap(find.text('Smaller (75 g)'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Larger (225 g)'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Nutrition'));
    await tester.pumpAndSettle();
    // 200 kcal × 1.5 + 100 kcal = 400 kcal
    expect(find.text('400 kcal', findRichText: true), findsOneWidget);
  });

  testWidgets('food editor saves a name change without stale nutrition',
      (tester) async {
    useTallView(tester);
    await showFoodReview(tester,
        (_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));
    await tester.tap(find.text('Review Demo Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.edit_outlined).first);
    await tester.pumpAndSettle();
    expect(find.text('Edit Food'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'Home recipe');
    await tester.tap(find.text('Save Changes'));
    await tester.pumpAndSettle();
    expect(find.text('Review Demo Foods'), findsOneWidget);
    expect(find.text('Home recipe'), findsOneWidget);
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
    await finishAnalysis(tester);
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
    // The backend marks the whole response as mock while portion estimation is
    // fixed, even when food recognition comes from the trained model.
    (json['meta'] as Map<String, dynamic>)['is_mock'] = true;
    (json['meta'] as Map<String, dynamic>)['model_name'] =
        'mobilenet_v3_large-multilabel';
    final items = json['items'] as List<dynamic>;
    (items[0] as Map<String, dynamic>)
      ..['label'] = 'white_rice'
      ..['nutrition_source'] = {
        'source': 'MRI_SL_FCDB',
        'source_food_id': 'SL_6'
      };
    (items[1] as Map<String, dynamic>)
      ..['label'] = 'brinjal_dish'
      ..['nutrition'] = {
        for (final k in [
          'energy_kcal',
          'carbohydrate_g',
          'sugars_g',
          'dietary_fiber_g',
          'protein_g',
          'fat_g',
          'sodium_mg'
        ])
          k: null,
      }
      ..['nutrition_source'] = null;
    json['totals'] = {
      for (final k in (json['totals'] as Map<String, dynamic>).keys) k: null,
    };
    return json;
  }

  testWidgets('unknown food shows only a clearly labelled reported subtotal',
      (tester) async {
    useTallView(tester);
    await showFoodReview(
        tester,
        (_) async =>
            http.Response(jsonEncode(realAnalysisWithUnknownFood()), 200));
    expect(find.text('AI matched 2 Sri Lankan dishes'), findsOneWidget);
    expect(find.text('White rice'), findsOneWidget);
    expect(find.text('Brinjal dish'), findsOneWidget);
    expect(find.textContaining('Demo data'), findsNothing);
    expect(find.text('Review the estimated portions'), findsOneWidget);

    await openNutrition(tester);
    await tester.tap(find.text('Review the estimated portions'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Missing nutrient data for Brinjal dish'),
        findsOneWidget);
    expect(find.textContaining('full meal total is not available'),
        findsOneWidget);
    expect(find.text('ESTIMATED CALORIES FROM REPORTED FOODS'), findsOneWidget);
    expect(find.text('200 kcal', findRichText: true), findsWidgets);
    expect(find.text('Reported carbohydrates'), findsOneWidget);
    expect(find.text('0 g'), findsNothing);

    await tester.tap(find.text('View Nutrition Details'));
    await tester.pumpAndSettle();
    final partialHeading = find.text('REPORTED-FOOD SUBTOTAL (INCOMPLETE)');
    await tester.scrollUntilVisible(partialHeading, 400,
        scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    expect(partialHeading, findsOneWidget);
    expect(find.text('200 kcal'), findsWidgets);

    await tester.tap(find.text('Continue to Glycemic Profile'));
    await tester.pumpAndSettle();
    expect(find.text('REPORTED CARBS'), findsOneWidget);
    expect(find.text('GLYCEMIC INDEX'), findsOneWidget);
    expect(find.text('Not available'), findsNWidgets(2));

    await tester.tap(find.text('Continue to Meal Summary'));
    await tester.pumpAndSettle();
    expect(find.text('REPORTED-FOOD SUBTOTAL (INCOMPLETE)'), findsOneWidget);
    expect(find.text('200 kcal'), findsOneWidget);
  });

  testWidgets('model labels are shown as readable names', (tester) async {
    useTallView(tester);
    final json = realAnalysisWithUnknownFood();
    ((json['items'] as List<dynamic>)[0] as Map<String, dynamic>)['label'] = 'pappadam';
    await showFoodReview(
        tester, (_) async => http.Response(jsonEncode(json), 200));
    expect(find.text('Pappadam'), findsOneWidget);
    expect(find.text('pappadam'), findsNothing);
  });

  testWidgets('removing the unknown food shows the totals of the rest',
      (tester) async {
    useTallView(tester);
    await showFoodReview(
        tester,
        (_) async =>
            http.Response(jsonEncode(realAnalysisWithUnknownFood()), 200));
    await tester.tap(find.text('Review Detected Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.close).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Confirm Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Nutrition'));
    await tester.pumpAndSettle();
    expect(find.text('200 kcal', findRichText: true), findsWidgets);
    expect(find.textContaining('Missing nutrient data'), findsNothing);
  });

  testWidgets('brinjal dish can be corrected to the exact curry table row',
      (tester) async {
    useTallView(tester);
    String? searched;
    final historyApi = MealHistoryApi(
      apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
      httpClient: MockClient((request) async {
        searched = request.url.queryParameters['q'];
        return http.Response(
            jsonEncode({
              'foods': [
                {
                  'id': 71,
                  'name': 'Brinjal Curry',
                  'name_si': null,
                  'name_ta': null,
                  'category': 'Cooked Dishes',
                  'source': 'MRI_SL_FCDB',
                  'per_100g': {
                    'energy_kcal': 49.45,
                    'carbohydrate_g': 3.78,
                    'sugars_g': null,
                    'dietary_fiber_g': 2.35,
                    'protein_g': 1.27,
                    'fat_g': 2.43,
                    'sodium_mg': 516.9,
                  },
                }
              ]
            }),
            200);
      }),
    );
    await tester.pumpWidget(screenWith(
      (_) async =>
          http.Response(jsonEncode(realAnalysisWithUnknownFood()), 200),
      historyApi: historyApi,
    ));
    await pickPhotoAndMealType(tester);
    await tester.tap(find.text('Review Photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Analyze Meal'));
    await finishAnalysis(tester);
    await tester.tap(find.text('Review Detected Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.edit_outlined).at(1));
    await tester.pumpAndSettle();
    expect(find.text('Edit Food'), findsOneWidget);
    await tester.tap(find.text('Choose a food with nutrition data'));
    await tester.pumpAndSettle();
    expect(searched, 'Brinjal');
    await tester.tap(find.text('Brinjal Curry'));
    await tester.pumpAndSettle();
    expect(find.text('Brinjal Curry'), findsOneWidget);
    await tester.tap(find.text('Confirm Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Nutrition'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Missing nutrient data'), findsNothing);
    expect(find.text('Brinjal Curry'), findsOneWidget);
  });

  testWidgets('no recognised foods leads to an add-food recovery path',
      (tester) async {
    useTallView(tester);
    final result = realAnalysisWithUnknownFood();
    result['items'] = [];
    await showFoodReview(
        tester, (_) async => http.Response(jsonEncode(result), 200));
    expect(find.text('No foods recognised'), findsOneWidget);
    expect(find.text('Add Foods'), findsOneWidget);
    await tester.tap(find.text('Add Foods'));
    await tester.pumpAndSettle();
    expect(find.text('Add from food database'), findsOneWidget);
    expect(find.text('Add an unlisted food'), findsOneWidget);
    expect(
        tester
            .widget<FilledButton>(
                find.widgetWithText(FilledButton, 'Confirm Foods'))
            .onPressed,
        isNull);
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
