import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../c3_strings.dart';
import '../../c3_theme.dart';
import '../../domain/risk_assessment.dart';

/// Colour, background and icon for a band. Words + icon always go with the colour.
(Color, Color, IconData) bandStyle(RiskBand band) => switch (band) {
      RiskBand.low => (C3Colors.success, C3Colors.successBg, Icons.check_circle_outline),
      RiskBand.moderate => (C3Colors.warning, C3Colors.warningBg, Icons.info_outline),
      RiskBand.high => (C3Colors.danger, C3Colors.dangerBg, Icons.priority_high),
    };

String bandWord(RiskBand band) => switch (band) {
      RiskBand.low => C3Strings.bandLow,
      RiskBand.moderate => C3Strings.bandModerate,
      RiskBand.high => C3Strings.bandHigh,
    };

/// Pill such as "High estimated risk" (prototype badge).
class BandBadge extends StatelessWidget {
  const BandBadge({super.key, required this.band, this.large = false});

  final RiskBand band;
  final bool large;

  @override
  Widget build(BuildContext context) {
    final (colour, background, icon) = bandStyle(band);
    final text = '${bandWord(band)} ${C3Strings.estimatedRisk}';
    return Semantics(
      label: '${C3Strings.bandPrefix}${bandWord(band)}',
      excludeSemantics: true,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: large ? 16 : 12, vertical: large ? 7 : 5),
        decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(20)),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: large ? 18 : 15, color: colour),
            const SizedBox(width: 6),
            Text(
              text,
              style: TextStyle(
                color: colour,
                fontWeight: FontWeight.w700,
                fontSize: large ? 14 : 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Small "Provisional" tag for the DHS and recommendations.
class ProvisionalTag extends StatelessWidget {
  const ProvisionalTag({super.key, this.text = C3Strings.provisional});

  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: C3Colors.warningBg,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          text,
          style:
              const TextStyle(color: C3Colors.warning, fontSize: 11, fontWeight: FontWeight.w700),
        ),
      );
}

/// DHS ring gauge (prototype "Your Risk Assessment"): the number over 100.
class DhsGauge extends StatelessWidget {
  const DhsGauge({super.key, required this.score, this.colour = C3Colors.primary, this.size = 180});

  final double score;
  final Color colour;
  final double size;

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
        tween: Tween<double>(begin: 0, end: score.clamp(0, 100).toDouble()),
        duration: const Duration(milliseconds: 900),
        curve: Curves.easeOutCubic,
        builder: (context, value, _) => Semantics(
          label: C3Strings.scoreSemantics(score.round()),
          excludeSemantics: true,
          child: SizedBox(
            width: size,
            height: size,
            child: CustomPaint(
              painter: _RingPainter(value / 100, colour),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      value.round().toString(),
                      style: const TextStyle(
                        fontSize: 38,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const Text(
                      C3Strings.scoreDenominator,
                      style: TextStyle(fontSize: 13, color: C3Colors.text2),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.fraction, this.colour);

  final double fraction;
  final Color colour;

  @override
  void paint(Canvas canvas, Size size) {
    const stroke = 14.0;
    final rect = Offset.zero & size;
    final ring = rect.deflate(stroke / 2);
    final track = Paint()
      ..color = C3Colors.border
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke;
    final value = Paint()
      ..color = colour
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(ring, 0, 2 * math.pi, false, track);
    canvas.drawArc(ring, -math.pi / 2, 2 * math.pi * fraction.clamp(0.0, 1.0), false, value);
  }

  @override
  bool shouldRepaint(_RingPainter old) => old.fraction != fraction || old.colour != colour;
}

/// One answered DHS question with a status icon (prototype "Risk Factors" list).
class FactorStatusRow extends StatelessWidget {
  const FactorStatusRow({super.key, required this.title, required this.subtitle, this.score});

  final String title;
  final String subtitle;

  /// 1 favourable, 0.5 in between, 0 needs attention; null = information only.
  final double? score;

  @override
  Widget build(BuildContext context) {
    final (icon, colour, background, word) = switch (score) {
      null => (Icons.info_outline, C3Colors.primary, C3Colors.primaryLight, ''),
      >= 1.0 => (Icons.check, C3Colors.success, C3Colors.successBg, C3Strings.statusGood),
      >= 0.5 => (Icons.remove, C3Colors.warning, C3Colors.warningBg, C3Strings.statusMixed),
      _ => (Icons.priority_high, C3Colors.danger, C3Colors.dangerBg, C3Strings.statusAttention),
    };
    return Semantics(
      label: '$title, $subtitle${word.isEmpty ? '' : ', $word'}',
      excludeSemantics: true,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(10)),
              child: Icon(icon, size: 18, color: colour),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
                  Text(subtitle, style: const TextStyle(color: C3Colors.text2, fontSize: 12.5)),
                ],
              ),
            ),
            if (word.isNotEmpty)
              Text(word,
                  style: TextStyle(color: colour, fontSize: 12, fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}

/// Prototype XAI bars: one section per direction, bar length = relative size of the
/// contribution to the model's estimate. No numbers (no probability parts on screen).
class ContributionBars extends StatelessWidget {
  const ContributionBars({super.key, required this.factors, required this.raising});

  final List<ShapFactor> factors;
  final bool raising;

  @override
  Widget build(BuildContext context) {
    if (factors.isEmpty) {
      return const Text(C3Strings.noneInThisGroup, style: TextStyle(color: C3Colors.text2));
    }
    final largest = factors.map((f) => f.shap.abs()).reduce(math.max);
    final colour = raising ? C3Colors.danger : C3Colors.success;
    final word = raising ? C3Strings.raises : C3Strings.lowers;
    return Column(
      children: [
        for (final factor in factors)
          Semantics(
            label: '${factor.readable}, $word',
            excludeSemantics: true,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: [
                  SizedBox(
                    width: 130,
                    child: Text(factor.readable, style: const TextStyle(fontSize: 13)),
                  ),
                  Expanded(
                    child: LayoutBuilder(
                      builder: (context, constraints) => Stack(
                        children: [
                          Container(
                            height: 10,
                            decoration: BoxDecoration(
                              color: C3Colors.border,
                              borderRadius: BorderRadius.circular(5),
                            ),
                          ),
                          Container(
                            height: 10,
                            width: constraints.maxWidth *
                                (largest == 0 ? 0.0 : factor.shap.abs() / largest).clamp(0.05, 1.0),
                            decoration: BoxDecoration(
                              color: colour,
                              borderRadius: BorderRadius.circular(5),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Icon(raising ? Icons.arrow_upward : Icons.arrow_downward,
                      size: 16, color: colour),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

/// Prototype "AI Explanation" card with the sparkle tag.
class AiExplanationCard extends StatelessWidget {
  const AiExplanationCard({super.key, required this.text, required this.footnote});

  final String text;
  final String footnote;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: C3Colors.primaryLight,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.auto_awesome, size: 16, color: C3Colors.primaryDark),
                SizedBox(width: 6),
                Text(
                  C3Strings.aiExplanation,
                  style: TextStyle(color: C3Colors.primaryDark, fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 6),
            // Fixed dark text: the card stays light in dark mode too.
            Text(text, style: const TextStyle(fontSize: 13, height: 1.45, color: C3Colors.text)),
            const SizedBox(height: 6),
            Text(footnote, style: const TextStyle(fontSize: 11, color: C3Colors.text2)),
          ],
        ),
      );
}

/// Small uppercase label above a section (prototype `label-sm`).
class C3Label extends StatelessWidget {
  const C3Label(this.text, {super.key, this.colour = C3Colors.text2});

  final String text;
  final Color colour;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 18, bottom: 8),
        child: Semantics(
          header: true,
          child: Text(
            text.toUpperCase(),
            style: TextStyle(
              color: colour,
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.4,
            ),
          ),
        ),
      );
}

/// Quiet placeholder shown while a check is loading.
class C3LoadingSkeleton extends StatelessWidget {
  const C3LoadingSkeleton({super.key, this.lines = 3});

  final int lines;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (var i = 0; i < lines; i++) ...[
                if (i > 0) const SizedBox(height: 12),
                FractionallySizedBox(
                  widthFactor: i == lines - 1 ? 0.58 : 0.86,
                  child: Container(
                    height: 14,
                    decoration: BoxDecoration(
                      color: C3Colors.border,
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      );
}
