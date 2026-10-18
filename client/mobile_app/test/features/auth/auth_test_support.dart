import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/auth/data/account_api.dart';
import 'package:mobile_app/features/auth/data/auth_api.dart';
import 'package:mobile_app/features/auth/data/auth_tokens.dart';

/// A fake gateway: answers each request with [handler] and records what it was sent.
class FakeGateway {
  FakeGateway(this.handler);

  final http.Response Function(http.Request request) handler;
  final List<http.Request> requests = [];

  late final MockClient _client = MockClient((request) async {
    requests.add(request);
    return handler(request);
  });

  final ApiClient _apiClient = ApiClient(baseUrl: 'http://gateway.test:8000');

  AuthApi get api => AuthApi(apiClient: _apiClient, httpClient: _client);

  AccountApi accountApi(AuthSession session) =>
      AccountApi(apiClient: _apiClient, httpClient: _client, session: session);

  Map<String, dynamic> bodyOf(int index) =>
      jsonDecode(requests[index].body) as Map<String, dynamic>;
}

http.Response json(int status, Object body) => http.Response(
      jsonEncode(body),
      status,
      headers: const {'content-type': 'application/json'},
    );

http.Response errorEnvelope(int status, String code, String message,
        {List<Map<String, String?>> details = const []}) =>
    json(status, {
      'error': {'code': code, 'message': message, 'details': details},
      'request_id': 'req-1',
    });

http.Response meResponse({String email = 'me@example.test', String? displayName}) =>
    json(200, {
      'user_id': '11111111-1111-4111-8111-111111111111',
      'email': email,
      'display_name': displayName,
      'role': 'patient',
      'created_at': '2026-10-18T10:00:00+05:30',
    });

/// A session that is already signed in.
Future<AuthSession> signedInSession() async {
  final session = AuthSession();
  await session.signIn(const AuthTokens(
      accessToken: 'access-1', refreshToken: 'refresh-1', expiresInSeconds: 900));
  return session;
}

http.Response tokenResponse() => json(200, {
      'access_token': 'access-1',
      'refresh_token': 'refresh-1',
      'token_type': 'bearer',
      'expires_in': 900,
    });
