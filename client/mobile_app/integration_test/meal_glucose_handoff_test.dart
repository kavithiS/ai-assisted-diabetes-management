import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/meal_scan/data/meal_api.dart';
import 'package:mobile_app/features/meal_scan/meal_scan_screen.dart';

import '../test/features/meal_scan/meal_scan_test_data.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('reviewed scan nutrition reaches the glucose forecast on Android',
      (tester) async {
    final analysis = mockAnalysisJson();
    (analysis['meta'] as Map<String, dynamic>)
      ..['model_name'] = 'mobilenet_v3_large-multilabel'
      ..['warnings'] = <String>[];
    for (final item in analysis['items'] as List<dynamic>) {
      (item as Map<String, dynamic>)['nutrition_source'] = {
        'source': 'MRI_SL_FCDB',
        'source_food_id': 'synthetic-test-row',
      };
    }

    Map<String, dynamic>? forecastBody;
    final glucoseApi = ApiClient(
      baseUrl: 'http://gateway.test:8000',
      httpClient: MockClient((request) async {
        forecastBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(
          jsonEncode({
            'predictions': List<double>.generate(16, (i) => 110.0 + i),
            'horizon_minutes': List<int>.generate(16, (i) => (i + 1) * 15),
            'unit': 'mg/dL',
            'model_name': 'Synthetic test model',
            'model_version': 'test',
            'disclaimer': 'Synthetic test response.',
          }),
          200,
        );
      }),
    );
    addTearDown(glucoseApi.close);

    await tester.pumpWidget(MaterialApp(
      home: MealScanScreen(
        api: MealApi(
          apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
          httpClient:
              MockClient((_) async => http.Response(jsonEncode(analysis), 200)),
        ),
        glucoseApi: glucoseApi,
        pickImage: (_) async => tinyPng,
      ),
    ));

    await tester.tap(find.text('Upload Image'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Lunch'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Review Photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Analyze Meal'));
    await tester.pump();
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 250));
    }
    await tester.pumpAndSettle();
    await tester.tap(find.text('Review Detected Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Confirm Foods'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Nutrition'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('View Nutrition Details'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue to Glycemic Profile'));
    await tester.pumpAndSettle();

    expect(find.text('Glucose Forecast'), findsOneWidget);
    expect(forecastBody, isNull);
    await tester.enterText(find.byType(TextFormField).first, '110');
    await tester.ensureVisible(find.text('Get 4-hour estimate'));
    await tester.tap(find.text('Get 4-hour estimate'));
    await tester.pumpAndSettle();

    expect(forecastBody, {
      'premeal_glucose': 110.0,
      'calories': 300.0,
      'carbs': 45.0,
      'protein': 13.0,
      'fat': 7.0,
      'fiber': 5.0,
    });
    expect(find.text('Estimated glucose, next 4 hours'), findsOneWidget);
  });
}
