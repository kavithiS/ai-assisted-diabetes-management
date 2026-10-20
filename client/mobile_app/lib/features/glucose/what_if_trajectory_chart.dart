import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

/// Series colours. The current meal is a dashed neutral line and the what-if
/// meal a solid teal line, so the two stay distinct without relying on colour
/// alone.
const whatIfCurrentColor = Color(0xFF1B2A41);
const whatIfScenarioColor = Color(0xFF00796B);

/// Line chart comparing the current meal's forecast with the what-if forecast.
/// Both series share one x-axis (minutes after the meal) and one y-axis (mg/dL).
class WhatIfTrajectoryChart extends StatelessWidget {
  const WhatIfTrajectoryChart({
    super.key,
    required this.horizonMinutes,
    required this.currentPredictions,
    required this.scenarioPredictions,
  })  : assert(horizonMinutes.length == currentPredictions.length),
        assert(horizonMinutes.length == scenarioPredictions.length),
        assert(horizonMinutes.length > 1);

  final List<int> horizonMinutes;

  /// Model estimates for the meal as entered.
  final List<double> currentPredictions;

  /// Model estimates for the meal with the simulated carbohydrate amount.
  final List<double> scenarioPredictions;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final all = [...currentPredictions, ...scenarioPredictions];
    final low = all.reduce((a, b) => a < b ? a : b);
    final high = all.reduce((a, b) => a > b ? a : b);

    // Keep a visible range even when both curves are nearly flat.
    final span = high - low;
    final padding = span < 20 ? (20 - span) / 2 : span * 0.1;
    final minY = low - padding;
    final maxY = high + padding;

    LineChartBarData series(List<double> values, Color color,
        {List<int>? dashArray}) {
      return LineChartBarData(
        spots: [
          for (var i = 0; i < values.length; i++)
            FlSpot(horizonMinutes[i].toDouble(), values[i]),
        ],
        color: color,
        barWidth: 2.5,
        dashArray: dashArray,
        dotData: const FlDotData(show: false),
      );
    }

    final currentLow = currentPredictions.reduce((a, b) => a < b ? a : b);
    final currentHigh = currentPredictions.reduce((a, b) => a > b ? a : b);
    final scenarioLow = scenarioPredictions.reduce((a, b) => a < b ? a : b);
    final scenarioHigh = scenarioPredictions.reduce((a, b) => a > b ? a : b);

    return Semantics(
      label:
          'Chart of estimated glucose over four hours. Current meal ranges from '
          '${currentLow.round()} to ${currentHigh.round()} mg/dL. What-if meal ranges from '
          '${scenarioLow.round()} to ${scenarioHigh.round()} mg/dL.',
      child: SizedBox(
        height: 220,
        width: double.infinity,
        child: LineChart(
          LineChartData(
            minX: horizonMinutes.first.toDouble(),
            maxX: horizonMinutes.last.toDouble(),
            minY: minY,
            maxY: maxY,
            lineBarsData: [
              series(currentPredictions, whatIfCurrentColor,
                  dashArray: const [6, 4]),
              series(scenarioPredictions, whatIfScenarioColor),
            ],
            gridData: FlGridData(
              drawVerticalLine: false,
              horizontalInterval: (maxY - minY) / 2,
              getDrawingHorizontalLine: (_) => FlLine(
                color: theme.colorScheme.outlineVariant,
                strokeWidth: 1,
              ),
            ),
            borderData: FlBorderData(show: false),
            titlesData: FlTitlesData(
              topTitles: const AxisTitles(),
              rightTitles: const AxisTitles(),
              leftTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 40,
                  interval: (maxY - minY) / 2,
                  getTitlesWidget: (value, meta) => SideTitleWidget(
                    meta: meta,
                    child: Text('${value.round()}',
                        style: theme.textTheme.labelSmall),
                  ),
                ),
              ),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 24,
                  interval: 15,
                  // Whole hours only, as on the forecast chart.
                  getTitlesWidget: (value, meta) => value.round() % 60 == 0
                      ? SideTitleWidget(
                          meta: meta,
                          child: Text('${value.round() ~/ 60}h',
                              style: theme.textTheme.labelSmall),
                        )
                      : const SizedBox.shrink(),
                ),
              ),
            ),
            lineTouchData: LineTouchData(
              touchTooltipData: LineTouchTooltipData(
                getTooltipColor: (_) => theme.colorScheme.inverseSurface,
                getTooltipItems: (spots) => [
                  for (final spot in spots)
                    LineTooltipItem(
                      '${spot.barIndex == 0 ? 'Current' : 'What-if'}: '
                      '${spot.y.round()} mg/dL\n+${spot.x.round()} min',
                      TextStyle(color: theme.colorScheme.onInverseSurface),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
