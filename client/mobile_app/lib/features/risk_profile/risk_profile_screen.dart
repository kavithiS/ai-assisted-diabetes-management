import 'package:flutter/material.dart';

import 'c3_strings.dart';
import 'domain/risk_presets.dart';
import 'presentation/risk_controller.dart';
import 'presentation/risk_history_screen.dart';
import 'presentation/risk_questionnaire_screen.dart';
import 'presentation/risk_result_screen.dart';
import 'presentation/risk_settings_screen.dart';
import 'presentation/widgets/risk_widgets.dart';

/// Risk Profile (C3) tab. Entry point imported by `lib/main.dart` (shared), so the class
/// name and path stay the same.
///
/// The feature is split into `domain/` (contract models, presets, input ranges),
/// `data/` (repository, live API, mock, settings, history) and `presentation/`
/// (controller, questionnaire, result, history and settings screens).
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

  void _open(Widget screen) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => screen));

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

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _controller,
      builder: (context, _) {
        if (!_controller.isReady) return const Center(child: CircularProgressIndicator());
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (_controller.isDemoData) const DemoBanner(),
            Row(
              children: [
                Expanded(
                  child: Semantics(
                    header: true,
                    child: Text(
                      C3Strings.homeTitle,
                      style: Theme.of(context).textTheme.titleLarge,
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
            const SizedBox(height: 8),
            const Text(C3Strings.homeIntro),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => _open(RiskQuestionnaireScreen(controller: _controller)),
              icon: const Icon(Icons.assignment_outlined),
              label: const Text(C3Strings.startQuestionnaire),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => _open(RiskHistoryScreen(controller: _controller)),
              icon: const Icon(Icons.history),
              label: Text('${C3Strings.history} (${_controller.history.entries.length})'),
            ),
            const SectionTitle(C3Strings.presetsTitle),
            for (final preset in riskPresets)
              Card(
                child: ListTile(
                  title: Text(preset.label),
                  subtitle: Text(preset.description),
                  trailing: const Icon(Icons.play_arrow),
                  onTap: () => _open(
                    RiskResultScreen(controller: _controller, profile: preset.profile),
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
            Text(C3Strings.settingsHint, style: Theme.of(context).textTheme.bodySmall),
          ],
        );
      },
    );
  }
}
