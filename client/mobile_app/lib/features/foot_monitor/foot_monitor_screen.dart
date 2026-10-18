import 'package:flutter/material.dart';

import '../../core/coming_soon_view.dart';

/// Foot monitoring. The service behind it is not built yet.
class FootMonitorScreen extends StatelessWidget {
  const FootMonitorScreen({super.key});

  @override
  Widget build(BuildContext context) => const ComingSoonView(
        icon: Icons.healing_outlined,
        title: 'Foot Monitoring',
        summary:
            'Take a photo of your foot to get an estimate of whether anything looks abnormal.',
        features: [
          'Photograph your foot and get an estimated abnormality class',
          'Smart alerts when something may need attention',
        ],
      );
}
