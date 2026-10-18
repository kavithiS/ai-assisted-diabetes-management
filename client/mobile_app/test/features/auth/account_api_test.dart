import 'dart:async';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/auth/data/auth_api.dart';
import 'package:mobile_app/features/auth/data/auth_tokens.dart';
import 'package:mobile_app/features/auth/data/secure_token_store.dart';

import 'auth_test_support.dart';

/// A storage whose calls never complete, like a stuck platform channel.
class _HangingStorage implements FlutterSecureStorage {
  @override
  dynamic noSuchMethod(Invocation invocation) => Completer<String?>().future;
}

void main() {
  group('AccountApi', () {
    test('me reads the signed-in user', () async {
      final session = await signedInSession();
      final gateway = FakeGateway((_) => meResponse(displayName: 'Nimal'));

      final user = await gateway.accountApi(session).me();

      expect(gateway.requests.single.method, 'GET');
      expect(gateway.requests.single.url.path, '/api/v1/me');
      expect(user.email, 'me@example.test');
      expect(user.label, 'Nimal');
    });

    test('the label falls back to the e-mail when there is no display name', () async {
      final session = await signedInSession();
      final gateway = FakeGateway((_) => meResponse());

      expect((await gateway.accountApi(session).me()).label, 'me@example.test');
    });

    test('me reports an expired session with the gateway code', () async {
      final session = await signedInSession();
      final gateway = FakeGateway(
          (_) => errorEnvelope(401, 'UNAUTHORIZED', 'Not signed in.'));

      await expectLater(
        gateway.accountApi(session).me(),
        throwsA(isA<AuthApiException>().having((e) => e.code, 'code', 'UNAUTHORIZED')),
      );
    });

    test('logout sends the refresh token and signs out', () async {
      final session = await signedInSession();
      final gateway = FakeGateway((_) => json(204, {}));

      await gateway.accountApi(session).logout();

      expect(gateway.requests.single.url.path, '/api/v1/auth/logout');
      expect(gateway.bodyOf(0), {'refresh_token': 'refresh-1'});
      expect(session.isSignedIn, isFalse);
    });

    test('logout still signs out on the device when the server is down', () async {
      final session = await signedInSession();
      final gateway = FakeGateway((_) => errorEnvelope(502, 'UPSTREAM_UNAVAILABLE', 'Down.'));

      await gateway.accountApi(session).logout();

      expect(session.isSignedIn, isFalse);
    });

    test('deleting the account signs out only after the gateway confirms', () async {
      final session = await signedInSession();
      final gateway = FakeGateway((_) => json(204, {}));

      await gateway.accountApi(session).deleteAccount();

      expect(gateway.requests.single.method, 'DELETE');
      expect(gateway.requests.single.url.path, '/api/v1/me');
      expect(session.isSignedIn, isFalse);
    });

    test('a failed delete keeps the session so it can be repeated', () async {
      final session = await signedInSession();
      final gateway = FakeGateway((_) => errorEnvelope(
          502, 'UPSTREAM_UNAVAILABLE', 'A service could not delete the data.'));

      await expectLater(
        gateway.accountApi(session).deleteAccount(),
        throwsA(isA<AuthApiException>()
            .having((e) => e.code, 'code', 'UPSTREAM_UNAVAILABLE')),
      );
      expect(session.isSignedIn, isTrue);
    });
  });

  group('SecureTokenStore', () {
    setUp(() => FlutterSecureStorage.setMockInitialValues({}));

    const tokens = AuthTokens(
        accessToken: 'access-9', refreshToken: 'refresh-9', expiresInSeconds: 900);

    test('keeps the tokens between app starts', () async {
      await AuthSession(store: SecureTokenStore()).signIn(tokens);

      final restarted = AuthSession(store: SecureTokenStore());
      await restarted.restore();

      expect(restarted.isSignedIn, isTrue);
      expect(restarted.tokens!.refreshToken, 'refresh-9');
      expect(restarted.needsRefresh, isTrue, reason: 'expiry is unknown after a restart');
    });

    test('signing out removes them', () async {
      final session = AuthSession(store: SecureTokenStore());
      await session.signIn(tokens);
      await session.signOut();

      final restarted = AuthSession(store: SecureTokenStore());
      await restarted.restore();

      expect(restarted.isSignedIn, isFalse);
    });

    testWidgets('storage that never answers cannot block start-up', (tester) async {
      final store = SecureTokenStore(storage: _HangingStorage());

      final loaded = store.load();
      await tester.pump(const Duration(seconds: 6));

      expect(await loaded, isNull);
      // Let the background clean-up give up too, so no timer outlives the test.
      await tester.pump(const Duration(seconds: 6));
    });

    test('damaged stored data means signed out, not a crash', () async {
      FlutterSecureStorage.setMockInitialValues({'diacare_auth_tokens': 'not json'});

      final session = AuthSession(store: SecureTokenStore());
      await session.restore();

      expect(session.isSignedIn, isFalse);
    });
  });
}
