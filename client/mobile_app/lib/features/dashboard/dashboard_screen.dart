import 'package:flutter/material.dart';

import '../../core/coming_soon_view.dart';

/// Health analytics dashboard. The service behind it is not built yet.
class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) => const ComingSoonView(
        icon: Icons.insights_outlined,
        title: 'Health Dashboard',
        summary: 'See how your health is changing over time, all in one place.',
        features: [
          'A real-time health analytics dashboard',
          'Trend charts that show how your numbers change over time',
          'Context-aware notifications and smart alerts',
          'Predictive alerts based on your behaviour and clinical patterns',
        ],
      );
}
