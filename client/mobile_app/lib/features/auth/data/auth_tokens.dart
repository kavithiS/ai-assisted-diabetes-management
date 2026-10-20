import 'secure_token_store.dart';

/// The pair of tokens returned by `POST /api/v1/auth/login`.
class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresInSeconds,
  });

  factory AuthTokens.fromJson(Map<String, dynamic> json) => AuthTokens(
        accessToken: json['access_token'] as String,
        refreshToken: json['refresh_token'] as String,
        expiresInSeconds: json['expires_in'] as int,
      );

  Map<String, dynamic> toJson() => {
        'access_token': accessToken,
        'refresh_token': refreshToken,
        'expires_in': expiresInSeconds,
      };

  final String accessToken;
  final String refreshToken;

  /// Lifetime of the access token, from the moment it was issued.
  final int expiresInSeconds;
}

/// Where tokens are kept: [SecureTokenStore] in the app, [MemoryTokenStore] in tests.
abstract class TokenStore {
  Future<AuthTokens?> load();
  Future<void> save(AuthTokens tokens);
  Future<void> clear();
}

/// Keeps tokens in memory only, so the user signs in again after the app is closed.
/// Used by tests and as the fallback of a fresh [AuthSession].
class MemoryTokenStore implements TokenStore {
  AuthTokens? _tokens;

  @override
  Future<AuthTokens?> load() async => _tokens;

  @override
  Future<void> save(AuthTokens tokens) async => _tokens = tokens;

  @override
  Future<void> clear() async => _tokens = null;
}

/// The signed-in state of the app.
class AuthSession {
  AuthSession({TokenStore? store}) : _store = store ?? MemoryTokenStore();

  /// The session the screens use unless a test passes its own. Its tokens survive a restart.
  static final AuthSession instance = AuthSession(store: SecureTokenStore());

  final TokenStore _store;
  AuthTokens? _tokens;
  DateTime? _expiresAt;
  Future<void>? _refreshing;

  AuthTokens? get tokens => _tokens;
  bool get isSignedIn => _tokens != null;

  /// True when the access token expires within a minute.
  bool get needsRefresh {
    final expiresAt = _expiresAt;
    return expiresAt != null &&
        DateTime.now().isAfter(expiresAt.subtract(const Duration(minutes: 1)));
  }

  /// Loads the stored tokens. The expiry is unknown after a restore, so the first request
  /// refreshes them (and signs the user out if the gateway no longer accepts them).
  Future<void> restore() async {
    _tokens = await _store.load();
    _expiresAt = _tokens == null ? null : DateTime.now();
  }

  Future<void> signIn(AuthTokens tokens) async {
    _tokens = tokens;
    _expiresAt = DateTime.now().add(Duration(seconds: tokens.expiresInSeconds));
    await _store.save(tokens);
  }

  Future<void> signOut() async {
    _tokens = null;
    _expiresAt = null;
    await _store.clear();
  }

  /// Refreshes the tokens when they are about to expire. Only one refresh runs at a time,
  /// because the gateway treats a refresh token used twice as stolen and ends every session.
  /// [refresh] returns the new pair, or `null` when the refresh token was rejected.
  Future<void> ensureFresh(Future<AuthTokens?> Function(String refreshToken) refresh) {
    final tokens = _tokens;
    if (tokens == null || !needsRefresh) return Future.value();
    return _refreshing ??= () async {
      try {
        final fresh = await refresh(tokens.refreshToken);
        if (fresh == null) {
          await signOut();
        } else {
          await signIn(fresh);
        }
      } finally {
        _refreshing = null;
      }
    }();
  }
}
