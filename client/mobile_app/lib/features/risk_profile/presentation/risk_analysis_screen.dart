import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../c3_theme.dart';
import '../data/risk_api.dart';
import '../domain/risk_profile.dart';
import 'risk_controller.dart';
import 'risk_result_screen.dart';
import 'widgets/c3_widgets.dart';
import 'widgets/risk_widgets.dart';

/// "Analyzing Your Risk" (prototype Module 3): one real call to C3 through the gateway.
/// The list shows what the engine looks at; every row turns into a tick together when
/// the server has answered (no fake step timing). Then the result replaces this screen.
class RiskAnalysisScreen extends StatefulWidget {
  const RiskAnalysisScreen({super.key, required this.controller, required this.profile});

  final RiskController controller;
  final RiskProfile profile;

  static const steps = [C3Strings.analysisStepFactors, C3Strings.analysisStepScore];

  @override
  State<RiskAnalysisScreen> createState() => _RiskAnalysisScreenState();
}

class _RiskAnalysisScreenState extends State<RiskAnalysisScreen> {
  Object? _error;

  @override
  void initState() {
    super.initState();
    _run();
  }

  Future<void> _run() async {
    setState(() => _error = null);
    try {
      final assessment = await widget.controller.assess(widget.profile);
      if (!mounted) return;
      await Navigator.of(context).pushReplacement(
        c3Route<void>(
          RiskResultView(
            assessment: assessment,
            isDemoData: widget.controller.isDemoData,
            controller: widget.controller,
            profile: widget.profile,
          ),
        ),
      );
    } on Object catch (error) {
      if (mounted) setState(() => _error = error);
    }
  }

  bool get _serverDown =>
      _error is RiskApiException &&
      ((_error! as RiskApiException).kind == RiskApiErrorKind.network ||
          (_error! as RiskApiException).kind == RiskApiErrorKind.gateway);

  @override
  Widget build(BuildContext context) {
    final failed = _error != null;
    return Scaffold(
      appBar: AppBar(title: const Text(C3Strings.analyzingTitle)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Center(
            child: Container(
              width: 72,
              height: 72,
              decoration: const BoxDecoration(color: C3Colors.primaryLight, shape: BoxShape.circle),
              child: failed
                  ? const Icon(Icons.cloud_off_outlined, color: C3Colors.danger, size: 34)
                  : const Icon(Icons.favorite_outline, color: C3Colors.primary, size: 34),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            failed ? C3Strings.errorTitle : C3Strings.analyzing,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          const Text(
            C3Strings.analyzingSub,
            textAlign: TextAlign.center,
            style: TextStyle(color: C3Colors.text2, fontSize: 12.5),
          ),
          const SizedBox(height: 18),
          if (failed) ...[
            const Text(C3Strings.connectionFailed),
            if (_serverDown) ServerDownHint(onCheckAgain: _run),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _run,
              icon: const Icon(Icons.refresh),
              label: const Text(C3Strings.retry),
            ),
          ] else
            const C3LoadingSkeleton(lines: 4),
        ],
      ),
    );
  }
}
