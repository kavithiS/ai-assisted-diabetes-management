// UNVERIFIED: written without the Flutter SDK; run `flutter analyze` before use.

import 'package:flutter/material.dart';

/// Seven-step questionnaire that builds a RiskProfile.
class RiskQuestionnaireScreen extends StatelessWidget {
  const RiskQuestionnaireScreen({super.key});

  // TODO(c3): steps 1 age + sex, 2 height + weight (BMI), 3 blood pressure,
  // 4 pulse, 5 optional glucose, 6 family history, 7 medical history; then call
  // RiskRepository.assess and open RiskResultScreen.

  @override
  Widget build(BuildContext context) {
    return const Center(child: Text('Risk questionnaire (C3): coming soon'));
  }
}
