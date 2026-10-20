import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/auth/data/auth_api.dart';
import 'package:mobile_app/features/auth/data/auth_tokens.dart';
import 'package:mobile_app/features/auth/login_screen.dart';
import 'package:mobile_app/features/auth/register_screen.dart';
import 'package:mobile_app/features/onboarding/questionnaire_screen.dart';

import 'auth_test_support.dart';

void main() {
  const consent =
      'I agree to the terms and consent to my data being used for this research study';

  void useTallView(WidgetTester tester) {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
  }

  Widget app(FakeGateway gateway, AuthSession session) => MaterialApp(
        home: RegisterScreen(api: gateway.api, session: session),
        routes: {'/home': (_) => const Scaffold(body: Text('HOME PAGE'))},
      );

  /// A gateway that creates the account (201) and then logs in (200).
  FakeGateway openGateway() =>
      FakeGateway((request) => request.url.path.endsWith('/register')
          ? json(201, {'user_id': 'u1'})
          : tokenResponse());

  Future<void> fill(
    WidgetTester tester, {
    String name = 'Nimal Silva',
    String email = 'me@example.test',
    String password = 'a long enough password',
    String confirm = 'a long enough password',
    bool agree = true,
  }) async {
    await tester.enterText(find.byType(TextFormField).at(0), name);
    await tester.enterText(find.byType(TextFormField).at(1), email);
    await tester.enterText(find.byType(TextFormField).at(2), password);
    await tester.enterText(find.byType(TextFormField).at(3), confirm);
    if (agree) await tester.tap(find.byType(Checkbox));
    await tester.tap(find.text('Create Account'));
    await tester.pumpAndSettle();
  }

  testWidgets('shows the exact consent wording and the Create Account button',
      (tester) async {
    useTallView(tester);
    await tester.pumpWidget(app(openGateway(), AuthSession()));

    expect(find.text(consent), findsOneWidget);
    expect(kConsentText, consent);
    expect(find.text('Create Account'), findsOneWidget);
    expect(tester.widget<Checkbox>(find.byType(Checkbox)).value, isFalse);
  });

  testWidgets('without consent nothing is sent', (tester) async {
    useTallView(tester);
    final gateway = openGateway();
    await tester.pumpWidget(app(gateway, AuthSession()));

    await fill(tester, agree: false);

    expect(find.text('Please agree to continue.'), findsOneWidget);
    expect(gateway.requests, isEmpty);
  });

  testWidgets(
      'checks the email, the password length and that the passwords match',
      (tester) async {
    useTallView(tester);
    final gateway = openGateway();
    await tester.pumpWidget(app(gateway, AuthSession()));

    await fill(tester,
        email: 'not-an-email', password: 'short', confirm: 'different');

    expect(find.text('Enter a valid email address.'), findsOneWidget);
    expect(find.text('Use 10 to 128 characters.'), findsOneWidget);
    expect(find.text('Passwords do not match.'), findsOneWidget);
    expect(gateway.requests, isEmpty);
  });

  testWidgets('creates the account, signs in and opens health setup',
      (tester) async {
    useTallView(tester);
    final session = AuthSession();
    final gateway = openGateway();
    await tester.pumpWidget(app(gateway, session));

    await fill(tester);

    expect(gateway.requests.map((r) => r.url.path),
        ['/api/v1/auth/register', '/api/v1/auth/login']);
    expect(gateway.bodyOf(0)['accept'], isTrue);
    expect(gateway.bodyOf(0)['display_name'], 'Nimal Silva');
    expect(gateway.bodyOf(0)['consent_version'], kConsentVersion);
    expect(gateway.bodyOf(1),
        {'email': 'me@example.test', 'password': 'a long enough password'});
    expect(session.tokens!.accessToken, 'access-1');
    expect(find.byType(QuestionnaireScreen), findsOneWidget);
    expect(find.text('Health Profile Setup'), findsOneWidget);
    expect(find.byType(RegisterScreen), findsNothing);
  });

  testWidgets('a closed registration shows the gateway message and code',
      (tester) async {
    useTallView(tester);
    final session = AuthSession();
    final gateway = FakeGateway((_) =>
        errorEnvelope(403, 'REGISTRATION_CLOSED', 'Registration is closed.'));
    await tester.pumpWidget(app(gateway, session));

    await fill(tester);

    expect(find.text('Registration is closed.'), findsOneWidget);
    expect(find.text('REGISTRATION_CLOSED'), findsOneWidget);
    expect(find.byType(RegisterScreen), findsOneWidget);
    expect(session.isSignedIn, isFalse);
    expect(gateway.requests, hasLength(1));
  });

  testWidgets('an e-mail that is already used is reported', (tester) async {
    useTallView(tester);
    final gateway = FakeGateway((_) => errorEnvelope(
        409, 'EMAIL_TAKEN', 'An account with this e-mail already exists.'));
    await tester.pumpWidget(app(gateway, AuthSession()));

    await fill(tester);

    expect(find.text('An account with this e-mail already exists.'),
        findsOneWidget);
    expect(find.text('EMAIL_TAKEN'), findsOneWidget);
  });

  testWidgets(
      'if the account is created but sign-in fails, that error is shown',
      (tester) async {
    useTallView(tester);
    final session = AuthSession();
    final gateway = FakeGateway((request) =>
        request.url.path.endsWith('/register')
            ? json(201, {'user_id': 'u1'})
            : errorEnvelope(429, 'TOO_MANY_ATTEMPTS',
                'Too many failed attempts. Try again later.'));
    await tester.pumpWidget(app(gateway, session));

    await fill(tester);

    expect(find.text('Too many failed attempts. Try again later.'),
        findsOneWidget);
    expect(find.text('Continue to account'), findsOneWidget);
    expect(session.isSignedIn, isFalse);
    expect(find.text('HOME PAGE'), findsNothing);
  });

  testWidgets('retrying sign-in does not create a second account',
      (tester) async {
    useTallView(tester);
    var loginAttempts = 0;
    final gateway = FakeGateway((request) {
      if (request.url.path.endsWith('/register')) {
        return json(201, {'user_id': 'u1'});
      }
      loginAttempts++;
      return loginAttempts == 1
          ? errorEnvelope(503, 'SERVICE_UNAVAILABLE', 'Try again.')
          : tokenResponse();
    });
    await tester.pumpWidget(app(gateway, AuthSession()));

    await fill(tester);
    await tester.tap(find.text('Continue to account'));
    await tester.pumpAndSettle();

    expect(gateway.requests.where((r) => r.url.path.endsWith('/register')),
        hasLength(1));
    expect(find.byType(QuestionnaireScreen), findsOneWidget);
  });

  testWidgets('"Log in" opens the login screen', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(app(openGateway(), AuthSession()));

    await tester.tap(find.text('Log in'));
    await tester.pumpAndSettle();

    expect(find.byType(LoginScreen), findsOneWidget);
  });
}
