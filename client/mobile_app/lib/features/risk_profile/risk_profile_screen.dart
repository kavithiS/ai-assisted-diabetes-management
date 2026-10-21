import 'package:flutter/material.dart';

import 'c3_strings.dart';
import 'c3_theme.dart';
import 'presentation/risk_analysis_screen.dart';
import 'presentation/risk_controller.dart';
import 'presentation/risk_history_screen.dart';
import 'presentation/risk_questionnaire_screen.dart';
import 'presentation/risk_result_screen.dart';
import 'presentation/risk_settings_screen.dart';
import 'presentation/risk_xai_screen.dart';
import 'presentation/widgets/c3_widgets.dart';
import 'presentation/widgets/risk_widgets.dart';

/// Risk Profile (C3) tab: the prototype's "Diabetic Health Score" home. Entry point
/// imported by `lib/main.dart` (shared), so the class name and path stay the same.
///
/// The feature is split into `domain/` (contract models, presets, input ranges),
/// `data/` (repository, live API, mock, settings, history) and `presentation/`
/// (controller and the Module 3 screens). Every number comes from the server.
class RiskProfileScreen extends StatefulWidget {
  const RiskProfileScreen({super.key, this.controller});

  /// Injected in tests; the app creates its own.
  final RiskController? controller;

  @override
  State<RiskProfileScreen> createState() => _RiskProfileScreenState();
}

class _RiskProfileScreenState extends State<RiskProfileScreen> {
  late final RiskController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ?? RiskController();
    if (_ownsController) _controller.init();
  }

  @override
  void dispose() {
    if (_ownsController) _controller.dispose();
    super.dispose();
  }

  void _open(Widget screen) => c3Push<void>(context, screen);

  static String _when(DateTime t) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${C3Strings.today} ${two(t.hour)}:${two(t.minute)}';
  }

  List<Widget> _scoreCard() {
    final latest = _controller.latest;
    final profile = _controller.latestProfile;
    final dhs = latest?.dhs;
    if (latest == null || dhs == null || profile == null) {
      return const [
        Card(
          child: Padding(
            padding: EdgeInsets.all(18),
            child: Column(
              children: [
                C3Label(C3Strings.yourCurrentDhs),
                Text('–', style: TextStyle(fontSize: 40, fontWeight: FontWeight.w800)),
                SizedBox(height: 6),
                Text(C3Strings.noScoreYet, textAlign: TextAlign.center),
              ],
            ),
          ),
        ),
      ];
    }
    return [
      Card(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            children: [
              const C3Label(C3Strings.yourCurrentDhs),
              // Same band colour as the result screen, so one score never shows two colours.
              DhsGauge(score: dhs.score, size: 156, colour: bandStyle(latest.band!).$1),
              const SizedBox(height: 6),
              BandBadge(band: latest.band!),
              const SizedBox(height: 6),
              Text(
                '${C3Strings.lastAssessed}${_when(_controller.latestAt!)}',
                style: const TextStyle(color: C3Colors.text2, fontSize: 12),
              ),
              const SizedBox(height: 6),
              const ProvisionalTag(text: C3Strings.provisionalScore),
            ],
          ),
        ),
      ),
      const SizedBox(height: 8),
      FilledButton.icon(
        onPressed: () => _open(RiskAnalysisScreen(controller: _controller, profile: profile)),
        icon: const Icon(Icons.refresh),
        label: const Text(C3Strings.recalculate),
      ),
      const C3Label(C3Strings.riskFactors),
      Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Column(
            children: [
              if (profile.systolicBp != null && profile.diastolicBp != null)
                FactorStatusRow(
                  title: C3Strings.bloodPressureTitle,
                  subtitle:
                      '${profile.systolicBp!.round()}/${profile.diastolicBp!.round()} mmHg · ${C3Strings.usedByModel}',
                ),
              for (final item in dhs.items)
                FactorStatusRow(
                  title: item.label,
                  subtitle: describeAnswer(item.factor, item.value),
                  score: item.itemScore,
                ),
            ],
          ),
        ),
      ),
      const SizedBox(height: 8),
      if (latest.explanation != null)
        OutlinedButton.icon(
          onPressed: () => _open(
            RiskXaiScreen(assessment: latest, controller: _controller, profile: profile),
          ),
          icon: const Icon(Icons.auto_awesome),
          label: const Text(C3Strings.understandMyScore),
        ),
      const SizedBox(height: 8),
      Row(
        children: [
          Expanded(
            child: OutlinedButton(
              onPressed: () =>
                  _open(RiskQuestionnaireScreen(controller: _controller, initial: profile)),
              child: const Text(C3Strings.updateHealthInfoShort),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: OutlinedButton(
              onPressed: () => _open(
                RiskResultView(
                  assessment: latest,
                  isDemoData: _controller.isDemoData,
                  controller: _controller,
                  profile: profile,
                ),
              ),
              child: const Text(C3Strings.fullAssessment),
            ),
          ),
        ],
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: c3Theme(brightness: MediaQuery.platformBrightnessOf(context)),
      child: ListenableBuilder(
        listenable: _controller,
        builder: (context, _) {
          if (!_controller.isReady) {
            return ColoredBox(
              color: Theme.of(context).colorScheme.surface,
              child: Padding(
                padding: EdgeInsets.all(16),
                child: C3LoadingSkeleton(lines: 5),
              ),
            );
          }
          return ColoredBox(
            color: Theme.of(context).colorScheme.surface,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_controller.isDemoData) const DemoBanner(),
                Row(
                  children: [
                    Expanded(
                      child: Semantics(
                        header: true,
                        child: Text(
                          C3Strings.dhsName,
                          style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.w800,
                              color: Theme.of(context).colorScheme.onSurface),
                        ),
                      ),
                    ),
                    ConnectionIndicator(
                      controller: _controller,
                      onOpenSettings: () => _open(RiskSettingsScreen(controller: _controller)),
                    ),
                  ],
                ),
                if (_controller.gateway == GatewayState.offline && !_controller.isDemoData)
                  ServerDownHint(onCheckAgain: _controller.checkConnection),
                const SizedBox(height: 4),
                const Text(C3Strings.homeIntro, style: TextStyle(color: C3Colors.text2)),
                const SizedBox(height: 10),
                ..._scoreCard(),
                if (_controller.latest == null) ...[
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    onPressed: () => _open(RiskQuestionnaireScreen(controller: _controller)),
                    icon: const Icon(Icons.assignment_outlined),
                    label: const Text(C3Strings.startQuestionnaire),
                  ),
                ],
                const SizedBox(height: 8),
                TextButton.icon(
                  onPressed: () => _open(RiskHistoryScreen(controller: _controller)),
                  icon: const Icon(Icons.history),
                  label: Text('${C3Strings.history} (${_controller.history.entries.length})'),
                ),
                // Example answers and connection settings are not for app users: they are on
                // the Settings page, opened by a long-press on the connection chip.
              ],
            ),
          );
        },
      ),
    );
  }
}

/// Plain words for one answered DHS question (the server sends the raw answer).
String describeAnswer(String factor, Object value) => switch ((factor, value)) {
      ('physical_activity', final String v) => '${v[0].toUpperCase()}${v.substring(1)} activity',
      ('smoker', 0) => 'Non-smoker',
      ('smoker', _) => 'Smoker',
      ('medication_adherence', final String v) => '${v[0].toUpperCase()}${v.substring(1)}',
      ('cholesterol_level', 'borderline_high') => 'Borderline high',
      ('cholesterol_level', final String v) => '${v[0].toUpperCase()}${v.substring(1)}',
      ('kidney_disease' || 'liver_disease', 0) => 'No condition reported',
      ('kidney_disease' || 'liver_disease', _) => 'Condition reported',
      ('weight_change_kg', final num v) =>
        '${v > 0 ? '+' : ''}${v.toStringAsFixed(1)} kg in 3 months',
      _ => '$value',
    };
