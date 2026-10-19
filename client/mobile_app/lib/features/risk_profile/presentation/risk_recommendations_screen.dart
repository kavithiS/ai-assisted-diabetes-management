import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../c3_theme.dart';
import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import 'risk_controller.dart';
import 'risk_whatif_screen.dart';
import 'widgets/c3_widgets.dart';

/// "Recommendations" (prototype Module 3): the top-priority template and the others, all
/// from the server's fixed rule base and marked provisional. Never medicine changes.
class RiskRecommendationsScreen extends StatelessWidget {
  const RiskRecommendationsScreen({
    super.key,
    required this.assessment,
    this.controller,
    this.profile,
  });

  final RiskAssessment assessment;
  final RiskController? controller;
  final RiskProfile? profile;

  @override
  Widget build(BuildContext context) {
    final items = assessment.recommendations;
    return Scaffold(
      appBar: AppBar(title: const Text(C3Strings.recommendationsTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
        children: [
          const C3Label(C3Strings.personalised),
          if (items.isEmpty)
            const Card(
              child: Padding(padding: EdgeInsets.all(16), child: Text(C3Strings.noRecommendations)),
            )
          else ...[
            _TopPriority(item: items.first),
            if (items.length > 1) ...[
              const C3Label(C3Strings.additional),
              for (final item in items.skip(1)) _Suggestion(item: item),
            ],
          ],
          const SizedBox(height: 10),
          const Text(C3Strings.recommendationsFooter,
              style: TextStyle(fontSize: 11.5, color: C3Colors.text2)),
          if (controller != null && profile != null && assessment.dhs != null) ...[
            const SizedBox(height: 14),
            OutlinedButton(
              onPressed: () => Navigator.of(context).push(
                c3Route<void>(
                  RiskWhatIfScreen(controller: controller!, profile: profile!, base: assessment),
                ),
              ),
              child: const Text(C3Strings.exploreWhatIf),
            ),
          ],
        ],
      ),
    );
  }
}

class _TopPriority extends StatelessWidget {
  const _TopPriority({required this.item});

  final Recommendation item;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: C3Colors.primaryLight,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Text(
                      C3Strings.topPriority,
                      style: TextStyle(
                          color: C3Colors.primaryDark, fontWeight: FontWeight.w700, fontSize: 12),
                    ),
                  ),
                  ProvisionalTag(text: item.reviewStatus),
                ],
              ),
              const SizedBox(height: 10),
              Text(item.title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
              if (item.current != null && item.target != null) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(child: _Metric(label: C3Strings.current, value: item.current!)),
                    Expanded(child: _Metric(label: C3Strings.target, value: item.target!)),
                  ],
                ),
              ],
              const SizedBox(height: 10),
              Text(item.action),
              if (item.seekCare != null) ...[
                const SizedBox(height: 8),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.local_hospital_outlined, size: 18, color: C3Colors.primary),
                    const SizedBox(width: 6),
                    Expanded(child: Text(item.seekCare!)),
                  ],
                ),
              ],
              const SizedBox(height: 8),
              Text(
                C3Strings.because(item.trigger, item.window, item.raisedEstimate),
                style: const TextStyle(fontSize: 11.5, color: C3Colors.text2),
              ),
            ],
          ),
        ),
      );
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11.5, color: C3Colors.text2)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
        ],
      );
}

class _Suggestion extends StatelessWidget {
  const _Suggestion({required this.item});

  final Recommendation item;

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          leading: Icon(
            item.seekCare != null ? Icons.local_hospital_outlined : Icons.check_circle_outline,
            color: C3Colors.primary,
          ),
          title: Text(item.title, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(
            [item.action, if (item.seekCare != null) item.seekCare!].join('\n'),
          ),
        ),
      );
}
