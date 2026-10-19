import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/risk_profile/data/risk_api.dart';
import 'package:mobile_app/features/risk_profile/data/settings_store.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_assessment.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_presets.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_controller.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_questionnaire_screen.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_result_screen.dart';
import 'package:mobile_app/features/risk_profile/risk_profile_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes.dart';

Widget app(Widget child) => MaterialApp(home: child);

/// Every piece of text currently on screen, joined.
String allText(WidgetTester tester) => tester
    .widgetList<Text>(find.byType(Text))
    .map((t) => t.data ?? t.textSpan?.toPlainText() ?? '')
    .join('\n');

Future<RiskController> controllerWith(FakeRiskRepository repository) async {
  SharedPreferences.setMockInitialValues({});
  final controller = RiskController(repositoryBuilder: (_) => repository);
  await controller.init();
  return controller;
}

void main() {
  testWidgets('ok: band, referral, factors, agreement and disclaimer are shown', (tester) async {
    await tester.pumpWidget(app(RiskResultView(assessment: RiskAssessment.fromJson(okJson()))));

    expect(find.text('Estimated risk band: High'), findsOneWidget);
    expect(find.text('Please arrange a blood test and a check-up.'), findsOneWidget);
    expect(find.text('Factors you can work on'), findsOneWidget);
    expect(find.text('Background and medical history'), findsOneWidget);
    expect(find.text('blood glucose: raised the estimate'), findsWidgets);
    // The list builds lazily: scroll to the lower parts before checking them.
    for (final text in [
      'The two methods agree on 4 of their top 5 factors.',
      'LIME fit (R²): 0.69',
    ]) {
      await tester.scrollUntilVisible(find.text(text), 200);
      expect(find.text(text), findsOneWidget);
    }
    await tester.scrollUntilVisible(find.textContaining('resting pulse'), 200); // imputed
    await tester.scrollUntilVisible(find.textContaining('not a diagnosis'), 200);
    expect(find.textContaining('not a diagnosis'), findsOneWidget);
  });

  testWidgets('patient screen never shows the probability, even when the server sent it',
      (tester) async {
    final assessment = RiskAssessment.fromJson(okJson(debug: debugJson));
    expect(assessment.researcherInfo?.riskProbability, 0.5657);

    // A tall screen, so every part of the result is built and checked.
    tester.view.physicalSize = const Size(800, 4000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(app(RiskResultView(assessment: assessment)));
    final text = allText(tester);
    expect(text, contains('not a diagnosis')); // proves the whole page was rendered

    expect(text, isNot(contains('0.5657')));
    expect(text, isNot(contains('56.6')));
    expect(text, isNot(contains('%')));
    expect(text.toLowerCase(), isNot(contains('probability')));
  });

  testWidgets('long-pressing the title opens the researcher view', (tester) async {
    final assessment = RiskAssessment.fromJson(okJson(debug: debugJson));
    await tester.pumpWidget(app(RiskResultView(assessment: assessment)));

    await tester.longPress(find.text('Your estimated risk'));
    await tester.pumpAndSettle();

    expect(find.text('Researcher view (not for patients)'), findsOneWidget);
    expect(find.text('Calibrated probability: 0.5657'), findsOneWidget);
  });

  testWidgets('insufficient_data: no band, the missing answers are listed', (tester) async {
    final assessment = RiskAssessment.fromJson({
      'status': 'insufficient_data',
      'disclaimer': 'This is not a diagnosis.',
      'missing_critical_fields': ['bmi'],
    });
    await tester.pumpWidget(app(RiskResultView(assessment: assessment)));

    expect(find.text('We need a few more answers'), findsOneWidget);
    expect(find.text('height and weight (BMI)'), findsOneWidget);
    expect(find.textContaining('Estimated risk band'), findsNothing);
  });

  testWidgets('invalid_input: no band, the problems are listed', (tester) async {
    final assessment = RiskAssessment.fromJson({
      'status': 'invalid_input',
      'disclaimer': 'This is not a diagnosis.',
      'problems': ['bmi=500.0 is outside 12-70'],
    });
    await tester.pumpWidget(app(RiskResultView(assessment: assessment)));

    expect(find.text('Some answers look out of range'), findsOneWidget);
    expect(find.text('bmi=500.0 is outside 12-70'), findsOneWidget);
    expect(find.textContaining('Estimated risk band'), findsNothing);
  });

  testWidgets('a network error shows Retry, and Retry gets the result', (tester) async {
    final repository = FakeRiskRepository([
      const RiskApiException(RiskApiErrorKind.network, 'Cannot reach the gateway.'),
      okJson(band: 'Low'),
    ]);
    final controller = await controllerWith(repository);
    await tester.pumpWidget(
      app(RiskResultScreen(controller: controller, profile: lowerRiskPreset.profile)),
    );
    await tester.pumpAndSettle();

    expect(find.text('Cannot reach the gateway.'), findsOneWidget);
    expect(find.textContaining('DEMO DATA'), findsNothing); // no silent mock fallback

    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();

    expect(find.text('Estimated risk band: Low'), findsOneWidget);
    expect(controller.history.entries, hasLength(1));
  });

  testWidgets('questionnaire rejects an out-of-range age before sending', (tester) async {
    final repository = FakeRiskRepository([okJson()]);
    final controller = await controllerWith(repository);
    await tester.pumpWidget(app(RiskQuestionnaireScreen(controller: controller)));

    await tester.enterText(find.byType(TextFormField).first, '150');
    await tester.tap(find.text('Next').hitTestable().first);
    await tester.pump();

    expect(find.text('Enter a value from 18 to 100'), findsOneWidget);
    expect(repository.sent, isEmpty);
  });

  testWidgets('home shows the connection, the three presets and runs one', (tester) async {
    final repository = FakeRiskRepository([okJson()]);
    final controller = await controllerWith(repository);
    await tester.pumpWidget(app(Scaffold(body: RiskProfileScreen(controller: controller))));
    await tester.pumpAndSettle();

    expect(find.text('Connected'), findsOneWidget);
    for (final preset in riskPresets) {
      expect(find.text(preset.label), findsOneWidget);
    }

    await tester.tap(find.text(higherRiskPreset.label));
    await tester.pumpAndSettle();

    expect(find.text('Estimated risk band: High'), findsOneWidget);
    expect(repository.sent.single.toJson(), higherRiskPreset.profile.toJson());
  });

  testWidgets('unreachable gateway: home tells how to start the server, Check again retries',
      (tester) async {
    final repository = FakeRiskRepository(
      [okJson()],
      statusError: const RiskApiException(RiskApiErrorKind.network, 'Cannot reach the gateway.'),
    );
    final controller = await controllerWith(repository);
    await tester.pumpWidget(app(Scaffold(body: RiskProfileScreen(controller: controller))));
    await tester.pumpAndSettle();

    expect(find.text('Not connected'), findsOneWidget);
    expect(find.textContaining('demo.ps1'), findsOneWidget);

    repository.statusError = null; // the user started the server
    await tester.tap(find.text('Check again'));
    await tester.pumpAndSettle();

    expect(find.text('Connected'), findsOneWidget);
    expect(find.textContaining('demo.ps1'), findsNothing);
  });

  testWidgets('network error on a result also shows the start-the-server hint', (tester) async {
    final repository = FakeRiskRepository([
      const RiskApiException(RiskApiErrorKind.network, 'Cannot reach the gateway.'),
    ]);
    final controller = await controllerWith(repository);
    await tester.pumpWidget(
      app(RiskResultScreen(controller: controller, profile: lowerRiskPreset.profile)),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('demo.ps1'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });

  test('device ID is made once, kept, and identifies nobody', () async {
    SharedPreferences.setMockInitialValues({});
    final store = SettingsStore();
    final first = await store.load();
    final second = await store.load();

    expect(first.deviceId, second.deviceId);
    expect(first.deviceId, matches(RegExp(r'^[0-9a-f]{32}$')));
  });

  test('gateway URL must be a full http(s) address', () {
    expect(isValidGatewayUrl('http://localhost:8000'), isTrue);
    expect(isValidGatewayUrl('http://10.0.2.2:8000'), isTrue);
    expect(isValidGatewayUrl('localhost:8000'), isFalse);
    expect(isValidGatewayUrl(''), isFalse);
  });
}
