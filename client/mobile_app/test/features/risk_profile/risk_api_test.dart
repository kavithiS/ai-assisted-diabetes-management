import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/risk_profile/data/risk_api.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_assessment.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_presets.dart';

import 'fakes.dart';

RiskApi apiAnswering(
  Future<http.Response> Function(http.Request request) handler, {
  bool researcherMode = false,
  Duration timeout = const Duration(seconds: 10),
}) =>
    RiskApi(
      client: ApiClient(baseUrl: 'http://localhost:8000'),
      httpClient: MockClient(handler),
      researcherMode: researcherMode,
      timeout: timeout,
    );

void main() {
  test('posts the profile as JSON to the gateway route and parses the answer', () async {
    late http.Request seen;
    final api = apiAnswering((request) async {
      seen = request;
      return http.Response(jsonEncode(okJson()), 200);
    });

    final assessment = await api.assess(higherRiskPreset.profile);

    expect(seen.method, 'POST');
    expect(seen.url.toString(), 'http://localhost:8000/api/v1/risk/assess');
    expect(jsonDecode(seen.body), higherRiskPreset.profile.toJson());
    expect(assessment.band, RiskBand.high);
  });

  test('researcher mode adds ?debug=true; normal mode never does', () async {
    final urls = <Uri>[];
    Future<http.Response> handler(http.Request request) async {
      urls.add(request.url);
      return http.Response(jsonEncode(okJson()), 200);
    }

    await apiAnswering(handler).assess(lowerRiskPreset.profile);
    await apiAnswering(handler, researcherMode: true).assess(lowerRiskPreset.profile);

    expect(urls[0].query, isEmpty);
    expect(urls[1].queryParameters, {'debug': 'true'});
  });

  test('503 means the model is not loaded', () async {
    final api = apiAnswering((_) async => http.Response('{"detail": "not loaded"}', 503));
    expect(
      () => api.assess(lowerRiskPreset.profile),
      throwsA(isA<RiskApiException>().having((e) => e.kind, 'kind', RiskApiErrorKind.notReady)),
    );
  });

  test('502 from the gateway means C3 is unreachable', () async {
    final api = apiAnswering((_) async => http.Response('{}', 502));
    expect(
      () => api.status(),
      throwsA(isA<RiskApiException>().having((e) => e.kind, 'kind', RiskApiErrorKind.gateway)),
    );
  });

  test('an assessment may take up to 30 s (cold start); other calls keep 10 s', () {
    final api = RiskApi(client: ApiClient(baseUrl: 'http://localhost:8000'));
    expect(api.timeout, const Duration(seconds: 10));
    expect(api.assessTimeout, const Duration(seconds: 30));
  });

  test('a slow server times out instead of hanging', () async {
    final api = apiAnswering(
      (_) => Completer<http.Response>().future,
      timeout: const Duration(milliseconds: 50),
    );
    expect(
      () => api.assess(lowerRiskPreset.profile),
      throwsA(isA<RiskApiException>().having((e) => e.kind, 'kind', RiskApiErrorKind.timeout)),
    );
  });

  test('a network failure is reported, never replaced by demo data', () async {
    final api = apiAnswering((_) async => throw http.ClientException('refused'));
    expect(
      () => api.assess(lowerRiskPreset.profile),
      throwsA(isA<RiskApiException>().having((e) => e.kind, 'kind', RiskApiErrorKind.network)),
    );
    expect(api.isDemoData, isFalse);
  });

  test('the device pseudonym goes in the X-Device-Id header, never in the URL', () async {
    late http.Request seen;
    final api = RiskApi(
      client: ApiClient(baseUrl: 'http://localhost:8000'),
      deviceId: '0123456789abcdef0123456789abcdef',
      httpClient: MockClient((request) async {
        seen = request;
        return http.Response(jsonEncode({...okJson(), 'saved': true}), 200);
      }),
    );

    final assessment = await api.assess(lowerRiskPreset.profile);

    expect(seen.headers['X-Device-Id'], '0123456789abcdef0123456789abcdef');
    expect(seen.url.query, isEmpty);
    expect(assessment.saved, isTrue);
  });

  test('history and delete use the server and parse its answers', () async {
    final api = RiskApi(
      client: ApiClient(baseUrl: 'http://localhost:8000'),
      deviceId: '0123456789abcdef0123456789abcdef',
      httpClient: MockClient((request) async {
        expect(request.url.path, '/api/v1/risk/history');
        if (request.method == 'DELETE') {
          return http.Response('{"deleted_assessments": 2}', 200);
        }
        return http.Response(
          jsonEncode({
            'items': [
              {
                'id': 'a',
                'assessed_at': '2026-10-19T10:00:00Z',
                'status': 'ok',
                'risk_category': 'High',
                'model_version': '2026-10-10',
                'schema_version': '0.1',
              },
            ],
          }),
          200,
        );
      }),
    );

    final items = await api.history();
    expect(items.single.band, RiskBand.high);
    expect(items.single.schemaVersion, '0.1');
    expect(await api.deleteMyRecords(), 2);
  });

  test('a stopped database (503) is reported with the server message', () async {
    final api = apiAnswering(
      (_) async => http.Response('{"detail": "C3 database is unreachable."}', 503),
    );
    expect(
      () => api.history(),
      throwsA(isA<RiskApiException>()
          .having((e) => e.message, 'message', 'C3 database is unreachable.')),
    );
  });

  test('status parses model_loaded and the models', () async {
    final api = apiAnswering(
      (_) async => http.Response(
        jsonEncode({
          'model_loaded': true,
          'models': {'without_glucose': 'logistic_regression', 'with_glucose': 'random_forest'},
        }),
        200,
      ),
    );
    final status = await api.status();
    expect(status.modelLoaded, isTrue);
    expect(status.models['with_glucose'], 'random_forest');
  });
}
