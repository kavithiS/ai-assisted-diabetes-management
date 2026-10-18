import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/api_client.dart';
import 'auth_api.dart';
import 'auth_http_client.dart';
import 'auth_tokens.dart';

/// The signed-in patient's own account, from `GET /api/v1/me`.
class UserProfile {
  const UserProfile({
    required this.userId,
    required this.email,
    required this.role,
    this.displayName,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        userId: json['user_id'] as String,
        email: json['email'] as String,
        role: json['role'] as String,
        displayName: json['display_name'] as String?,
      );

  final String userId;
  final String email;
  final String role;
  final String? displayName;

  /// The name shown in greetings: the display name when there is one, otherwise the e-mail.
  String get label {
    final name = displayName?.trim();
    return name == null || name.isEmpty ? email : name;
  }
}

/// Calls the gateway for the signed-in patient: who am I, log out, delete my account.
/// Every call carries the login token and refreshes it when needed ([AuthHttpClient]).
class AccountApi {
  AccountApi({
    ApiClient? apiClient,
    http.Client? httpClient,
    AuthSession? session,
    Duration? requestTimeout,
  })  : _apiClient = apiClient ?? ApiClient(),
        _session = session ?? AuthSession.instance,
        _http = httpClient ?? AuthHttpClient(session: session),
        requestTimeout = requestTimeout ?? _defaultTimeout;

  final ApiClient _apiClient;
  final AuthSession _session;
  final http.Client _http;

  static const Duration _defaultTimeout = Duration(seconds: 15);
  final Duration requestTimeout;

  Future<UserProfile> me() async {
    final response = await _send(() => _http.get(_apiClient.uri('/api/v1/me')));
    if (response.statusCode != 200) throw AuthApiException.fromResponse(response);
    try {
      return UserProfile.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    } catch (_) {
      throw const AuthApiException('BAD_RESPONSE', 'Something went wrong. Please try again.');
    }
  }

  /// Ends this device's session. The patient is signed out on the device even when the
  /// gateway cannot be reached; the refresh token then simply expires on its own.
  Future<void> logout() async {
    final refreshToken = _session.tokens?.refreshToken;
    try {
      if (refreshToken != null) {
        await _send(() => _http.post(
              _apiClient.uri('/api/v1/auth/logout'),
              headers: const {'Content-Type': 'application/json'},
              body: jsonEncode({'refresh_token': refreshToken}),
            ));
      }
    } on AuthApiException {
      // Signed out locally below.
    } finally {
      await _session.signOut();
    }
  }

  /// Deletes the account and every record of it (ADR 0006). The patient is signed out only
  /// when the gateway confirms; on a failure the account is unchanged and the call can be
  /// repeated.
  Future<void> deleteAccount() async {
    final response = await _send(() => _http.delete(_apiClient.uri('/api/v1/me')));
    if (response.statusCode != 204) throw AuthApiException.fromResponse(response);
    await _session.signOut();
  }

  Future<http.Response> _send(Future<http.Response> Function() call) async {
    try {
      return await call().timeout(requestTimeout);
    } on TimeoutException {
      throw const AuthApiException.timeout();
    } on http.ClientException {
      throw const AuthApiException.network();
    }
  }
}
