import 'package:flutter/material.dart';

/// Risk Profile (C3) tab. Entry point imported by `lib/main.dart` (shared), so the class
/// name and path stay the same.
///
/// The feature is split into `domain/` (contract models), `data/` (repository, live API,
/// mock, history) and `presentation/` (questionnaire, result, history screens).
class RiskProfileScreen extends StatelessWidget {
  const RiskProfileScreen({super.key});

  // TODO(c3): open RiskQuestionnaireScreen, with a link to RiskHistoryScreen.

  @override
  Widget build(BuildContext context) {
    return const Center(child: Text('Risk Profile — placeholder (C3)'));
  }
}
