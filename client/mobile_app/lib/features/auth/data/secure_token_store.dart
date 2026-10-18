import 'dart:async';
import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'auth_tokens.dart';

/// Keeps the login tokens in the platform's secure storage (Android Keystore, iOS Keychain,
/// encrypted browser storage on the web) so the patient stays signed in after a restart.
///
/// Storage problems never break the app: if a read fails the user simply logs in again, and if a
/// write fails the session still works until the app is closed.
class SecureTokenStore implements TokenStore {
  SecureTokenStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const String _key = 'diacare_auth_tokens';

  /// A storage call that never answers must not block app start-up or logging out.
  static const Duration _timeout = Duration(seconds: 5);

  final FlutterSecureStorage _storage;

  @override
  Future<AuthTokens?> load() async {
    try {
      final raw = await _storage.read(key: _key).timeout(_timeout);
      if (raw == null) return null;
      return AuthTokens.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      // Unreadable or damaged data: treat as signed out and drop it, without waiting for it.
      unawaited(clear());
      return null;
    }
  }

  @override
  Future<void> save(AuthTokens tokens) async {
    try {
      await _storage
          .write(key: _key, value: jsonEncode(tokens.toJson()))
          .timeout(_timeout);
    } catch (_) {
      // Keep the in-memory session; the user logs in again after a restart.
    }
  }

  @override
  Future<void> clear() async {
    try {
      await _storage.delete(key: _key).timeout(_timeout);
    } catch (_) {
      // Nothing more to do.
    }
  }
}
