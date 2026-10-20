import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/foot_monitor/data/foot_analysis.dart';
import 'package:mobile_app/features/foot_monitor/data/foot_api.dart';

import 'foot_test_data.dart';

void main() {
  FootApi apiWith(MockClientHandler handler, {Duration? timeout}) => FootApi(
        apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
        httpClient: MockClient(handler),
        timeout: timeout,
      );

  test('sends a multipart request to the gateway and parses the response', () async {
    late http.Request sent;
    final api = apiWith((request) async {
      sent = request;
      return http.Response(jsonEncode(footAnalysisJson()), 200);
    });

    final result = await api.analyze(imageBytes: tinyPng);

    expect(sent.method, 'POST');
    expect(sent.url.toString(), 'http://gateway.test:8000/api/v1/foot/analyze');
    final body = latin1.decode(sent.bodyBytes);
    expect(body, contains('name="image"'));
    expect(body, contains('content-type: image/png'));

    expect(result.riskBand, FootRiskBand.high);
    expect(result.classification, 'ulcer');
    expect(result.recommendations, hasLength(2));
    expect(result.isMock, isTrue);
  });

  test('rejects a file that is not JPEG or PNG before sending', () async {
    var called = false;
    final api = apiWith((_) async {
      called = true;
      return http.Response('{}', 200);
    });

    await expectLater(
      api.analyze(imageBytes: Uint8List.fromList(utf8.encode('GIF89a'))),
      throwsA(isA<FootApiException>()
          .having((e) => e.code, 'code', 'UNSUPPORTED_MEDIA_TYPE')),
    );
    expect(called, isFalse);
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
      api.analyze(imageBytes: tinyPng),
      throwsA(isA<FootApiException>()
          .having((e) => e.code, 'code', 'IMAGE_TOO_LARGE')
          .having((e) => e.message, 'message', isNot(contains('internal detail')))),
    );
  });

  test('a non-JSON error page keeps the HTTP status as the code', () async {
    final api = apiWith((_) async => http.Response('<html>Bad gateway</html>', 502));

    await expectLater(
      api.analyze(imageBytes: tinyPng),
      throwsA(isA<FootApiException>().having((e) => e.code, 'code', 'HTTP_502')),
    );
  });

  test('a malformed success response becomes BAD_RESPONSE', () async {
    final api = apiWith((_) async => http.Response('{"risk_band": "Unknown"}', 200));

    await expectLater(
      api.analyze(imageBytes: tinyPng),
      throwsA(isA<FootApiException>().having((e) => e.code, 'code', 'BAD_RESPONSE')),
    );
  });

  test('a network failure becomes NETWORK', () async {
    final api = apiWith((_) async => throw http.ClientException('offline'));

    await expectLater(
      api.analyze(imageBytes: tinyPng),
      throwsA(isA<FootApiException>().having((e) => e.code, 'code', 'NETWORK')),
    );
  });

  test('a slow server becomes TIMEOUT', () async {
    final api = apiWith(
      (_) => Completer<http.Response>().future,
      timeout: const Duration(milliseconds: 10),
    );

    await expectLater(
      api.analyze(imageBytes: tinyPng),
      throwsA(isA<FootApiException>().having((e) => e.code, 'code', 'TIMEOUT')),
    );
  });

  test('parses every risk band and rejects unknown ones', () {
    for (final band in FootRiskBand.values) {
      final parsed = FootAnalysis.fromJson(footAnalysisJson(riskBand: band.apiValue));
      expect(parsed.riskBand, band);
    }
    expect(() => FootRiskBand.parse('Severe'), throwsFormatException);
  });
}
