import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

/// Line chart of the forecast: one point per horizon, x-axis in minutes after the meal,
/// y-axis in mg/dL.
///
/// Draws only the values it is given. It does not draw target ranges or
/// intervals, because the API does not provide them.
class GlucoseTrajectoryChart extends StatelessWidget {
  const GlucoseTrajectoryChart({
    super.key,
    required this.predictions,
    required this.horizonMinutes,
    this.peakIndex,
  })  : assert(predictions.length == horizonMinutes.length),
        assert(predictions.length > 1);

  final List<double> predictions;
  final List<int> horizonMinutes;

  /// Point to highlight as the highest estimate, if any.
  final int? peakIndex;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final lineColor = theme.colorScheme.primary;
    final low = predictions.reduce((a, b) => a < b ? a : b);
    final high = predictions.reduce((a, b) => a > b ? a : b);

    // Keep a visible range even when the forecast is nearly flat.
    final span = high - low;
    final padding = span < 20 ? (20 - span) / 2 : span * 0.1;
    final minY = low - padding;
    final maxY = high + padding;

    return Semantics(
      label:
          'Chart of estimated glucose over four hours, from ${low.round()} to ${high.round()} mg/dL.',
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
              LineChartBarData(
                spots: [
                  for (var i = 0; i < predictions.length; i++)
                    FlSpot(horizonMinutes[i].toDouble(), predictions[i]),
                ],
                color: lineColor,
                barWidth: 2.5,
                dotData: FlDotData(
                  getDotPainter: (spot, percent, bar, index) =>
                      FlDotCirclePainter(
                    radius: index == peakIndex ? 5 : 3,
                    color: index == peakIndex
                        ? theme.colorScheme.tertiary
                        : lineColor,
                  ),
                ),
              ),
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
                  // Label whole hours only, to keep the axis readable.
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
                      '+${spot.x.round()} min\n${spot.y.round()} mg/dL',
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
