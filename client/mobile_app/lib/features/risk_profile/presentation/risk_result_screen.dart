import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../c3_theme.dart';
import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import 'risk_controller.dart';
import 'risk_questionnaire_screen.dart';
import 'risk_recommendations_screen.dart';
import 'risk_xai_screen.dart';
import 'widgets/c3_widgets.dart';
import 'widgets/risk_widgets.dart';

/// "Your Risk Assessment" (prototype Module 3): the Diabetic Health Score ring, the
/// model's estimated band, the referral note, and the way to the explanation and the
/// recommendations. Shows exactly what the server sent; never a probability.
class RiskResultView extends StatelessWidget {
  const RiskResultView({
    super.key,
    required this.assessment,
    this.isDemoData = false,
    this.controller,
    this.profile,
  });

  final RiskAssessment assessment;
  final bool isDemoData;

  /// Present for a fresh result (not for a history entry): enables "Update" and "What-if".
  final RiskController? controller;
  final RiskProfile? profile;

  void _openResearcherView(BuildContext context) {
    final info = assessment.researcherInfo;
    showModalBottomSheet<void>(
      context: context,
      builder: (context) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(C3Strings.researcherTitle, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            if (info == null)
              const Text(C3Strings.researcherOff)
            else ...[
              Text('Calibrated probability: ${info.riskProbability.toStringAsFixed(4)}'),
              for (final entry in info.thresholds.entries)
                Text('Cut-off ${entry.key}: ${entry.value.toStringAsFixed(4)}'),
              Text('Model: ${assessment.modelUsed} (${assessment.featureSet})'),
            ],
            if (assessment.dhs != null)
              Text(
                'DHS today ${assessment.dhs!.todayScore}, previous '
                '${assessment.dhs!.previousScore ?? '-'}, shown ${assessment.dhs!.score}',
              ),
          ],
        ),
      ),
    );
  }

  void _push(BuildContext context, Widget screen) =>
      Navigator.of(context).push(c3Route<void>(screen));

  @override
  Widget build(BuildContext context) {
    final children = <Widget>[
      if (isDemoData) const DemoBanner(),
      ...switch (assessment.status) {
        AssessmentStatus.ok => _okContent(context),
        AssessmentStatus.insufficientData => _insufficientContent(context),
        AssessmentStatus.invalidInput => _invalidContent(context),
      },
      const SizedBox(height: 20),
      NoticeBox(icon: Icons.medical_information_outlined, text: assessment.disclaimer),
    ];
    return Scaffold(
      appBar: AppBar(
        // Hidden researcher view: long-press the title.
        title: GestureDetector(
          onLongPress: () => _openResearcherView(context),
          child: const Text(C3Strings.resultTitle),
        ),
      ),
      body: ListView(padding: const EdgeInsets.fromLTRB(16, 0, 16, 24), children: children),
    );
  }

  List<Widget> _okContent(BuildContext context) {
    final band = assessment.band!;
    final dhs = assessment.dhs;
    final (bandColour, _, _) = bandStyle(band);
    return [
      Card(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            children: [
              if (dhs != null) ...[
                const Text(C3Strings.dhsName, style: TextStyle(color: C3Colors.text2)),
                const SizedBox(height: 10),
                DhsGauge(score: dhs.score, colour: bandColour),
                const SizedBox(height: 8),
                const ProvisionalTag(text: C3Strings.provisionalScore),
                const SizedBox(height: 14),
              ],
              BandBadge(band: band, large: true),
              const SizedBox(height: 10),
              const Text(
                C3Strings.resultSummary,
                textAlign: TextAlign.center,
                style: TextStyle(color: C3Colors.text2, fontSize: 12.5),
              ),
            ],
          ),
        ),
      ),
      if (assessment.referral != null) ...[
        const SizedBox(height: 8),
        NoticeBox(icon: Icons.local_hospital_outlined, text: assessment.referral!, strong: true),
      ],
      if (assessment.saved == false) ...[
        const SizedBox(height: 8),
        const NoticeBox(icon: Icons.cloud_off_outlined, text: C3Strings.notSaved),
      ],
      const SizedBox(height: 14),
      if (assessment.explanation != null)
        FilledButton.icon(
          onPressed: () => _push(
            context,
            RiskXaiScreen(assessment: assessment, controller: controller, profile: profile),
          ),
          icon: const Icon(Icons.auto_awesome),
          label: const Text(C3Strings.understandMyRisk),
        ),
      const SizedBox(height: 10),
      OutlinedButton(
        onPressed: () => _push(
          context,
          RiskRecommendationsScreen(
            assessment: assessment,
            controller: controller,
            profile: profile,
          ),
        ),
        child: Text(C3Strings.viewRecommendations(assessment.recommendations.length)),
      ),
      if (controller != null && profile != null) ...[
        const SizedBox(height: 10),
        TextButton(
          onPressed: () => _push(
            context,
            RiskQuestionnaireScreen(controller: controller!, initial: profile),
          ),
          child: const Text(C3Strings.updateHealthInfo),
        ),
      ],
      const SizedBox(height: 12),
      Text(
        assessment.imputedFields.isEmpty
            ? C3Strings.allAnswersUsed
            : C3Strings.imputedIntro +
                assessment.imputedFields.map((f) => c3FieldLabels[f] ?? f).join(', '),
        style: const TextStyle(fontSize: 12.5),
      ),
      if (assessment.modelUsed != null)
        Text(
          C3Strings.modelLine(
            assessment.modelUsed!,
            assessment.modelVersion ?? '?',
            assessment.featureSet == 'with_glucose',
          ),
          style: const TextStyle(fontSize: 11.5, color: C3Colors.text2),
        ),
    ];
  }

  List<Widget> _insufficientContent(BuildContext context) => [
        const NoticeBox(icon: Icons.help_outline, text: C3Strings.insufficientTitle),
        const SizedBox(height: 12),
        const Text(C3Strings.insufficientBody),
        for (final field in assessment.missingCriticalFields)
          ListTile(
            leading: const Icon(Icons.edit_note),
            title: Text(c3FieldLabels[field] ?? field),
          ),
        _answerAgainButton(context),
      ];

  List<Widget> _invalidContent(BuildContext context) => [
        const NoticeBox(icon: Icons.error_outline, text: C3Strings.invalidTitle, strong: true),
        const SizedBox(height: 12),
        for (final problem in assessment.problems)
          ListTile(leading: const Icon(Icons.close), title: Text(problem)),
        _answerAgainButton(context),
      ];

  Widget _answerAgainButton(BuildContext context) => OutlinedButton(
        onPressed: () => controller != null
            ? Navigator.of(context).pushReplacement(
                c3Route<void>(RiskQuestionnaireScreen(controller: controller!, initial: profile)),
              )
            : Navigator.of(context).pop(),
        child: const Text(C3Strings.answerQuestions),
      );
}
