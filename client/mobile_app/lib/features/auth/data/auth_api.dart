import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/api_client.dart';
import 'auth_tokens.dart';

/// Version label sent with the consent. It must be replaced by the version of the
/// consent text approved by the ethics committee.
const String kConsentVersion = 'v1';

/// Calls the gateway's login endpoints: `POST /api/v1/auth/login` and `/register`.
class AuthApi {
  AuthApi(
      {ApiClient? apiClient, http.Client? httpClient, Duration? requestTimeout})
      : _apiClient = apiClient ?? ApiClient(),
        _http = httpClient ?? http.Client(),
        requestTimeout = requestTimeout ?? _defaultTimeout;

  final ApiClient _apiClient;
  final http.Client _http;

  static const Duration _defaultTimeout = Duration(seconds: 15);
  final Duration requestTimeout;

  Future<AuthTokens> login(
      {required String email, required String password}) async {
    final response = await _post('/api/v1/auth/login', {
      'email': email.trim(),
      'password': password,
    });
    if (response.statusCode != 200) {
      throw AuthApiException.fromResponse(response);
    }
    try {
      return AuthTokens.fromJson(
          jsonDecode(response.body) as Map<String, dynamic>);
    } catch (_) {
      // Malformed JSON or an unexpected shape: never crash the screen.
      throw const AuthApiException('BAD_RESPONSE', _genericMessage);
    }
  }

  /// Creates the account. The gateway answers `201 {"user_id": ...}` and no tokens.
  Future<String> register(
      {required String fullName,
      required String email,
      required String password}) async {
    final response = await _post('/api/v1/auth/register', {
      'display_name': fullName.trim(),
      'email': email.trim(),
      'password': password,
      'consent_version': kConsentVersion,
      'accept': true,
    });
    if (response.statusCode != 201) {
      throw AuthApiException.fromResponse(response);
    }
    try {
      return (jsonDecode(response.body) as Map<String, dynamic>)['user_id']
          as String;
    } catch (_) {
      throw const AuthApiException('BAD_RESPONSE', _genericMessage);
    }
  }

  /// Swaps a refresh token for a new pair. Each refresh token works only once.
  Future<AuthTokens> refresh(String refreshToken) async {
    final response =
        await _post('/api/v1/auth/refresh', {'refresh_token': refreshToken});
    if (response.statusCode != 200) {
      throw AuthApiException.fromResponse(response);
    }
    try {
      return AuthTokens.fromJson(
          jsonDecode(response.body) as Map<String, dynamic>);
    } catch (_) {
      throw const AuthApiException('BAD_RESPONSE', _genericMessage);
    }
  }

  Future<http.Response> _post(String path, Map<String, Object?> body) async {
    try {
      return await _http
          .post(
            _apiClient.uri(path),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(requestTimeout);
    } on TimeoutException {
      throw const AuthApiException.timeout();
    } on http.ClientException {
      throw const AuthApiException.network();
    }
  }
}

const String _genericMessage = 'Something went wrong. Please try again.';

class AuthApiException implements Exception {
  const AuthApiException(this.code, this.message, {this.details = const []});

  const AuthApiException.timeout()
      : this(
          'TIMEOUT',
          'The server is taking too long. Make sure the server is running and try again.',
        );

  const AuthApiException.network()
      : this(
          'NETWORK',
          'Cannot reach the server. Make sure the server is running on your PC and try again.',
        );

  /// Reads the shared error envelope:
  /// `{"error": {"code", "message", "details": [{"field", "issue"}]}, "request_id"}`.
  factory AuthApiException.fromResponse(http.Response response) {
    var code = 'HTTP_${response.statusCode}';
    var message = _genericMessage;
    final details = <String>[];
    try {
      final body = jsonDecode(response.body);
      final error = body is Map ? body['error'] : null;
      if (error is Map) {
        if (error['code'] is String) code = error['code'] as String;
        if (error['message'] is String) message = error['message'] as String;
        final raw = error['details'];
        if (raw is List) {
          for (final item in raw) {
            if (item is Map && item['issue'] is String) {
              details.add(item['issue'] as String);
            }
          }
        }
      }
    } on FormatException {
      // Not JSON (e.g. a proxy error page): keep the HTTP status code.
    }
    return AuthApiException(code, message, details: details);
  }

  /// Machine-readable code from the gateway, e.g. `INVALID_CREDENTIALS`.
  final String code;

  /// The gateway's own message, safe to show to the patient.
  final String message;

  /// Field-level problems from a validation error (`issue` of each detail).
  final List<String> details;

  @override
  String toString() => 'AuthApiException($code): $message';
}
