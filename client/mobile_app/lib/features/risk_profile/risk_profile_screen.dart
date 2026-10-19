import 'package:flutter/material.dart';

import 'c3_strings.dart';
import 'c3_theme.dart';
import 'domain/risk_presets.dart';
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
  String? _warmUpMessage;
  bool _warming = false;

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

  void _open(Widget screen) => Navigator.of(context).push(c3Route<void>(screen));

  Future<void> _warmUp() async {
    setState(() {
      _warming = true;
      _warmUpMessage = null;
    });
    String message;
    try {
      final took = await _controller.warmUp();
      message = '${C3Strings.warmUpDone} (${(took.inMilliseconds / 1000).toStringAsFixed(1)} s)';
    } on Object catch (error) {
      message = '$error';
    }
    if (!mounted) return;
    setState(() {
      _warming = false;
      _warmUpMessage = message;
    });
  }

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
              Semantics(
                label: '${C3Strings.dhsName} ${dhs.score.round()} out of 100',
                excludeSemantics: true,
                child: Text.rich(
                  TextSpan(
                    text: dhs.score.round().toString(),
                    style: const TextStyle(
                        fontSize: 44, fontWeight: FontWeight.w800, color: C3Colors.text),
                    children: const [
                      TextSpan(
                          text: ' /100', style: TextStyle(fontSize: 16, color: C3Colors.text2)),
                    ],
                  ),
                ),
              ),
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
      data: c3Theme(),
      child: ListenableBuilder(
        listenable: _controller,
        builder: (context, _) {
          if (!_controller.isReady) return const Center(child: CircularProgressIndicator());
          return ColoredBox(
            color: C3Colors.background,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_controller.isDemoData) const DemoBanner(),
                Row(
                  children: [
                    Expanded(
                      child: Semantics(
                        header: true,
                        child: const Text(
                          C3Strings.dhsName,
                          style: TextStyle(
                              fontSize: 20, fontWeight: FontWeight.w800, color: C3Colors.text),
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
                const C3Label(C3Strings.presetsTitle),
                for (final preset in riskPresets)
                  Card(
                    child: ListTile(
                      title:
                          Text(preset.label, style: const TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Text(preset.description),
                      trailing: const Icon(Icons.play_arrow, color: C3Colors.primary),
                      onTap: () => _open(
                        RiskAnalysisScreen(controller: _controller, profile: preset.profile),
                      ),
                    ),
                  ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: _warming ? null : _warmUp,
                  icon: const Icon(Icons.local_fire_department_outlined),
                  label: const Text(C3Strings.warmUp),
                ),
                if (_warming) const LinearProgressIndicator(),
                if (_warmUpMessage != null)
                  Padding(padding: const EdgeInsets.only(top: 8), child: Text(_warmUpMessage!)),
                const SizedBox(height: 16),
                const Text(
                  C3Strings.settingsHint,
                  style: TextStyle(fontSize: 11.5, color: C3Colors.text2),
                ),
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
