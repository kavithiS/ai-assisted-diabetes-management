import 'package:flutter/material.dart';

import '../../c3_strings.dart';
import '../../domain/risk_assessment.dart';
import '../risk_controller.dart';

/// Band shown as words + icon + colour, so colour is never the only cue (WCAG 2.2).
class BandCard extends StatelessWidget {
  const BandCard({super.key, required this.band});

  final RiskBand band;

  static String label(RiskBand band) => switch (band) {
        RiskBand.low => C3Strings.bandLow,
        RiskBand.moderate => C3Strings.bandModerate,
        RiskBand.high => C3Strings.bandHigh,
      };

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final (icon, background, foreground) = switch (band) {
      RiskBand.low => (
          Icons.check_circle_outline,
          scheme.secondaryContainer,
          scheme.onSecondaryContainer
        ),
      RiskBand.moderate => (
          Icons.info_outline,
          scheme.tertiaryContainer,
          scheme.onTertiaryContainer
        ),
      RiskBand.high => (Icons.priority_high, scheme.errorContainer, scheme.onErrorContainer),
    };
    final text = '${C3Strings.bandPrefix}${label(band)}';
    return Semantics(
      label: text,
      excludeSemantics: true,
      child: Card(
        color: background,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(icon, size: 40, color: foreground),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  text,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(color: foreground),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Coloured notice box with an icon (referral, warnings, disclaimer).
class NoticeBox extends StatelessWidget {
  const NoticeBox({super.key, required this.icon, required this.text, this.strong = false});

  final IconData icon;
  final String text;
  final bool strong;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final background = strong ? scheme.errorContainer : scheme.surfaceContainerHighest;
    final foreground = strong ? scheme.onErrorContainer : scheme.onSurfaceVariant;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(12)),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: foreground),
          const SizedBox(width: 12),
          Expanded(child: Text(text, style: TextStyle(color: foreground))),
        ],
      ),
    );
  }
}

/// Shown when the gateway cannot be reached: how to start the server, and a retry.
class ServerDownHint extends StatelessWidget {
  const ServerDownHint({super.key, required this.onCheckAgain});

  final VoidCallback onCheckAgain;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const NoticeBox(
              icon: Icons.power_off_outlined,
              text: '${C3Strings.serverDownTitle}\n${C3Strings.serverDownBody}',
              strong: true,
            ),
            TextButton.icon(
              onPressed: onCheckAgain,
              icon: const Icon(Icons.refresh),
              label: const Text(C3Strings.checkAgain),
            ),
          ],
        ),
      );
}

class DemoBanner extends StatelessWidget {
  const DemoBanner({super.key});

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.only(bottom: 12),
        child: NoticeBox(icon: Icons.science_outlined, text: C3Strings.demoBanner, strong: true),
      );
}

/// SHAP factors as ranked bars. Bar length = relative size of the contribution; the
/// direction is written in words and shown with an arrow. No numbers are shown.
class FactorBars extends StatelessWidget {
  const FactorBars({super.key, required this.factors});

  final List<ShapFactor> factors;

  @override
  Widget build(BuildContext context) {
    if (factors.isEmpty) return const SizedBox.shrink();
    final largest = factors.map((f) => f.shap.abs()).reduce((a, b) => a > b ? a : b);
    final scheme = Theme.of(context).colorScheme;
    return Column(
      children: [
        for (final factor in factors)
          _FactorBar(
            factor: factor,
            share: largest == 0 ? 0 : factor.shap.abs() / largest,
            colour: factor.shap > 0 ? scheme.error : scheme.primary,
          ),
      ],
    );
  }
}

class _FactorBar extends StatelessWidget {
  const _FactorBar({required this.factor, required this.share, required this.colour});

  final ShapFactor factor;
  final double share;
  final Color colour;

  @override
  Widget build(BuildContext context) {
    final raises = factor.shap > 0;
    final direction = raises ? C3Strings.raises : C3Strings.lowers;
    return Semantics(
      label: '${factor.readable}, $direction',
      excludeSemantics: true,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(raises ? Icons.arrow_upward : Icons.arrow_downward, size: 18, color: colour),
                const SizedBox(width: 6),
                Expanded(child: Text('${factor.readable}: $direction')),
              ],
            ),
            const SizedBox(height: 4),
            LayoutBuilder(
              builder: (context, constraints) => Container(
                height: 10,
                width: constraints.maxWidth * share.clamp(0.04, 1.0),
                decoration: BoxDecoration(color: colour, borderRadius: BorderRadius.circular(5)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Connection status chip. Tap = check again, long-press = settings (hidden).
class ConnectionIndicator extends StatelessWidget {
  const ConnectionIndicator({
    super.key,
    required this.controller,
    required this.onOpenSettings,
  });

  final RiskController controller;
  final VoidCallback onOpenSettings;

  @override
  Widget build(BuildContext context) {
    final (icon, text) = controller.isDemoData
        ? (Icons.science_outlined, C3Strings.demoData)
        : switch (controller.gateway) {
            GatewayState.checking => (Icons.sync, C3Strings.checking),
            GatewayState.online => (Icons.cloud_done_outlined, C3Strings.online),
            GatewayState.modelNotLoaded => (Icons.cloud_queue, C3Strings.notLoaded),
            GatewayState.offline => (Icons.cloud_off_outlined, C3Strings.offline),
          };
    // One button for screen readers, kept apart from the heading next to it (container),
    // with the chip's own semantics hidden so it is not also read as a checkbox.
    return Semantics(
      container: true,
      button: true,
      label: '$text ${C3Strings.connectionButtonHint}',
      onTap: controller.checkConnection,
      onLongPress: onOpenSettings,
      excludeSemantics: true,
      child: GestureDetector(
        onLongPress: onOpenSettings,
        child: ActionChip(
          avatar: Icon(icon, size: 18),
          label: Text(text),
          onPressed: controller.checkConnection,
        ),
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 8),
        child: Semantics(
          header: true,
          child: Text(text, style: Theme.of(context).textTheme.titleMedium),
        ),
      );
}
