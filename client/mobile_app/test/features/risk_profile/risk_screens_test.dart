import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
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
import 'package:mobile_app/features/risk_profile/presentation/risk_settings_screen.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_whatif_screen.dart';
import 'package:mobile_app/features/risk_profile/presentation/risk_xai_screen.dart';
import 'package:mobile_app/features/risk_profile/presentation/widgets/c3_widgets.dart';
import 'package:mobile_app/features/risk_profile/risk_profile_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes.dart';

Widget app(Widget child) => MaterialApp(theme: c3Theme(), home: child);

/// Every piece of text currently on screen, joined.
String allText(WidgetTester tester) => tester
    .widgetList<Text>(find.byType(Text))
    .map((t) => t.data ?? t.textSpan?.toPlainText() ?? '')
    .join('\n');

String allSemantics(WidgetTester tester) {
  final labels = <String>[];
  void visit(SemanticsNode node) {
    final data = node.getSemanticsData();
    labels.addAll([data.label, data.value, data.hint, data.tooltip]);
    node.visitChildren((child) {
      visit(child);
      return true;
    });
  }

  visit(tester.getSemantics(find.byType(Scaffold).first));
  return labels.join('\n');
}

/// A tall test screen so every part of a page is built (lists build lazily).
void tallScreen(WidgetTester tester) {
  tester.view.physicalSize = const Size(900, 5000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

/// The example answers are not on home: a long-press on the connection chip opens
/// Settings, where they are kept for presenting and testing.
Future<void> openExamples(WidgetTester tester) async {
  await tester.longPress(find.text('Connected'));
  await tester.pumpAndSettle();
  expect(find.byType(RiskSettingsScreen), findsOneWidget);
}

Future<RiskController> controllerWith(FakeRiskRepository repository) async {
  SharedPreferences.setMockInitialValues({});
  final controller = RiskController(repositoryBuilder: (_) => repository);
  await controller.init();
  return controller;
}

void main() {
  testWidgets('result: animated score ring, early estimate, band and referral', (tester) async {
    tallScreen(tester);
    await tester.pumpWidget(app(RiskResultView(assessment: RiskAssessment.fromJson(okJson()))));
    await tester.pumpAndSettle();

    expect(find.text('Your health score'), findsOneWidget);
    expect(find.text('58'), findsOneWidget); // ring shows the rounded score
    expect(find.text('Early estimate'), findsOneWidget);
    expect(find.text('High estimated risk'), findsOneWidget);
    expect(find.text('Please see your doctor.'), findsOneWidget);
    expect(find.text('Why this score'), findsOneWidget);
    expect(find.text('What you can do (2)'), findsOneWidget);
    expect(find.text('Estimate for self-care support. Not medical advice.'), findsOneWidget);
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
      expect(text.toLowerCase(), isNot(contains('diagnosis')));
    }
  });

  testWidgets('no diagnosis wording on the patient result', (tester) async {
    await tester.pumpWidget(app(RiskResultView(assessment: RiskAssessment.fromJson(okJson()))));
    final patientText = '${allText(tester)}\n${allSemantics(tester)}'.toLowerCase();
    expect(patientText, isNot(contains('diagnosis')));
    expect(find.text('High estimated risk'), findsOneWidget);
  });

  testWidgets('patient screens and semantics contain no removed terms', (tester) async {
    tallScreen(tester);
    final semantics = tester.ensureSemantics();
    final assessment = RiskAssessment.fromJson(okJson());
    final controller = await controllerWith(FakeRiskRepository([okJson()]));
    final forbidden = RegExp(
      r'\b(?:AI|artificial intelligence|machine learning|model|algorithm|SHAP|LIME|prototype|research(?:er)?|demo|debug|probability|agreement|warm up|provisional|pending clinician review)\b',
      caseSensitive: false,
    );
    final screens = <Widget>[
      Scaffold(body: RiskProfileScreen(controller: controller)),
      RiskQuestionnaireScreen(controller: controller),
      RiskAnalysisScreen(controller: controller, profile: lowerRiskPreset.profile),
      RiskResultView(assessment: assessment),
      RiskXaiScreen(assessment: assessment),
      RiskRecommendationsScreen(assessment: assessment),
      RiskWhatIfScreen(
        controller: controller,
        profile: higherRiskPreset.profile,
        base: assessment,
      ),
      RiskHistoryScreen(controller: controller),
      RiskSettingsScreen(controller: controller),
    ];
    for (final screen in screens) {
      // A fresh app per screen: otherwise a route pushed by one screen (the analysis
      // screen opens the result) hides every later screen and they are never checked.
      await tester.pumpWidget(KeyedSubtree(key: UniqueKey(), child: app(screen)));
      // The analysis screen replaces itself with the result once the answer arrives:
      // check its first frame. Every other screen is checked once it has settled.
      final transient = screen is RiskAnalysisScreen;
      if (transient) {
        await tester.pump();
      } else {
        await tester.pumpAndSettle();
      }
      expect(find.byWidget(screen), findsOneWidget,
          reason: '${screen.runtimeType} must be the screen being checked');
      final visible = '${allText(tester)}\n${allSemantics(tester)}';
      expect(visible, isNot(matches(forbidden)), reason: screen.runtimeType.toString());
      if (transient) await tester.pumpAndSettle();
    }
    semantics.dispose();
    controller.dispose();
  });

  testWidgets('long-pressing the result title opens Details without raw probability',
      (tester) async {
    final assessment = RiskAssessment.fromJson(okJson(debug: debugJson));
    await tester.pumpWidget(app(RiskResultView(assessment: assessment)));

    await tester.longPress(find.text('Your estimate'));
    await tester.pumpAndSettle();

    expect(find.text('Details'), findsOneWidget);
    expect(allText(tester), isNot(contains('0.5657')));
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
    expect(find.textContaining(RegExp(r'^Estimated risk: (Low|Moderate|High)')), findsNothing);
    expect(find.text('Your health score'), findsNothing);
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

    expect(find.text('MAY RAISE YOUR ESTIMATE'), findsOneWidget);
    expect(find.text('MAY LOWER YOUR ESTIMATE'), findsOneWidget);
    expect(find.text('blood glucose'), findsOneWidget); // raising bar
    expect(find.text('body mass index (BMI)'), findsOneWidget); // protective bar
    expect(find.text('Why this score'), findsWidgets);
  });

  testWidgets('recommendations: top priority with current and target', (tester) async {
    tallScreen(tester);
    await tester.pumpWidget(
      app(RiskRecommendationsScreen(assessment: RiskAssessment.fromJson(okJson()))),
    );

    expect(find.text('Try this first'), findsOneWidget);
    expect(find.text('Increase physical activity'), findsOneWidget);
    expect(find.text('Low activity'), findsOneWidget);
    expect(find.text('150 min of moderate activity per week (WHO guideline)'), findsOneWidget);
    expect(find.text('Review your cholesterol with your doctor'), findsOneWidget);
    expect(find.textContaining('pending clinician review'), findsNothing);
    expect(find.textContaining('never ask'), findsNothing);
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

    expect(find.text('Could not connect. Check the address and try again.'), findsOneWidget);
    expect(find.textContaining('Start the service'), findsOneWidget);
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
    expect(find.text('Start with a quick health check.'), findsOneWidget);
    // App users see no example answers and no settings link on home.
    for (final preset in riskPresets) {
      expect(find.text(preset.label), findsNothing);
    }
    expect(find.text('Example answers'), findsNothing);
    expect(find.text('Open connection settings'), findsNothing);

    await openExamples(tester);
    for (final preset in riskPresets) {
      expect(find.text(preset.label), findsOneWidget);
    }
    await tester.tap(find.text(higherRiskPreset.label));
    await tester.pumpAndSettle();
    expect(find.text('High estimated risk'), findsOneWidget);
    expect(repository.sent.single.toJson(), higherRiskPreset.profile.toJson());

    await tester.pageBack(); // result -> Settings
    await tester.pumpAndSettle();
    await tester.pageBack(); // Settings -> home
    await tester.pumpAndSettle();

    expect(find.text('58'), findsOneWidget);
    expect(find.text('/100'), findsOneWidget);
    expect(find.text('YOUR FACTORS'), findsOneWidget);
    expect(find.text('Low activity'), findsOneWidget);
    expect(find.text('Borderline high'), findsOneWidget);
    expect(find.text('Non-smoker'), findsOneWidget);
    expect(find.text('Check again'), findsOneWidget);
  });

  testWidgets('a fast double tap on an example sends and saves the check only once',
      (tester) async {
    tallScreen(tester);
    final repository = FakeRiskRepository([okJson()]);
    final controller = await controllerWith(repository);
    await tester.pumpWidget(app(Scaffold(body: RiskProfileScreen(controller: controller))));
    await tester.pumpAndSettle();
    await openExamples(tester);

    await tester.tap(find.text(higherRiskPreset.label));
    await tester.pump(const Duration(milliseconds: 40));
    await tester.tap(find.text(higherRiskPreset.label), warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(repository.sent, hasLength(1));
    expect(find.byType(RiskResultView), findsOneWidget);
  });

  testWidgets('an out-of-range answer far up the form is shown and explained on Save',
      (tester) async {
    final controller = await controllerWith(FakeRiskRepository([okJson()]));
    await tester.pumpWidget(app(RiskQuestionnaireScreen(controller: controller)));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextFormField, 'Weight (kg)'), '500');
    await tester.scrollUntilVisible(find.text('Save & recalculate'), 400,
        scrollable: find.byType(Scrollable).first);
    await tester.tap(find.text('Save & recalculate'));
    await tester.pumpAndSettle();

    expect(find.text('Please check the answers marked in red.'), findsOneWidget);
    expect(find.text('Enter a value from 20 to 300').hitTestable(), findsOneWidget);
    expect(find.byType(RiskAnalysisScreen), findsNothing);
  });

  testWidgets('home and result rings both follow the risk band colour', (tester) async {
    tallScreen(tester);
    const expected = {
      'Low': C3Colors.success,
      'Moderate': C3Colors.warning,
      'High': C3Colors.danger,
    };
    for (final MapEntry(key: band, value: colour) in expected.entries) {
      final controller = await controllerWith(FakeRiskRepository([okJson(band: band)]));
      await tester.pumpWidget(KeyedSubtree(
        key: UniqueKey(),
        child: app(Scaffold(body: RiskProfileScreen(controller: controller))),
      ));
      await tester.pumpAndSettle();
      await openExamples(tester);
      await tester.tap(find.text(higherRiskPreset.label));
      await tester.pumpAndSettle();
      expect(tester.widget<DhsGauge>(find.byType(DhsGauge)).colour, colour, reason: '$band result');

      await tester.pageBack(); // result -> Settings
      await tester.pumpAndSettle();
      await tester.pageBack(); // Settings -> home
      await tester.pumpAndSettle();
      expect(tester.widget<DhsGauge>(find.byType(DhsGauge)).colour, colour, reason: '$band home');
    }
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
    await tester.tap(find.text('Update estimate'));
    await tester.pumpAndSettle();

    expect(find.text('58 → 70'), findsOneWidget);
    expect(repository.unsaved, 1);
    expect(repository.sent.single.physicalActivity, 'high');
    expect(controller.history.entries, isEmpty);
    expect(find.text('Preview only. This check is not saved.'), findsOneWidget);
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
    expect(find.textContaining('Start the service'), findsOneWidget);

    repository.statusError = null; // the user started the server
    await tester.tap(find.text('Check again'));
    await tester.pumpAndSettle();

    expect(find.text('Connected'), findsOneWidget);
    expect(find.textContaining('Start the service'), findsNothing);
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

    expect(find.text('Saved checks'), findsOneWidget);
    expect(find.text('Estimated risk: High'), findsOneWidget);
    expect(find.text('More answers needed'), findsOneWidget);
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

    expect(find.textContaining('Past checks are offline'), findsOneWidget);
    expect(find.text('Estimated risk: Low'), findsOneWidget);
  });

  testWidgets('a result the server could not save says so, and is still shown', (tester) async {
    tallScreen(tester);
    final assessment = RiskAssessment.fromJson({...okJson(band: 'Low'), 'saved': false});
    await tester.pumpWidget(app(RiskResultView(assessment: assessment)));

    expect(find.text('Low estimated risk'), findsOneWidget);
    expect(find.textContaining('This check wasn’t saved'), findsOneWidget);
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
