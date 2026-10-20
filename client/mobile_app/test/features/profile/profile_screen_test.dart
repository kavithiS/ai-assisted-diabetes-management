import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/auth/data/account_api.dart';
import 'package:mobile_app/features/profile/profile_screen.dart';

import '../auth/auth_test_support.dart';

void main() {
  void useTallView(WidgetTester tester) {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
  }

  const user = UserProfile(
      userId: 'u1', email: 'me@example.test', role: 'patient');

  var signedOutCalls = 0;
  setUp(() => signedOutCalls = 0);

  Widget app(AccountApi api) => MaterialApp(
        home: ProfileScreen(user: user, api: api, onSignedOut: () => signedOutCalls++),
      );

  testWidgets('shows who is signed in', (tester) async {
    useTallView(tester);
    final gateway = FakeGateway((_) => json(204, {}));
    await tester.pumpWidget(app(gateway.accountApi(await signedInSession())));

    expect(find.text('me@example.test'), findsOneWidget);
    expect(find.text('Log out'), findsOneWidget);
    expect(find.text('Delete my account'), findsOneWidget);
  });

  testWidgets('Log out ends the session and returns to the start screen', (tester) async {
    useTallView(tester);
    final session = await signedInSession();
    final gateway = FakeGateway((_) => json(204, {}));
    await tester.pumpWidget(app(gateway.accountApi(session)));

    await tester.tap(find.text('Log out'));
    await tester.pumpAndSettle();

    expect(signedOutCalls, 1);
    expect(session.isSignedIn, isFalse);
    expect(gateway.requests.single.url.path, '/api/v1/auth/logout');
  });

  testWidgets('deleting asks first, and Cancel changes nothing', (tester) async {
    useTallView(tester);
    final session = await signedInSession();
    final gateway = FakeGateway((_) => json(204, {}));
    await tester.pumpWidget(app(gateway.accountApi(session)));

    await tester.tap(find.text('Delete my account'));
    await tester.pumpAndSettle();
    expect(find.text('Delete your account?'), findsOneWidget);
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();

    expect(gateway.requests, isEmpty);
    expect(session.isSignedIn, isTrue);
    expect(signedOutCalls, 0);
  });

  testWidgets('confirming deletes the account and returns to the start screen',
      (tester) async {
    useTallView(tester);
    final session = await signedInSession();
    final gateway = FakeGateway((_) => json(204, {}));
    await tester.pumpWidget(app(gateway.accountApi(session)));

    await tester.tap(find.text('Delete my account'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delete account'));
    await tester.pumpAndSettle();

    expect(gateway.requests.single.method, 'DELETE');
    expect(signedOutCalls, 1);
    expect(session.isSignedIn, isFalse);
  });

  testWidgets('a failed delete shows the gateway message and keeps the account',
      (tester) async {
    useTallView(tester);
    final session = await signedInSession();
    final gateway = FakeGateway((_) => errorEnvelope(
        502, 'UPSTREAM_UNAVAILABLE', 'A service could not delete the data.'));
    await tester.pumpWidget(app(gateway.accountApi(session)));

    await tester.tap(find.text('Delete my account'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delete account'));
    await tester.pumpAndSettle();

    expect(find.text('A service could not delete the data.'), findsOneWidget);
    expect(find.text('UPSTREAM_UNAVAILABLE'), findsOneWidget);
    expect(session.isSignedIn, isTrue);
    expect(signedOutCalls, 0);
  });
}
