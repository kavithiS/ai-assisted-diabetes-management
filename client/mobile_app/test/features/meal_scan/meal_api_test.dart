import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/meal_scan/data/meal_analysis.dart';
import 'package:mobile_app/features/meal_scan/data/meal_api.dart';

import 'meal_scan_test_data.dart';

void main() {
  MealApi apiWith(MockClientHandler handler) => MealApi(
        apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
        httpClient: MockClient(handler),
      );

  test('sends a multipart request to the gateway and parses the response', () async {
    late http.Request sent;
    final api = apiWith((request) async {
      sent = request;
      return http.Response(jsonEncode(mockAnalysisJson()), 200);
    });

    final result = await api.analyze(imageBytes: tinyPng, mealType: MealType.lunch);

    expect(sent.method, 'POST');
    expect(sent.url.toString(), 'http://gateway.test:8000/api/v1/meals/analyze');
    final body = latin1.decode(sent.bodyBytes);
    expect(body, contains('name="meal_type"'));
    expect(body, contains('lunch'));
    expect(body, contains('name="captured_at"'));
    expect(body, contains('content-type: image/png'));

    expect(result.isMock, isTrue);
    expect(result.mealType, MealType.lunch);
    expect(result.items, hasLength(2));
    expect(result.items.first.portion.grams, 150);
    expect(result.totals.energyKcal, 300);
  });

  test('unknown nutrients stay null, never zero', () async {
    final api = apiWith((_) async => http.Response(jsonEncode(mockAnalysisJson()), 200));

    final result = await api.analyze(imageBytes: tinyPng, mealType: MealType.lunch);

    expect(result.items.first.nutrition.sugarsG, isNull);
    expect(result.totals.sugarsG, isNull);
  });

  test('maps the error envelope to a patient-friendly message', () async {
    final api = apiWith((_) async => http.Response(
          jsonEncode({
            'error': {'code': 'IMAGE_TOO_LARGE', 'message': 'internal detail', 'details': []},
            'request_id': 'r1',
          }),
          413,
        ));

    await expectLater(
      api.analyze(imageBytes: tinyPng, mealType: MealType.lunch),
      throwsA(isA<MealApiException>()
          .having((e) => e.code, 'code', 'IMAGE_TOO_LARGE')
          .having((e) => e.message, 'message', isNot(contains('internal detail')))),
    );
  });

  test('a non-JSON error body still gives a usable error', () async {
    final api = apiWith((_) async => http.Response('Bad Gateway', 502));

    await expectLater(
      api.analyze(imageBytes: tinyPng, mealType: MealType.lunch),
      throwsA(isA<MealApiException>().having((e) => e.code, 'code', 'HTTP_502')),
    );
  });

  test('rejects bytes that are not JPEG or PNG before calling the API', () async {
    var called = false;
    final api = apiWith((_) async {
      called = true;
      return http.Response('', 200);
    });

    await expectLater(
      api.analyze(imageBytes: Uint8List.fromList([1, 2, 3, 4]), mealType: MealType.snack),
      throwsA(isA<MealApiException>().having((e) => e.code, 'code', 'UNSUPPORTED_MEDIA_TYPE')),
    );
    expect(called, isFalse);
  });

  test('detects JPEG and PNG from the file bytes', () {
    expect(MealApi.detectImageType(Uint8List.fromList([0xFF, 0xD8, 0xFF, 0xE0]))?.mimeType,
        'image/jpeg');
    expect(MealApi.detectImageType(tinyPng)?.mimeType, 'image/png');
    expect(MealApi.detectImageType(Uint8List(0)), isNull);
  });

  test('formats captured_at as RFC 3339 with an offset', () {
    final formatted = MealApi.toRfc3339(DateTime(2026, 10, 3, 12, 30, 5));
    expect(formatted, matches(RegExp(r'^2026-10-03T12:30:05[+-]\d{2}:\d{2}$')));
  });

  test('NutrientProfile.sum is null for a nutrient unknown in any item', () {
    final total = NutrientProfile.sum(const [
      NutrientProfile(energyKcal: 100, sugarsG: null),
      NutrientProfile(energyKcal: 50, sugarsG: 2),
    ]);
    expect(total.energyKcal, 150);
    expect(total.sugarsG, isNull);
  });

  test('default analyzeTimeout is at least 60 seconds', () {
    expect(MealApi().analyzeTimeout.inSeconds, greaterThanOrEqualTo(60));
  });

  test('a network error gives code NETWORK with a user message', () async {
    final api = apiWith((_) async => throw http.ClientException('Connection refused'));

    await expectLater(
      api.analyze(imageBytes: tinyPng, mealType: MealType.snack),
      throwsA(isA<MealApiException>()
          .having((e) => e.code, 'code', 'NETWORK')
          .having((e) => e.message, 'message', isNotEmpty)),
    );
  });

  test('a timeout gives code TIMEOUT with a message telling the user to retry', () async {
    final api = MealApi(
      apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
      httpClient: MockClient((_) async {
        await Future<void>.delayed(const Duration(milliseconds: 10));
        return http.Response(jsonEncode(mockAnalysisJson()), 200);
      }),
      // Very short timeout so the test does not take 60 s.
      analyzeTimeout: const Duration(milliseconds: 1),
    );

    await expectLater(
      api.analyze(imageBytes: tinyPng, mealType: MealType.lunch),
      throwsA(isA<MealApiException>()
          .having((e) => e.code, 'code', 'TIMEOUT')
          .having((e) => e.message, 'message', isNotEmpty)),
    );
  });
}
