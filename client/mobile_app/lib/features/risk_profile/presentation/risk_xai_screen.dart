import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../c3_theme.dart';
import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import 'risk_controller.dart';
import 'risk_recommendations_screen.dart';
import 'widgets/c3_widgets.dart';

/// Plain-language view of factors that shaped the estimate.
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
          // Built from the factor names, not the server's longer technical summary.
          AiExplanationCard(
              text: C3Strings.mainReasons(raising.take(2).map((f) => f.readable).toList()),
              footnote: C3Strings.shapFootnote),
          const SizedBox(height: 18),
          FilledButton(
            onPressed: () => c3Push<void>(
              context,
              RiskRecommendationsScreen(
                assessment: assessment,
                controller: controller,
                profile: profile,
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
