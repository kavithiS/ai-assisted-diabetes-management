import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/foot_monitor/c4_standalone.dart';

void main() {
  testWidgets('the C4 entry point opens on the foot check screen', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const C4StandaloneApp());

    expect(find.text('Foot Check'), findsOneWidget);
    expect(find.text('Analyse Photo'), findsOneWidget);
  });
}
