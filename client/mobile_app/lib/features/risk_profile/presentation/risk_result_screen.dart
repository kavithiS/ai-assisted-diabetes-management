import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../data/risk_api.dart';
import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import 'risk_controller.dart';
import 'widgets/risk_widgets.dart';

/// Sends one profile to C3 and shows the answer. Loading, error + Retry, then the result.
class RiskResultScreen extends StatefulWidget {
  const RiskResultScreen({super.key, required this.controller, required this.profile});

  final RiskController controller;
  final RiskProfile profile;

  @override
  State<RiskResultScreen> createState() => _RiskResultScreenState();
}

class _RiskResultScreenState extends State<RiskResultScreen> {
  late Future<RiskAssessment> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.controller.assess(widget.profile);
  }

  static bool _isServerDown(Object? error) =>
      error is RiskApiException &&
      (error.kind == RiskApiErrorKind.network || error.kind == RiskApiErrorKind.gateway);

  void _retry() {
    setState(() {
      _future = widget.controller.assess(widget.profile);
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<RiskAssessment>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const _Frame(
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text(C3Strings.estimating),
                ],
              ),
            ),
          );
        }
        if (snapshot.hasError) {
          return _Frame(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const NoticeBox(icon: Icons.cloud_off_outlined, text: C3Strings.errorTitle, strong: true),
                const SizedBox(height: 12),
                Text('${snapshot.error}'),
                if (_isServerDown(snapshot.error)) ServerDownHint(onCheckAgain: _retry),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _retry,
                  icon: const Icon(Icons.refresh),
                  label: const Text(C3Strings.retry),
                ),
              ],
            ),
          );
        }
        return RiskResultView(
          assessment: snapshot.data!,
          isDemoData: widget.controller.isDemoData,
        );
      },
    );
  }
}

class _Frame extends StatelessWidget {
  const _Frame({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) =>
      Scaffold(appBar: AppBar(title: const Text(C3Strings.resultTitle)), body: child);
}

/// Renders one assessment exactly as the server sent it. Used by the result and
/// history screens. Patient view: never shows a probability or a percentage.
class RiskResultView extends StatelessWidget {
  const RiskResultView({super.key, required this.assessment, this.isDemoData = false});

  final RiskAssessment assessment;
  final bool isDemoData;

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
          ],
        ),
      ),
    );
  }

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
      body: ListView(padding: const EdgeInsets.all(16), children: children),
    );
  }

  List<Widget> _okContent(BuildContext context) {
    final explanation = assessment.explanation;
    final modifiable = explanation?.shap.where((f) => f.factorType == 'modifiable').toList() ?? [];
    final other = explanation?.shap.where((f) => f.factorType != 'modifiable').toList() ?? [];
    return [
      BandCard(band: assessment.band!),
      if (assessment.referral != null) ...[
        const SizedBox(height: 12),
        NoticeBox(icon: Icons.local_hospital_outlined, text: assessment.referral!, strong: true),
      ],
      if (explanation != null) ...[
        const SizedBox(height: 16),
        Text(explanation.explanationText),
        if (modifiable.isNotEmpty) ...[
          const SectionTitle(C3Strings.workOn),
          FactorBars(factors: modifiable),
        ],
        if (other.isNotEmpty) ...[
          const SectionTitle(C3Strings.background),
          FactorBars(factors: other),
        ],
        const SizedBox(height: 8),
        Text(C3Strings.notCauses, style: Theme.of(context).textTheme.bodySmall),
        const SectionTitle(C3Strings.secondCheck),
        const Text(C3Strings.secondCheckIntro),
        for (final factor in explanation.lime)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Icon(factor.weight > 0 ? Icons.arrow_upward : Icons.arrow_downward),
            title: Text(
              '${factor.readable}: ${factor.weight > 0 ? C3Strings.raises : C3Strings.lowers}',
            ),
            subtitle: Text(factor.rule),
          ),
        const SizedBox(height: 8),
        Text(
          C3Strings.agreement(
            explanation.agreement.shared.length,
            explanation.agreement.shapTop.length,
          ),
        ),
        Text(C3Strings.limeFit(explanation.limeFidelity)),
        if (explanation.explanationQuality != 'consistent') ...[
          const SizedBox(height: 8),
          NoticeBox(icon: Icons.warning_amber_outlined, text: explanation.explanationQuality),
        ],
      ],
      const SizedBox(height: 16),
      Text(
        assessment.imputedFields.isEmpty
            ? C3Strings.allAnswersUsed
            : C3Strings.imputedIntro +
                assessment.imputedFields.map((f) => c3FieldLabels[f] ?? f).join(', '),
      ),
      if (assessment.modelUsed != null)
        Text(
          C3Strings.modelLine(
            assessment.modelUsed!,
            assessment.modelVersion ?? '?',
            assessment.featureSet == 'with_glucose',
          ),
          style: Theme.of(context).textTheme.bodySmall,
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
        OutlinedButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text(C3Strings.answerQuestions),
        ),
      ];

  List<Widget> _invalidContent(BuildContext context) => [
        const NoticeBox(icon: Icons.error_outline, text: C3Strings.invalidTitle, strong: true),
        const SizedBox(height: 12),
        for (final problem in assessment.problems)
          ListTile(leading: const Icon(Icons.close), title: Text(problem)),
        OutlinedButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text(C3Strings.answerQuestions),
        ),
      ];
}
