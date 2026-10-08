import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/main.dart';

void main() {
  testWidgets('home screen shows the five placeholder tabs', (tester) async {
    await tester.pumpWidget(const DiaCareApp());

    for (final label in ['Meal Scan', 'Glucose', 'Risk Profile', 'Foot Monitor', 'Dashboard']) {
      expect(find.text(label), findsWidgets);
    }
    expect(find.text('Meal Scan — placeholder (C1)'), findsOneWidget);

    await tester.tap(find.text('Glucose'));
    await tester.pumpAndSettle();

    expect(find.text('Glucose — placeholder (C2)'), findsOneWidget);
  });
}
