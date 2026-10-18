import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/auth/login_screen.dart';
import 'package:mobile_app/features/auth/register_screen.dart';
import 'package:mobile_app/features/onboarding/questionnaire_screen.dart';
import 'package:mobile_app/features/onboarding/welcome_screen.dart';

void main() {
  void useTallView(WidgetTester tester) {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
  }

  testWidgets('"Get Started" opens Register, not the questionnaire', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(const MaterialApp(home: WelcomeScreen()));

    await tester.tap(find.text('Get Started'));
    await tester.pumpAndSettle();

    expect(find.byType(RegisterScreen), findsOneWidget);
    expect(find.byType(QuestionnaireScreen), findsNothing);
  });

  testWidgets('"I already have an account" opens Login', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(const MaterialApp(home: WelcomeScreen()));

    await tester.tap(find.text('I already have an account'));
    await tester.pumpAndSettle();

    expect(find.byType(LoginScreen), findsOneWidget);
  });
}
