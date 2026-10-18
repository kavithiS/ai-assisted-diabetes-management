import 'package:flutter/material.dart';

import '../../core/coming_soon_view.dart';

/// Glucose forecast. The service behind it is not built yet.
class GlucoseScreen extends StatelessWidget {
  const GlucoseScreen({super.key});

  @override
  Widget build(BuildContext context) => const ComingSoonView(
        icon: Icons.water_drop_outlined,
        title: 'Glucose Forecast',
        summary:
            'Predicts how your blood glucose may change in the hours after a meal, using what you ate, your history and when you ate.',
        features: [
          'A 4-hour estimate of your glucose after a meal',
          "Uses the meal's nutrition, your history and meal timing",
          'A dietary risk score based on meal timing, carbohydrate load and your intake over the day',
          'Built on a Sri Lankan meal glycemic index reference',
        ],
      );
}
