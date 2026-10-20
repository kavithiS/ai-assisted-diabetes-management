import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/auth/data/auth_api.dart';

import 'auth_test_support.dart';

void main() {
  test('login posts the credentials and returns the tokens', () async {
    final gateway = FakeGateway((_) => tokenResponse());

    final tokens =
        await gateway.api.login(email: '  me@example.test ', password: 'secret pass');

    expect(gateway.requests.single.method, 'POST');
    expect(gateway.requests.single.url.toString(),
        'http://gateway.test:8000/api/v1/auth/login');
    expect(gateway.requests.single.headers['Content-Type'], contains('application/json'));
    expect(gateway.bodyOf(0), {'email': 'me@example.test', 'password': 'secret pass'});
    expect(tokens.accessToken, 'access-1');
    expect(tokens.refreshToken, 'refresh-1');
    expect(tokens.expiresInSeconds, 900);
  });

  test('a wrong password gives the gateway code and message', () async {
    final gateway = FakeGateway((_) =>
        errorEnvelope(401, 'INVALID_CREDENTIALS', 'Wrong e-mail or password.'));

    await expectLater(
      gateway.api.login(email: 'me@example.test', password: 'nope'),
      throwsA(isA<AuthApiException>()
          .having((e) => e.code, 'code', 'INVALID_CREDENTIALS')
          .having((e) => e.message, 'message', 'Wrong e-mail or password.')),
    );
  });

  test('register posts the consent and expects 201', () async {
    final gateway = FakeGateway((_) => json(201, {'user_id': 'abc'}));

    await gateway.api.register(email: 'me@example.test', password: 'a long enough password');

    expect(gateway.requests.single.url.path, '/api/v1/auth/register');
    expect(gateway.bodyOf(0), {
      'email': 'me@example.test',
      'password': 'a long enough password',
      'consent_version': kConsentVersion,
      'accept': true,
    });
  });

  test('a closed registration gives the gateway message', () async {
    final gateway = FakeGateway(
        (_) => errorEnvelope(403, 'REGISTRATION_CLOSED', 'Registration is closed.'));

    await expectLater(
      gateway.api.register(email: 'me@example.test', password: 'a long enough password'),
      throwsA(isA<AuthApiException>()
          .having((e) => e.code, 'code', 'REGISTRATION_CLOSED')
          .having((e) => e.message, 'message', 'Registration is closed.')),
    );
  });

  test('validation errors keep the listed problems', () async {
    final gateway = FakeGateway((_) => errorEnvelope(
          422,
          'VALIDATION_ERROR',
          'The request is invalid.',
          details: [
            {'field': 'password', 'issue': 'String should have at least 10 characters'},
          ],
        ));

    await expectLater(
      gateway.api.register(email: 'me@example.test', password: 'short'),
      throwsA(isA<AuthApiException>().having(
          (e) => e.details, 'details', ['String should have at least 10 characters'])),
    );
  });

  test('an unreachable server gives a NETWORK error', () async {
    final api = AuthApi(
      apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
      httpClient: MockClient((_) async => throw http.ClientException('refused')),
    );

    await expectLater(api.login(email: 'a@b.co', password: 'x'),
        throwsA(isA<AuthApiException>().having((e) => e.code, 'code', 'NETWORK')));
  });

  test('a slow server gives a TIMEOUT error', () async {
    final api = AuthApi(
      apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
      httpClient: MockClient((_) => Completer<http.Response>().future),
      requestTimeout: const Duration(milliseconds: 20),
    );

    await expectLater(api.login(email: 'a@b.co', password: 'x'),
        throwsA(isA<AuthApiException>().having((e) => e.code, 'code', 'TIMEOUT')));
  });

  test('a reply that is not the error envelope never crashes', () async {
    final gateway = FakeGateway((_) => http.Response('<html>Bad gateway</html>', 502));

    await expectLater(
      gateway.api.login(email: 'a@b.co', password: 'x'),
      throwsA(isA<AuthApiException>()
          .having((e) => e.code, 'code', 'HTTP_502')
          .having((e) => e.message, 'message', isNotEmpty)),
    );
  });

  test('a malformed success reply gives BAD_RESPONSE', () async {
    final gateway = FakeGateway((_) => json(200, {'unexpected': true}));

    await expectLater(gateway.api.login(email: 'a@b.co', password: 'x'),
        throwsA(isA<AuthApiException>().having((e) => e.code, 'code', 'BAD_RESPONSE')));
  });
}
