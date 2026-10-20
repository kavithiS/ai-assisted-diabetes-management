import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/auth/data/auth_tokens.dart';
import 'package:mobile_app/features/auth/login_screen.dart';
import 'package:mobile_app/features/auth/register_screen.dart';

import 'auth_test_support.dart';

void main() {
  void useTallView(WidgetTester tester) {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
  }

  Widget app(FakeGateway gateway, AuthSession session) => MaterialApp(
        home: LoginScreen(api: gateway.api, session: session),
        routes: {'/home': (_) => const Scaffold(body: Text('HOME PAGE'))},
      );

  Future<void> logIn(WidgetTester tester) async {
    await tester.enterText(find.byType(TextFormField).at(0), 'me@example.test');
    await tester.enterText(find.byType(TextFormField).at(1), 'secret pass');
    await tester.tap(find.text('Log In'));
    await tester.pumpAndSettle();
  }

  testWidgets('shows the fields and supported actions',
      (tester) async {
    useTallView(tester);
    await tester.pumpWidget(app(FakeGateway((_) => tokenResponse()), AuthSession()));

    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Log In'), findsOneWidget);
    expect(find.text('Forgot password?'), findsNothing);
    expect(find.text('Create account'), findsOneWidget);
  });

  testWidgets('a successful login stores the tokens and opens /home', (tester) async {
    useTallView(tester);
    final session = AuthSession();
    final gateway = FakeGateway((_) => tokenResponse());
    await tester.pumpWidget(app(gateway, session));

    await logIn(tester);

    expect(find.text('HOME PAGE'), findsOneWidget);
    expect(find.byType(LoginScreen), findsNothing);
    expect(session.isSignedIn, isTrue);
    expect(session.tokens!.accessToken, 'access-1');
    expect(session.tokens!.refreshToken, 'refresh-1');
    expect(gateway.bodyOf(0), {'email': 'me@example.test', 'password': 'secret pass'});
  });

  testWidgets('a failed login shows the gateway message and code and stays here',
      (tester) async {
    useTallView(tester);
    final session = AuthSession();
    final gateway = FakeGateway((_) =>
        errorEnvelope(401, 'INVALID_CREDENTIALS', 'Wrong e-mail or password.'));
    await tester.pumpWidget(app(gateway, session));

    await logIn(tester);

    expect(find.text('Wrong e-mail or password.'), findsOneWidget);
    expect(find.text('INVALID_CREDENTIALS'), findsOneWidget);
    expect(find.byType(LoginScreen), findsOneWidget);
    expect(session.isSignedIn, isFalse);
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed, isNotNull);
  });

  testWidgets('empty fields are not sent', (tester) async {
    useTallView(tester);
    final gateway = FakeGateway((_) => tokenResponse());
    await tester.pumpWidget(app(gateway, AuthSession()));

    await tester.tap(find.text('Log In'));
    await tester.pumpAndSettle();

    expect(find.text('Enter your email.'), findsOneWidget);
    expect(find.text('Enter your password.'), findsOneWidget);
    expect(gateway.requests, isEmpty);
  });

  testWidgets('the password can be shown and hidden', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(app(FakeGateway((_) => tokenResponse()), AuthSession()));

    EditableText field() => tester.widget<EditableText>(find.byType(EditableText).at(1));
    expect(field().obscureText, isTrue);

    await tester.tap(find.byTooltip('Show password'));
    await tester.pump();

    expect(field().obscureText, isFalse);
  });

  testWidgets('"Create account" opens the register screen', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(app(FakeGateway((_) => tokenResponse()), AuthSession()));

    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();

    expect(find.byType(RegisterScreen), findsOneWidget);
    expect(find.byType(LoginScreen), findsNothing);
  });
}
