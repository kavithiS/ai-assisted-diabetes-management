import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../c3_theme.dart';
import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import 'risk_controller.dart';
import 'risk_questionnaire_screen.dart';
import 'widgets/c3_widgets.dart';

/// "Explore Your Risk" (prototype what-if): change activity or cholesterol and ask the
/// server for the DHS again. The app computes nothing itself; the preview is not saved.
class RiskWhatIfScreen extends StatefulWidget {
  const RiskWhatIfScreen({
    super.key,
    required this.controller,
    required this.profile,
    required this.base,
  });

  final RiskController controller;
  final RiskProfile profile;
  final RiskAssessment base;

  @override
  State<RiskWhatIfScreen> createState() => _RiskWhatIfScreenState();
}

class _RiskWhatIfScreenState extends State<RiskWhatIfScreen> {
  late String? _activity = widget.profile.physicalActivity;
  late String? _cholesterol = widget.profile.cholesterolLevel;
  RiskAssessment? _scenario;
  Object? _error;
  bool _busy = false;

  Future<void> _estimate() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final scenario = await widget.controller.simulate(
        widget.profile.withLifestyle(physicalActivity: _activity, cholesterolLevel: _cholesterol),
      );
      if (mounted) setState(() => _scenario = scenario);
    } on Object catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final before = widget.base.dhs!.todayScore;
    final after = _scenario?.dhs?.todayScore;
    return Scaffold(
      appBar: AppBar(title: const Text(C3Strings.whatIfTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
        children: [
          const Text(C3Strings.whatIfIntro, style: TextStyle(color: C3Colors.text2)),
          const SizedBox(height: 12),
          ChoiceGroup<String>(
            label: C3Strings.activityLevel,
            value: _activity,
            options: const {
              'low': C3Strings.activityLow,
              'moderate': C3Strings.activityModerate,
              'high': C3Strings.activityHigh,
            },
            onChanged: (v) => setState(() => _activity = v),
          ),
          ChoiceGroup<String>(
            label: C3Strings.cholesterolManagement,
            value: _cholesterol,
            options: const {
              'normal': C3Strings.cholesterolNormal,
              'borderline_high': C3Strings.cholesterolBorderlineHigh,
              'high': C3Strings.cholesterolHigh,
            },
            onChanged: (v) => setState(() => _cholesterol = v),
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: _busy ? null : _estimate,
            child: Text(_busy ? C3Strings.estimating : C3Strings.estimate),
          ),
          if (_error != null)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text(C3Strings.connectionFailed),
            ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  const Text(C3Strings.estimatedDhs, style: TextStyle(color: C3Colors.text2)),
                  const SizedBox(height: 8),
                  Text(
                    after == null
                        ? before.round().toString()
                        : '${before.round()} → ${after.round()}',
                    style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 8),
                  BandBadge(band: (_scenario ?? widget.base).band!),
                  const SizedBox(height: 8),
                  const ProvisionalTag(text: C3Strings.provisionalScore),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          const Text(C3Strings.whatIfBandNote, style: TextStyle(fontSize: 12)),
          const SizedBox(height: 6),
          const Text(C3Strings.whatIfDisclaimer,
              style: TextStyle(fontSize: 11.5, color: C3Colors.text2)),
        ],
      ),
    );
  }
}
