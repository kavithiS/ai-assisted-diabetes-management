import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/risk_profile/c3_theme.dart';
import 'package:mobile_app/features/risk_profile/data/risk_api.dart';
import 'package:mobile_app/features/risk_profile/data/settings_store.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_assessment.dart';
import 'package:mobile_app/features/risk_profile/domain/risk_presets.dart';
import 'package:mobile_app/features/risk_profile/domain/server_history.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_analysis_screen.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_controller.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_history_screen.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_questionnaire_screen.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_recommendations_screen.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_result_screen.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_whatif_screen.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_xai_screen.dart';
import 'package:mobile_app/features/risk_profile/risk_profile_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes.dart';

Widget app(Widget child) => MaterialApp(theme: c3Theme(), home: child);

/// Every piece of text currently on screen, joined.
String allText(WidgetTester tester) => tester
    .widgetList<Text>(find.byType(Text))
    .map((t) => t.data ?? t.textSpan?.toPlainText() ?? '')
    .join('\n');

/// A tall test screen so every part of a page is built (lists build lazily).
void tallScreen(WidgetTester tester) {
  tester.view.physicalSize = const Size(900, 5000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

Future<RiskController> controllerWith(FakeRiskRepository repository) async {
  SharedPreferences.setMockInitialValues({});
  final controller = RiskController(repositoryBuilder: (_) => repository);
  await controller.init();
  return controller;
}

void main() {
  testWidgets('result: DHS ring, provisional tag, band, referral and disclaimer', (tester) async {
    tallScreen(tester);
    await tester.pumpWidget(app(RiskResultView(assessment: RiskAssessment.fromJson(okJson()))));

    expect(find.text('Diabetic Health Score'), findsOneWidget);
    expect(find.text('58'), findsOneWidget); // ring shows the rounded score
    expect(find.textContaining('Provisional score'), findsOneWidget);
    expect(find.text('High estimated risk'), findsOneWidget);
    expect(find.text('Please arrange a blood test and a check-up.'), findsOneWidget);
    expect(find.text('Understand my risk'), findsOneWidget);
    expect(find.text('View recommendations (2)'), findsOneWidget);
    expect(find.textContaining('not a diagnosis'), findsWidgets);
  });

  testWidgets('no probability on any patient screen, even when the server sent it', (tester) async {
    tallScreen(tester);
    final assessment = RiskAssessment.fromJson(okJson(debug: debugJson));
    expect(assessment.researcherInfo?.riskProbability, 0.5657);

    for (final screen in <Widget>[
      RiskResultView(assessment: assessment),
      RiskXaiScreen(assessment: assessment),
      RiskRecommendationsScreen(assessment: assessment),
    ]) {
      await tester.pumpWidget(app(screen));
      final text = allText(tester);
      expect(text, isNot(contains('0.5657')));
      expect(text, isNot(contains('56.6')));
      expect(text, isNot(contains('%')));
      expect(text.toLowerCase(), isNot(contains('probability')));
    }
  });

  testWidgets('long-pressing the result title opens the researcher view', (tester) async {
    final assessment = RiskAssessment.fromJson(okJson(debug: debugJson));
    await tester.pumpWidget(app(RiskResultView(assessment: assessment)));

    await tester.longPress(find.text('Your estimated risk'));
    await tester.pumpAndSettle();

    expect(find.text('Researcher view (not for patients)'), findsOneWidget);
    expect(find.text('Calibrated probability: 0.5657'), findsOneWidget);
  });

  testWidgets('insufficient_data: no band, no score, the missing answers are listed',
      (tester) async {
    final assessment = RiskAssessment.fromJson({
      'status': 'insufficient_data',
      'disclaimer': 'This is not a diagnosis.',
      'missing_critical_fields': ['bmi'],
    });
    await tester.pumpWidget(app(RiskResultView(assessment: assessment)));

    expect(find.text('We need a few more answers'), findsOneWidget);
    expect(find.text('height and weight (BMI)'), findsOneWidget);
    expect(find.textContaining(RegExp(r'^(Low|Moderate|High) estimated risk')), findsNothing);
    expect(find.text('Diabetic Health Score'), findsNothing);
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
  });

  testWidgets('explanation: raising and protective factors, AI card, LIME check', (tester) async {
    tallScreen(tester);
    await tester.pumpWidget(app(RiskXaiScreen(assessment: RiskAssessment.fromJson(okJson()))));

    expect(find.text('FACTORS INCREASING RISK'), findsOneWidget);
    expect(find.text('FACTORS REDUCING RISK (PROTECTIVE)'), findsOneWidget);
    expect(find.text('blood glucose'), findsOneWidget); // raising bar
    expect(find.text('body mass index (BMI)'), findsOneWidget); // protective bar
    expect(find.text('AI Explanation'), findsWidgets);
    expect(find.text('The two methods agree on 4 of their top 5 factors.'), findsOneWidget);
  });

  testWidgets('recommendations: top priority with current and target, all provisional',
      (tester) async {
    tallScreen(tester);
    await tester.pumpWidget(
      app(RiskRecommendationsScreen(assessment: RiskAssessment.fromJson(okJson()))),
    );

    expect(find.text('Top priority'), findsOneWidget);
    expect(find.text('Increase physical activity'), findsOneWidget);
    expect(find.text('Low activity'), findsOneWidget);
    expect(find.text('150 min of moderate activity per week (WHO guideline)'), findsOneWidget);
    expect(find.text('Review your cholesterol with your doctor'), findsOneWidget);
    expect(find.textContaining('pending clinician review'), findsWidgets);
    expect(find.textContaining('never ask'), findsOneWidget);
  });

  testWidgets('analysis: a network error shows Retry and the hint; Retry opens the result',
      (tester) async {
    final repository = FakeRiskRepository([
      const RiskApiException(RiskApiErrorKind.network, 'Cannot reach the gateway.'),
      okJson(band: 'Low', dhs: 91),
    ]);
    final controller = await controllerWith(repository);
    await tester.pumpWidget(
      app(RiskAnalysisScreen(controller: controller, profile: lowerRiskPreset.profile)),
    );
    await tester.pumpAndSettle();

    expect(find.text('Cannot reach the gateway.'), findsOneWidget);
    expect(find.textContaining('demo.ps1'), findsOneWidget);
    expect(find.textContaining('DEMO DATA'), findsNothing); // no silent mock fallback

    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();

    expect(find.text('Low estimated risk'), findsOneWidget);
    expect(find.text('91'), findsOneWidget);
  });

  testWidgets('health info form rejects an out-of-range age before sending', (tester) async {
    tallScreen(tester);
    final repository = FakeRiskRepository([okJson()]);
    final controller = await controllerWith(repository);
    await tester.pumpWidget(app(RiskQuestionnaireScreen(controller: controller)));

    await tester.enterText(find.byType(TextFormField).first, '150');
    await tester.tap(find.text('Save & recalculate'));
    await tester.pumpAndSettle();

    expect(find.text('Enter a value from 18 to 100'), findsOneWidget);
    expect(repository.sent, isEmpty);
  });

  testWidgets('health info form sends the lifestyle answers with the clinical ones',
      (tester) async {
    tallScreen(tester);
    final repository = FakeRiskRepository([okJson()]);
    final controller = await controllerWith(repository);
    await tester.pumpWidget(app(RiskQuestionnaireScreen(controller: controller)));

    final fields = find.byType(TextFormField);
    await tester.enterText(fields.at(0), '50'); // age
    await tester.enterText(fields.at(1), '170'); // height
    await tester.enterText(fields.at(2), '70'); // weight
    await tester.enterText(fields.at(3), '120'); // systolic
    await tester.enterText(fields.at(4), '80'); // diastolic
    await tester.tap(find.text('Low'));
    await tester.tap(find.text('Borderline high'));
    await tester.tap(find.text('Save & recalculate'));
    await tester.pumpAndSettle();

    final sent = repository.sent.single.toJson();
    expect(sent['schema_version'], '0.2');
    expect(sent['bmi'], 24.2);
    expect(sent['physical_activity'], 'low');
    expect(sent['cholesterol_level'], 'borderline_high');
    expect(sent.containsKey('smoker'), isFalse); // not answered, not guessed
    expect(find.text('High estimated risk'), findsOneWidget);
  });

  testWidgets('home: after a preset, the DHS card and the risk factors appear', (tester) async {
    tallScreen(tester);
    final repository = FakeRiskRepository([okJson()]);
    final controller = await controllerWith(repository);
    await tester.pumpWidget(app(Scaffold(body: RiskProfileScreen(controller: controller))));
    await tester.pumpAndSettle();

    expect(find.text('Connected'), findsOneWidget);
    expect(find.textContaining('No score yet'), findsOneWidget);
    for (final preset in riskPresets) {
      expect(find.text(preset.label), findsOneWidget);
    }

    await tester.tap(find.text(higherRiskPreset.label));
    await tester.pumpAndSettle();
    expect(find.text('High estimated risk'), findsOneWidget);
    expect(repository.sent.single.toJson(), higherRiskPreset.profile.toJson());

    await tester.pageBack();
    await tester.pumpAndSettle();

    expect(find.text('58 /100', findRichText: true), findsOneWidget);
    expect(find.text('RISK FACTORS'), findsOneWidget);
    expect(find.text('Low activity'), findsOneWidget);
    expect(find.text('Borderline high'), findsOneWidget);
    expect(find.text('Non-smoker'), findsOneWidget);
    expect(find.text('Recalculate score'), findsOneWidget);
  });

  testWidgets('what-if: a new estimate from the server, not saved', (tester) async {
    tallScreen(tester);
    final repository = FakeRiskRepository([okJson(dhs: 70.4)]);
    final controller = await controllerWith(repository);
    await tester.pumpWidget(
      app(
        RiskWhatIfScreen(
          controller: controller,
          profile: higherRiskPreset.profile,
          base: RiskAssessment.fromJson(okJson()),
        ),
      ),
    );

    await tester.tap(find.text('High').first);
    await tester.tap(find.text('Estimate'));
    await tester.pumpAndSettle();

    expect(find.text('58 → 70'), findsOneWidget);
    expect(repository.unsaved, 1);
    expect(repository.sent.single.physicalActivity, 'high');
    expect(controller.history.entries, isEmpty);
    expect(find.textContaining('not a guaranteed medical outcome'), findsOneWidget);
  });

  testWidgets('unreachable gateway: home tells how to start the server, Check again retries',
      (tester) async {
    tallScreen(tester);
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

  testWidgets('history shows the results saved on the server', (tester) async {
    final repository = FakeRiskRepository(
      [okJson()],
      serverHistory: [
        ServerHistoryItem(
          id: 'a',
          assessedAt: DateTime(2026, 10, 19, 10, 5),
          status: 'ok',
          schemaVersion: '0.2',
          band: RiskBand.high,
          modelVersion: '2026-10-10',
        ),
        ServerHistoryItem(
          id: 'b',
          assessedAt: DateTime(2026, 10, 19, 10, 1),
          status: 'insufficient_data',
          schemaVersion: '0.2',
        ),
      ],
    );
    final controller = await controllerWith(repository);
    await tester.pumpWidget(app(RiskHistoryScreen(controller: controller)));
    await tester.pumpAndSettle();

    expect(find.text('Saved results on the server (newest first)'), findsOneWidget);
    expect(find.text('Estimated risk band: High'), findsOneWidget);
    expect(find.text('More answers were needed (no band)'), findsOneWidget);
    expect(find.textContaining('2026-10-19 10:05'), findsOneWidget);
  });

  testWidgets('history falls back to this session, and says so, when the database is down',
      (tester) async {
    final repository = FakeRiskRepository(
      [okJson(band: 'Low')],
      historyError:
          const RiskApiException(RiskApiErrorKind.notReady, 'C3 database is unreachable.'),
    );
    final controller = await controllerWith(repository);
    await controller.assess(lowerRiskPreset.profile);
    await tester.pumpWidget(app(RiskHistoryScreen(controller: controller)));
    await tester.pumpAndSettle();

    expect(find.textContaining('Saved results are not available right now'), findsOneWidget);
    expect(find.text('Estimated risk band: Low'), findsOneWidget);
  });

  testWidgets('a result the server could not save says so, and is still shown', (tester) async {
    tallScreen(tester);
    final assessment = RiskAssessment.fromJson({...okJson(band: 'Low'), 'saved': false});
    await tester.pumpWidget(app(RiskResultView(assessment: assessment)));

    expect(find.text('Low estimated risk'), findsOneWidget);
    expect(find.textContaining('This result was not saved'), findsOneWidget);
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
