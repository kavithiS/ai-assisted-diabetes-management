import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../data/foot_analysis.dart';
import '../foot_monitor_style.dart';

/// Shows an estimated risk band and recommendations. Never shows a model score.
class FootResultView extends StatelessWidget {
  const FootResultView({
    super.key,
    required this.analysis,
    required this.onScanAgain,
    this.image,
  });

  final FootAnalysis analysis;
  final VoidCallback onScanAgain;
  final Uint8List? image;

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(22, 16, 22, 24),
        children: [
          const Text('Foot Check Result', style: FootMonitorStyle.title),
          const SizedBox(height: 16),
          if (analysis.isMock) ...[
            const _Notice(
              icon: Icons.science_outlined,
              text: 'Demo result. No trained model is connected yet, so this result is '
                  'synthetic and says nothing about your foot.',
            ),
            const SizedBox(height: 14),
          ],
          RiskBandCard(band: analysis.riskBand),
          const SizedBox(height: 14),
          if (image != null) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(FootMonitorStyle.cardRadius),
              child: Image.memory(image!, height: 180, fit: BoxFit.cover),
            ),
            const SizedBox(height: 14),
          ],
          Container(
            padding: const EdgeInsets.all(16),
            decoration: FootMonitorStyle.cardDecoration(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('WHAT YOU CAN DO', style: FootMonitorStyle.sectionLabel),
                const SizedBox(height: 8),
                for (final recommendation in analysis.recommendations)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Padding(
                          padding: EdgeInsets.only(top: 1),
                          child: Icon(Icons.check_circle_outline,
                              size: 17, color: FootMonitorStyle.primary),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(recommendation,
                              style: const TextStyle(
                                  fontSize: 13.5, height: 1.45, color: FootMonitorStyle.text)),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          _Notice(icon: Icons.warning_amber_rounded, text: analysis.disclaimer),
          const SizedBox(height: 18),
          FilledButton.icon(
            style: FootMonitorStyle.primaryButton(),
            onPressed: onScanAgain,
            icon: const Icon(Icons.refresh),
            label: const Text('Scan Again'),
          ),
        ],
      );
}

/// The band as words, an icon and a colour, so colour is never the only cue.
class RiskBandCard extends StatelessWidget {
  const RiskBandCard({super.key, required this.band});

  final FootRiskBand band;

  static String label(FootRiskBand band) => switch (band) {
        FootRiskBand.low => 'Low',
        FootRiskBand.medium => 'Medium',
        FootRiskBand.high => 'High',
      };

  static String message(FootRiskBand band) => switch (band) {
        FootRiskBand.low => 'No signs of concern were estimated in this photo.',
        FootRiskBand.medium =>
          'Some changes were estimated. Please show this foot to your doctor or nurse.',
        FootRiskBand.high =>
          'Possible signs of a foot ulcer were estimated. Please seek medical advice soon.',
      };

  @override
  Widget build(BuildContext context) {
    final (icon, foreground, background) = switch (band) {
      FootRiskBand.low =>
        (Icons.check_circle_outline, FootMonitorStyle.success, FootMonitorStyle.successBg),
      FootRiskBand.medium =>
        (Icons.info_outline, FootMonitorStyle.warning, FootMonitorStyle.warningBg),
      FootRiskBand.high =>
        (Icons.priority_high, FootMonitorStyle.danger, FootMonitorStyle.dangerBg),
    };
    final title = 'Estimated risk: ${label(band)}';
    return Semantics(
      label: '$title. ${message(band)}',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration:
            FootMonitorStyle.cardDecoration(color: background, borderColor: foreground),
        child: Row(
          children: [
            Icon(icon, size: 40, color: foreground),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: TextStyle(
                          fontSize: 18, fontWeight: FontWeight.w800, color: foreground)),
                  const SizedBox(height: 4),
                  Text(message(band), style: FootMonitorStyle.body),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: FootMonitorStyle.warningBg,
          borderRadius: BorderRadius.circular(FootMonitorStyle.controlRadius),
          border: Border.all(color: const Color(0xFFF1DDB1)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 15, color: FootMonitorStyle.warningText),
            const SizedBox(width: 8),
            Expanded(
              child: Text(text,
                  style: const TextStyle(
                      fontSize: 12, height: 1.45, color: FootMonitorStyle.warningText)),
            ),
          ],
        ),
      );
}
