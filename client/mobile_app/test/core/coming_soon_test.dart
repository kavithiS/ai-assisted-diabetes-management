import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/dashboard/dashboard_screen.dart';
import 'package:mobile_app/features/foot_monitor/foot_monitor_screen.dart';
import 'package:mobile_app/features/glucose/glucose_screen.dart';
import 'package:mobile_app/features/risk_profile/risk_profile_screen.dart';

void main() {
  void useTallView(WidgetTester tester) {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
  }

  final screens = <String, ({Widget screen, String title, String feature})>{
    'glucose': (
      screen: const GlucoseScreen(),
      title: 'Glucose Forecast',
      feature: 'A 4-hour estimate of your glucose after a meal',
    ),
    'risk profile': (
      screen: const RiskProfileScreen(),
      title: 'Risk Profile',
      feature: 'A Diabetic Health Score that changes as your habits change',
    ),
    'foot monitoring': (
      screen: const FootMonitorScreen(),
      title: 'Foot Monitoring',
      feature: 'Photograph your foot and get an estimated abnormality class',
    ),
    'dashboard': (
      screen: const DashboardScreen(),
      title: 'Health Dashboard',
      feature: 'A real-time health analytics dashboard',
    ),
  };

  for (final entry in screens.entries) {
    testWidgets('${entry.key} shows an intentional coming-soon state', (tester) async {
      useTallView(tester);
      await tester.pumpWidget(MaterialApp(home: entry.value.screen));

      expect(find.text(entry.value.title), findsOneWidget);
      expect(find.text('Coming soon'), findsOneWidget);
      expect(find.text('WHAT IT WILL DO'), findsOneWidget);
      expect(find.text(entry.value.feature), findsOneWidget);
      expect(find.textContaining('estimates and predictions, not diagnoses'),
          findsOneWidget);
      // No placeholder text and no fake numbers.
      expect(find.textContaining('placeholder'), findsNothing);
      expect(find.textContaining('mg/dL'), findsNothing);
    });
  }

  testWidgets('a pushed screen has a back button; a tab does not', (tester) async {
    useTallView(tester);
    await tester.pumpWidget(MaterialApp(
      home: Builder(
        builder: (context) => Scaffold(
          body: Column(children: [
            const Text('ROOT'),
            TextButton(
              onPressed: () => Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => const GlucoseScreen())),
              child: const Text('OPEN'),
            ),
          ]),
        ),
      ),
    ));

    await tester.tap(find.text('OPEN'));
    await tester.pumpAndSettle();
    expect(find.byTooltip('Back'), findsOneWidget);

    await tester.tap(find.byTooltip('Back'));
    await tester.pumpAndSettle();
    expect(find.text('ROOT'), findsOneWidget);

    await tester.pumpWidget(const MaterialApp(home: FootMonitorScreen()));
    expect(find.byTooltip('Back'), findsNothing);
  });
}
