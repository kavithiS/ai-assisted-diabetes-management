import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/features/glucose/glucose_trajectory_chart.dart';

final _predictions = <double>[
  120, 135, 150, 162, 171.6, 168, 160, 150, //
  140, 132, 126, 121, 118, 116, 115, 114,
];
final _horizons = List<int>.generate(16, (i) => (i + 1) * 15);

Future<LineChartData> _pumpChart(WidgetTester tester, {int? peakIndex}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: GlucoseTrajectoryChart(
          predictions: _predictions,
          horizonMinutes: _horizons,
          peakIndex: peakIndex,
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return tester.widget<LineChart>(find.byType(LineChart)).data;
}

void main() {
  testWidgets('plots exactly the 16 returned values at their horizons',
      (tester) async {
    final data = await _pumpChart(tester);

    final spots = data.lineBarsData.single.spots;
    expect(spots, hasLength(16));
    for (var i = 0; i < 16; i++) {
      expect(spots[i].x, _horizons[i].toDouble());
      expect(spots[i].y, _predictions[i]);
    }
    expect(data.minX, 15);
    expect(data.maxX, 240);
  });

  testWidgets('keeps every value inside the visible range', (tester) async {
    final data = await _pumpChart(tester);

    expect(data.minY, lessThan(114));
    expect(data.maxY, greaterThan(171.6));
  });

  testWidgets('describes the range for screen readers', (tester) async {
    await _pumpChart(tester, peakIndex: 4);

    expect(
      find.byWidgetPredicate((widget) =>
          widget is Semantics &&
          widget.properties.label ==
              'Chart of estimated glucose over four hours, from 114 to 172 mg/dL.'),
      findsOneWidget,
    );
  });
}
