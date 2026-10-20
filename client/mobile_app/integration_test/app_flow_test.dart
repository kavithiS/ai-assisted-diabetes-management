// Drives the real app against the real gateway (run the gateway and C1 first):
//   flutter test integration_test -d <emulator id>
// Creates one synthetic test account and removes it at the end, even if a step fails.
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/auth/data/account_api.dart';
import 'package:mobile_app/features/auth/data/auth_http_client.dart';
import 'package:mobile_app/features/auth/data/auth_tokens.dart';
import 'package:mobile_app/features/auth/data/secure_token_store.dart';
import 'package:mobile_app/features/onboarding/data/health_profile.dart';
import 'package:mobile_app/main.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  final email = 'it-${DateTime.now().millisecondsSinceEpoch}@example.test';
  const password = 'integration test password';

  Future<void> pumpUntil(WidgetTester tester, Finder finder,
      {Duration timeout = const Duration(seconds: 30)}) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      await tester.pump(const Duration(milliseconds: 200));
      if (finder.evaluate().isNotEmpty) return;
    }
    fail('Timed out waiting for $finder');
  }

  Future<void> openApp(WidgetTester tester,
      {bool startSignedIn = false}) async {
    await tester.pumpWidget(const SizedBox());
    await tester.pumpWidget(DiaCareApp(
      startSignedIn: startSignedIn,
      mealImagePicker: (_) async => Uint8List.fromList(base64Decode(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=')),
    ));
  }

  Future<void> goToWelcome(WidgetTester tester) async {
    await pumpUntil(tester, find.text('Tap anywhere to continue'));
    await tester.tap(find.text('Tap anywhere to continue'));
    await pumpUntil(tester, find.text('Get Started'));
    await tester.pumpAndSettle();
  }

  Future<void> logIn(WidgetTester tester, String pass) async {
    await tester.enterText(find.byType(TextFormField).at(0), email);
    await tester.enterText(find.byType(TextFormField).at(1), pass);
    await tester.tap(find.text('Log In'));
  }

  testWidgets(
      'register, stay signed in, use the app, log out and delete the account',
      (tester) async {
    try {
      // Register: welcome -> register -> questionnaire -> home.
      await openApp(tester);
      await goToWelcome(tester);
      await tester.tap(find.text('Get Started'));
      await pumpUntil(tester, find.text('Create Account'));
      await tester.pumpAndSettle();
      final fields = find.byType(TextFormField);
      await tester.enterText(fields.at(0), 'Integration Test');
      await tester.enterText(fields.at(1), email);
      await tester.enterText(fields.at(2), password);
      await tester.enterText(fields.at(3), password);
      await tester.ensureVisible(find.byType(Checkbox));
      await tester.tap(find.byType(Checkbox));
      await tester.ensureVisible(find.text('Create Account'));
      await tester.tap(find.text('Create Account'));
      await pumpUntil(tester, find.text('Health Profile Setup'));
      await tester.tap(find.text('Red Rice'));
      for (var i = 0; i < 3; i++) {
        await tester.tap(find.text('Continue'));
        await tester.pumpAndSettle();
      }
      await tester.tap(find.text('Complete Setup'));
      await pumpUntil(tester, find.text('Insights'));
      final userId = (await AccountApi().me()).userId;
      expect(
          (await SecureHealthProfileStore().load(userId))
              ?.answer('staple_food'),
          'Red Rice');

      // Home greets the real account and shows no invented health numbers.
      await pumpUntil(tester, find.textContaining('Integration'));
      expect(find.text('No score yet'), findsOneWidget);
      expect(find.text('No readings yet'), findsOneWidget);
      expect(find.textContaining('mg/dL'), findsNothing);

      // The login is in secure storage: a restarted app finds it and opens on home.
      final restarted = AuthSession(store: SecureTokenStore());
      await restarted.restore();
      expect(restarted.isSignedIn, isTrue,
          reason: 'tokens survive an app restart');
      await AuthSession.instance.restore();
      await openApp(tester, startSignedIn: AuthSession.instance.isSignedIn);
      await pumpUntil(tester, find.textContaining('Integration'));
      await tester.tap(find.text('Profile').last);
      await pumpUntil(tester, find.textContaining('Red Rice'));
      await tester.tap(find.text('Home').last);

      // Meal history is reachable from home, empty, and a logged meal appears.
      await tester.tap(find.text('Meal history'));
      await pumpUntil(tester, find.text('No meals logged yet.'));
      await tester.tap(find.text('Add meal'));
      await pumpUntil(tester, find.text('Enter food manually'));
      await tester.enterText(find.byType(TextField).first, 'rice');
      await tester.tap(find.byIcon(Icons.search));
      await pumpUntil(tester, find.byIcon(Icons.add));
      await tester.tap(find.byIcon(Icons.add).first);
      await pumpUntil(tester, find.text('Grams eaten'));
      await tester.tap(find.widgetWithText(FilledButton, 'Add'));
      await pumpUntil(tester, find.text('Save 1 food'));
      await tester.tap(find.text('Save 1 food'));
      await pumpUntil(tester, find.textContaining('1 item'));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Back'));
      await tester.pumpAndSettle();

      // Today's summary opens too.
      await tester.drag(find.byType(ListView).first, const Offset(0, -300));
      await tester.pumpAndSettle();
      await tester.tap(find.text("Today's summary"));
      await pumpUntil(tester, find.text("Today's Intake"));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Back'));
      await tester.pumpAndSettle();

      // Walk every bottom tab on the Android build.
      await tester.tap(find.text('Meals').last);
      await pumpUntil(tester, find.text('Scan Meal'));
      await tester.tap(find.text('Insights').last);
      await pumpUntil(tester, find.text('Your day is taking shape'));
      await tester.tap(find.text('Foot').last);
      await pumpUntil(tester, find.text('Foot Monitoring'));
      await tester.tap(find.text('Home').last);
      await pumpUntil(tester, find.text('Meal history'));

      // Submit a generated image through the native scan screen and live C1 API.
      await tester.tap(find.text('Meals').last);
      await pumpUntil(tester, find.text('Scan Meal'));
      await tester.tap(find.text('Upload Image'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Lunch'));
      await tester.pumpAndSettle();
      await pumpUntil(tester, find.text('Review Photo'));
      await tester.tap(find.text('Review Photo'));
      await pumpUntil(tester, find.text('Analyze Meal'));
      await tester.tap(find.text('Analyze Meal'));
      await pumpUntil(tester, find.text('Analysing Your Meal'));
      await pumpUntil(tester, find.text('Your result is ready'));
      await tester.tap(find.text('Home').last);

      // Log out from the Profile tab: back to the start screen and nothing left on the device.
      await tester.tap(find.text('Profile'));
      await pumpUntil(tester, find.text('Log out'));
      expect(find.text('Integration Test'), findsWidgets);
      await pumpUntil(tester, find.text('Health profile'));
      expect(find.textContaining('Red Rice'), findsOneWidget);
      await tester.tap(find.text('Log out'));
      await pumpUntil(tester, find.text('Tap anywhere to continue'));
      expect(AuthSession.instance.isSignedIn, isFalse);
      expect(
          (await SecureHealthProfileStore().load(userId))
              ?.answer('staple_food'),
          'Red Rice');
      final afterLogout = AuthSession(store: SecureTokenStore());
      await afterLogout.restore();
      expect(afterLogout.isSignedIn, isFalse,
          reason: 'logout clears secure storage');

      // Log in again: wrong password first, then the right one.
      await tester.tap(find.text('Tap anywhere to continue'));
      await pumpUntil(tester, find.text('I already have an account'));
      await tester.tap(find.text('I already have an account'));
      await pumpUntil(tester, find.text('Log In'));
      await tester.pumpAndSettle();
      await logIn(tester, 'not the password');
      await pumpUntil(tester, find.text('INVALID_CREDENTIALS'));
      expect(find.text('Wrong e-mail or password.'), findsOneWidget);
      await tester.enterText(find.byType(TextFormField).at(1), password);
      await tester.tap(find.text('Log In'));
      await pumpUntil(tester, find.text('Insights'));
      expect(AuthSession.instance.isSignedIn, isTrue);

      // The meal saved earlier belongs to the account and is still there.
      await pumpUntil(tester, find.textContaining('Integration'));
      await tester.tap(find.text('Meal history'));
      await pumpUntil(tester, find.textContaining('1 item'));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Back'));
      await tester.pumpAndSettle();

      // Delete the account from the Profile tab: it is gone, so the same login now fails.
      await tester.tap(find.text('Profile'));
      await pumpUntil(tester, find.text('Delete my account'));
      await tester.drag(find.byType(ListView).last, const Offset(0, -250));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Delete my account'));
      await pumpUntil(tester, find.text('Delete your account?'));
      await tester.tap(find.text('Delete account'));
      await pumpUntil(tester, find.text('Tap anywhere to continue'));
      expect(AuthSession.instance.isSignedIn, isFalse);
      expect(await SecureHealthProfileStore().load(userId), isNull);

      await tester.tap(find.text('Tap anywhere to continue'));
      await pumpUntil(tester, find.text('I already have an account'));
      await tester.tap(find.text('I already have an account'));
      await pumpUntil(tester, find.text('Log In'));
      await tester.pumpAndSettle();
      await logIn(tester, password);
      await pumpUntil(tester, find.text('INVALID_CREDENTIALS'));
    } finally {
      // Clean-up if a step failed half way: remove the account (and its meals) through the API.
      if (AuthSession.instance.isSignedIn) {
        final client = AuthHttpClient();
        await client.delete(ApiClient().uri('/api/v1/me'));
        client.close();
        await AuthSession.instance.signOut();
      }
    }
  });
}
