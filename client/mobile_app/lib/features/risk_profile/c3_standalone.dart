import 'package:flutter/material.dart';

import '../../core/theme.dart';
import 'risk_profile_screen.dart';

/// C3-only entry point: opens straight on the Risk Profile feature.
///
/// The full app (`lib/main.dart`, shared) stays the normal way to run. This one is a
/// fallback for the C3 demo and for automated browser checks:
///   flutter run -d chrome -t lib/features/risk_profile/c3_standalone.dart
void main() => runApp(const C3StandaloneApp());

class C3StandaloneApp extends StatelessWidget {
  const C3StandaloneApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'DiaCare AI - Risk Profile (C3)',
        theme: buildAppTheme(),
        home: Scaffold(
          appBar: AppBar(title: const Text('Risk Profile')),
          body: const RiskProfileScreen(),
        ),
      );
}
