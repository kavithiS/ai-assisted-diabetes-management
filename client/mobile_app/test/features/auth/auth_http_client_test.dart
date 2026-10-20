import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/auth/data/auth_api.dart';
import 'package:mobile_app/features/auth/data/auth_http_client.dart';
import 'package:mobile_app/features/auth/data/auth_tokens.dart';

import 'auth_test_support.dart';

AuthTokens _tokens(String access, String refresh, {int expiresIn = 900}) =>
    AuthTokens(accessToken: access, refreshToken: refresh, expiresInSeconds: expiresIn);

void main() {
  final requests = <http.Request>[];
  late http.Response Function(http.Request) handler;

  AuthHttpClient clientFor(AuthSession session) {
    final inner = MockClient((request) async {
      requests.add(request);
      return handler(request);
    });
    return AuthHttpClient(
      session: session,
      inner: inner,
      authApi: AuthApi(
        apiClient: ApiClient(baseUrl: 'http://gateway.test:8000'),
        httpClient: inner,
      ),
    );
  }

  setUp(() {
    requests.clear();
    handler = (_) => json(200, {'ok': true});
  });

  test('adds the access token to every request', () async {
    final session = AuthSession();
    await session.signIn(_tokens('access-1', 'refresh-1'));

    await clientFor(session).get(Uri.parse('http://gateway.test:8000/api/v1/meals'));

    expect(requests.single.headers['Authorization'], 'Bearer access-1');
  });

  test('sends no Authorization header when signed out', () async {
    await clientFor(AuthSession()).get(Uri.parse('http://gateway.test:8000/api/v1/meals'));

    expect(requests.single.headers.containsKey('Authorization'), isFalse);
  });

  test('refreshes an expiring token once, even for parallel requests', () async {
    final session = AuthSession();
    await session.signIn(_tokens('old-access', 'old-refresh', expiresIn: 30));
    handler = (request) => request.url.path == '/api/v1/auth/refresh'
        ? tokenResponse()
        : json(200, {'ok': true});
    final client = clientFor(session);

    await Future.wait([
      client.get(Uri.parse('http://gateway.test:8000/api/v1/meals')),
      client.get(Uri.parse('http://gateway.test:8000/api/v1/meals/summary')),
    ]);

    final refreshes = requests.where((r) => r.url.path == '/api/v1/auth/refresh');
    expect(refreshes, hasLength(1));
    expect(refreshes.single.body, contains('old-refresh'));
    final calls = requests.where((r) => r.url.path != '/api/v1/auth/refresh');
    expect(calls.map((r) => r.headers['Authorization']),
        everyElement('Bearer access-1'));
    expect(session.tokens!.refreshToken, 'refresh-1');
  });

  test('a rejected refresh token signs the user out', () async {
    final session = AuthSession();
    await session.signIn(_tokens('old-access', 'old-refresh', expiresIn: 30));
    handler = (request) => request.url.path == '/api/v1/auth/refresh'
        ? errorEnvelope(401, 'UNAUTHORIZED', 'Invalid or expired refresh token.')
        : errorEnvelope(401, 'UNAUTHORIZED', 'Not signed in.');

    final response = await clientFor(session)
        .get(Uri.parse('http://gateway.test:8000/api/v1/meals'));

    expect(session.isSignedIn, isFalse);
    expect(response.statusCode, 401);
    expect(requests.last.headers.containsKey('Authorization'), isFalse);
  });

  test('a refresh that cannot reach the server keeps the tokens', () async {
    final session = AuthSession();
    await session.signIn(_tokens('old-access', 'old-refresh', expiresIn: 30));
    handler = (_) => throw http.ClientException('refused');

    await expectLater(
      clientFor(session).get(Uri.parse('http://gateway.test:8000/api/v1/meals')),
      throwsA(isA<http.ClientException>()),
    );
    expect(session.tokens!.refreshToken, 'old-refresh');
  });
}
