import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:mobile_app/main.dart';

/// End-to-end check on a device or emulator: meal entered once on the forecast
/// tab → real gateway → C2 GRU, then XGBoost on the Dynamic Dietary Risk tab.
/// Requires the backend gateway at AppConfig.apiBaseUrl
/// (http://10.0.2.2:8000 on the emulator).
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  /// Pumps until [done] finds something or an error icon appears.
  Future<void> waitFor(WidgetTester tester, Finder done) async {
    final errorIcon = find.byIcon(Icons.error_outline);
    for (var i = 0; i < 300; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      if (done.evaluate().isNotEmpty || errorIcon.evaluate().isNotEmpty) {
        break;
      }
    }
    expect(errorIcon, findsNothing, reason: 'The request returned an error.');
    expect(done, findsWidgets);
  }

  testWidgets('dietary risk page shows real API results for the shared meal',
      (tester) async {
    await tester.pumpWidget(const DiaCareApp());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Glucose'));
    await tester.pumpAndSettle();

    final fields = find.byType(TextFormField);
    const values = ['110', '600', '70', '25', '20', '8'];
    for (var i = 0; i < values.length; i++) {
      await tester.enterText(fields.at(i), values[i]);
      await tester.pumpAndSettle();
    }

    final forecastButton =
        find.widgetWithText(FilledButton, 'Get 4-hour estimate');
    await tester.ensureVisible(forecastButton);
    await tester.pumpAndSettle();
    await tester.tap(forecastButton);
    await waitFor(tester, find.text('Estimated glucose, next 4 hours'));

    await tester.tap(find.text('Dietary risk'));
    await tester.pumpAndSettle();
    expect(find.byType(TextFormField), findsNothing);

    final assess = find.widgetWithText(FilledButton, 'Assess this meal');
    await tester.ensureVisible(assess);
    await tester.pumpAndSettle();
    await tester.tap(assess);
    await waitFor(tester, find.text('Risk Interpretation'));

    expect(find.text('Predicted peak glucose'), findsOneWidget);
    expect(find.text('DIETARY METRICS'), findsOneWidget);
    expect(find.text('600 kcal'), findsOneWidget);
    expect(find.textContaining('xgb-above180-4h-'), findsOneWidget);
  });
}
