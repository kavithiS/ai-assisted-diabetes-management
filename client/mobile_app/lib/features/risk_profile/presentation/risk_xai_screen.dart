import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../c3_theme.dart';
import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import 'risk_controller.dart';
import 'risk_recommendations_screen.dart';
import 'widgets/c3_widgets.dart';
import 'widgets/risk_widgets.dart';

/// "AI Explanation" (prototype Module 3): SHAP factors that raised or lowered the
/// model's estimate, the server's plain-language summary, and the LIME cross-check.
/// Bars have no numbers: SHAP values are parts of a probability.
class RiskXaiScreen extends StatelessWidget {
  const RiskXaiScreen({super.key, required this.assessment, this.controller, this.profile});

  final RiskAssessment assessment;
  final RiskController? controller;
  final RiskProfile? profile;

  @override
  Widget build(BuildContext context) {
    final explanation = assessment.explanation!;
    final raising = explanation.shap.where((f) => f.shap > 0).toList();
    final protective = explanation.shap.where((f) => f.shap <= 0).toList();
    final agreement = explanation.agreement;
    return Scaffold(
      appBar: AppBar(title: const Text(C3Strings.aiExplanation)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
        children: [
          const Text(
            C3Strings.factorsAffecting,
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          ),
          const C3Label(C3Strings.increasing, colour: C3Colors.danger),
          ContributionBars(factors: raising, raising: true),
          const C3Label(C3Strings.protective, colour: C3Colors.success),
          ContributionBars(factors: protective, raising: false),
          const SizedBox(height: 10),
          const Wrap(
            spacing: 16,
            children: [
              _Legend(colour: C3Colors.danger, text: C3Strings.legendIncreasing),
              _Legend(colour: C3Colors.success, text: C3Strings.legendProtective),
            ],
          ),
          AiExplanationCard(text: explanation.explanationText, footnote: C3Strings.shapFootnote),
          const C3Label(C3Strings.secondCheck),
          const Text(C3Strings.secondCheckIntro, style: TextStyle(fontSize: 13)),
          for (final factor in explanation.lime)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Icon(
                factor.weight > 0 ? Icons.arrow_upward : Icons.arrow_downward,
                color: factor.weight > 0 ? C3Colors.danger : C3Colors.success,
              ),
              title: Text(
                '${factor.readable}: ${factor.weight > 0 ? C3Strings.raises : C3Strings.lowers}',
              ),
              subtitle: Text(factor.rule),
            ),
          Text(C3Strings.agreement(agreement.shared.length, agreement.shapTop.length)),
          Text(C3Strings.limeFit(explanation.limeFidelity),
              style: const TextStyle(color: C3Colors.text2)),
          if (explanation.explanationQuality != 'consistent') ...[
            const SizedBox(height: 8),
            NoticeBox(icon: Icons.warning_amber_outlined, text: explanation.explanationQuality),
          ],
          const SizedBox(height: 18),
          FilledButton(
            onPressed: () => Navigator.of(context).push(
              c3Route<void>(
                RiskRecommendationsScreen(
                  assessment: assessment,
                  controller: controller,
                  profile: profile,
                ),
              ),
            ),
            child: Text(C3Strings.viewRecommendations(assessment.recommendations.length)),
          ),
        ],
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.colour, required this.text});

  final Color colour;
  final String text;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(color: colour, borderRadius: BorderRadius.circular(3)),
          ),
          const SizedBox(width: 6),
          Text(text, style: const TextStyle(fontSize: 11.5, color: C3Colors.text2)),
        ],
      );
}
