import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/glucose/glucose_models.dart';

const _request = GlucoseForecastRequest(
  premealGlucose: 110,
  calories: 600,
  carbs: 70,
  protein: 25,
  fat: 20,
  fiber: 8,
);

Map<String, Object> _validResponse() => {
      'predictions': List<double>.generate(16, (i) => 100.0 + i),
      'horizon_minutes': List<int>.generate(16, (i) => (i + 1) * 15),
      'unit': 'mg/dL',
      'model_name': 'GRU',
      'model_version': 'test-version',
      'disclaimer': 'Research prediction.',
    };

/// Loopback HTTP server that answers every request with [status] and [body],
/// and records the last request it received.
class _StubServer {
  _StubServer._(this._server);

  final HttpServer _server;
  String? lastMethod;
  String? lastPath;
  Map<String, dynamic>? lastBody;

  int get port => _server.port;

  static Future<_StubServer> start(
      {required int status, required Object body}) async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final stub = _StubServer._(server);
    server.listen((request) async {
      stub.lastMethod = request.method;
      stub.lastPath = request.uri.path;
      final raw = await utf8.decoder.bind(request).join();
      if (raw.isNotEmpty) {
        stub.lastBody = jsonDecode(raw) as Map<String, dynamic>;
      }
      request.response
        ..statusCode = status
        ..headers.contentType = ContentType.json
        ..write(body is String ? body : jsonEncode(body));
      await request.response.close();
    });
    return stub;
  }

  Future<void> stop() => _server.close(force: true);
}

void main() {
  group('ApiClient.forecastGlucose', () {
    _StubServer? stub;

    tearDown(() async {
      await stub?.stop();
      stub = null;
    });

    test('POSTs the contract fields to the gateway and parses the response',
        () async {
      stub = await _StubServer.start(status: 200, body: _validResponse());
      final client = ApiClient(baseUrl: 'http://127.0.0.1:${stub!.port}');

      final forecast = await client.forecastGlucose(_request);
      client.close();

      expect(stub!.lastMethod, 'POST');
      expect(stub!.lastPath, '/api/v1/glucose/forecast');
      expect(stub!.lastBody, {
        'premeal_glucose': 110.0,
        'calories': 600.0,
        'carbs': 70.0,
        'protein': 25.0,
        'fat': 20.0,
        'fiber': 8.0,
      });
      expect(forecast.predictions, hasLength(16));
      expect(forecast.horizonMinutes.last, 240);
      expect(forecast.modelVersion, 'test-version');
    });

    test('decodes non-ASCII text in the response as UTF-8', () async {
      final body = _validResponse()
        ..['disclaimer'] = 'Research estimate — not a diagnosis.';
      stub = await _StubServer.start(status: 200, body: body);
      final client = ApiClient(baseUrl: 'http://127.0.0.1:${stub!.port}');

      final forecast = await client.forecastGlucose(_request);
      client.close();

      expect(forecast.disclaimer, 'Research estimate — not a diagnosis.');
    });

    test('shows a clear message when the backend cannot be reached', () async {
      // Bind and close a socket to get a loopback port that nothing listens on.
      final probe = await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
      final port = probe.port;
      await probe.close();
      final client = ApiClient(baseUrl: 'http://127.0.0.1:$port');

      await expectLater(
        client.forecastGlucose(_request),
        throwsA(
          isA<ApiException>().having(
            (e) => e.message,
            'message',
            contains('Cannot reach the DiaCare server'),
          ),
        ),
      );
      client.close();
    });

    test('maps a 503 from the model service to a model-unavailable message',
        () async {
      stub = await _StubServer.start(
        status: 503,
        body: {'detail': 'The C2 forecasting model is currently unavailable.'},
      );
      final client = ApiClient(baseUrl: 'http://127.0.0.1:${stub!.port}');

      await expectLater(
        client.forecastGlucose(_request),
        throwsA(
          isA<ApiException>()
              .having((e) => e.statusCode, 'statusCode', 503)
              .having((e) => e.message, 'message',
                  contains('model is unavailable')),
        ),
      );
      client.close();
    });

    test('maps a 502 from the gateway to a service-unavailable message',
        () async {
      stub = await _StubServer.start(
          status: 502, body: {'detail': 'Upstream service unavailable'});
      final client = ApiClient(baseUrl: 'http://127.0.0.1:${stub!.port}');

      await expectLater(
        client.forecastGlucose(_request),
        throwsA(
          isA<ApiException>()
              .having((e) => e.statusCode, 'statusCode', 502)
              .having((e) => e.message, 'message',
                  contains('forecasting service is unavailable')),
        ),
      );
      client.close();
    });

    test('maps a 422 validation error to a check-the-form message', () async {
      stub = await _StubServer.start(status: 422, body: {'detail': []});
      final client = ApiClient(baseUrl: 'http://127.0.0.1:${stub!.port}');

      await expectLater(
        client.forecastGlucose(_request),
        throwsA(
          isA<ApiException>().having(
            (e) => e.message,
            'message',
            contains('rejected these values'),
          ),
        ),
      );
      client.close();
    });

    test('includes the server detail for other errors', () async {
      stub = await _StubServer.start(status: 500, body: {'detail': 'boom'});
      final client = ApiClient(baseUrl: 'http://127.0.0.1:${stub!.port}');

      await expectLater(
        client.forecastGlucose(_request),
        throwsA(
          isA<ApiException>().having(
            (e) => e.message,
            'message',
            allOf(contains('HTTP 500'), contains('boom')),
          ),
        ),
      );
      client.close();
    });

    test('rejects a 200 response that is not JSON', () async {
      stub = await _StubServer.start(
          status: 200, body: '<html>proxy error</html>');
      final client = ApiClient(baseUrl: 'http://127.0.0.1:${stub!.port}');

      await expectLater(
        client.forecastGlucose(_request),
        throwsA(
          isA<ApiException>().having(
            (e) => e.message,
            'message',
            contains('could not read'),
          ),
        ),
      );
      client.close();
    });

    test('rejects a 200 response that does not match the contract', () async {
      final body = _validResponse()..['predictions'] = <double>[100, 101];
      stub = await _StubServer.start(status: 200, body: body);
      final client = ApiClient(baseUrl: 'http://127.0.0.1:${stub!.port}');

      await expectLater(
        client.forecastGlucose(_request),
        throwsA(
          isA<ApiException>().having(
            (e) => e.message,
            'message',
            contains('could not read'),
          ),
        ),
      );
      client.close();
    });
  });
}
