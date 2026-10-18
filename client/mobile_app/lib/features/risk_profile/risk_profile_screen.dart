import 'package:flutter/material.dart';

import '../../core/coming_soon_view.dart';

/// Risk profile and Diabetic Health Score. The service behind it is not built yet.
class RiskProfileScreen extends StatelessWidget {
  const RiskProfileScreen({super.key});

  @override
  Widget build(BuildContext context) => const ComingSoonView(
        icon: Icons.shield_outlined,
        title: 'Risk Profile',
        summary:
            'Estimates your diabetes-related risk from your lifestyle and health information as well as your food, and explains why.',
        features: [
          'Looks at physical activity, smoking, medication, blood pressure, cholesterol, kidney and liver conditions, and weight changes',
          'Combines these with your food and glucose results',
          'Explains each estimate so you can see what influenced it (SHAP and LIME)',
          'A Diabetic Health Score that changes as your habits change',
        ],
      );
}
