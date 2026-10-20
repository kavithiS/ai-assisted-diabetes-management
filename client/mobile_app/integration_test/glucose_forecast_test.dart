import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:mobile_app/main.dart';

/// End-to-end check on a device or emulator: form → real gateway → C2 GRU → results.
/// Requires the backend gateway at AppConfig.apiBaseUrl (http://10.0.2.2:8000 on the emulator).
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('glucose forecast returns real predictions from the gateway',
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

    final button = find.widgetWithText(FilledButton, 'Get 4-hour estimate');
    await tester.ensureVisible(button);
    await tester.pumpAndSettle();
    await tester.tap(button);

    // Wait for the real HTTP round trip. Poll instead of pumpAndSettle, because
    // the loading spinner keeps animating while the request is in flight.
    final resultTitle = find.text('Estimated glucose, next 4 hours');
    final errorIcon = find.byIcon(Icons.error_outline);
    for (var i = 0; i < 300; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      if (resultTitle.evaluate().isNotEmpty ||
          errorIcon.evaluate().isNotEmpty) {
        break;
      }
    }

    expect(errorIcon, findsNothing,
        reason: 'The forecast request returned an error.');
    expect(resultTitle, findsOneWidget);

    // The 16 values are in a collapsed section.
    final allValues = find.text('All 16 estimates');
    await tester.ensureVisible(allValues);
    await tester.pumpAndSettle();
    await tester.tap(allValues);
    await tester.pumpAndSettle();

    expect(find.text('+15 min'), findsOneWidget);
    expect(find.text('+4h'), findsOneWidget);
    expect(find.textContaining('Highest estimate:'), findsOneWidget);
    // The corrected single-step GRU served by the backend (routes.MODEL_VERSION).
    expect(find.textContaining('gru-single-step-premeal-fix-seed42-049cb23b'),
        findsOneWidget);
  });
}
