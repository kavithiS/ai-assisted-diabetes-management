import 'dart:async';

import 'package:http/http.dart' as http;

import 'auth_api.dart';
import 'auth_tokens.dart';

/// HTTP client for gateway calls that need the signed-in patient.
///
/// It adds `Authorization: Bearer <access token>` and refreshes the tokens shortly before
/// they expire. A refresh token the gateway rejects signs the user out, so later calls
/// get the gateway's `401 UNAUTHORIZED`.
class AuthHttpClient extends http.BaseClient {
  AuthHttpClient({AuthSession? session, AuthApi? authApi, http.Client? inner})
      : _session = session ?? AuthSession.instance,
        _inner = inner ?? http.Client(),
        _authApi = authApi;

  final AuthSession _session;
  final http.Client _inner;
  final AuthApi? _authApi;

  late final AuthApi _api = _authApi ?? AuthApi(httpClient: _inner);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    await _session.ensureFresh(_refresh);
    final tokens = _session.tokens;
    if (tokens != null) {
      request.headers['Authorization'] = 'Bearer ${tokens.accessToken}';
    }
    return _inner.send(request);
  }

  Future<AuthTokens?> _refresh(String refreshToken) async {
    try {
      return await _api.refresh(refreshToken);
    } on AuthApiException catch (e) {
      if (e.code == 'UNAUTHORIZED') return null;
      // Keep the tokens and surface it like any other network failure of the request.
      if (e.code == 'TIMEOUT') throw TimeoutException(e.message);
      throw http.ClientException(e.message);
    }
  }

  @override
  void close() => _inner.close();
}
