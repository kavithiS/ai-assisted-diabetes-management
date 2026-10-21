import 'package:flutter/material.dart';

import 'c3_strings.dart';
import 'c3_theme.dart';
import 'risk_profile_screen.dart';

/// C3-only entry point: opens straight on the Risk Profile feature.
///
/// The full app (`lib/main.dart`, shared) stays the normal way to run. This one is a
/// fallback for the C3 demo and for automated browser checks:
///   flutter run -d chrome -t lib/features/risk_profile/c3_standalone.dart
void main() => runApp(const C3StandaloneApp());

class C3StandaloneApp extends StatelessWidget {
  const C3StandaloneApp({super.key});

  // Uses the C3 theme in light and dark mode so the top bar matches the screens.
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: C3Strings.appName,
        theme: c3Theme(),
        darkTheme: c3Theme(brightness: Brightness.dark),
        home: Scaffold(
          appBar: AppBar(title: const Text(C3Strings.appName)),
          body: const RiskProfileScreen(),
        ),
      );
}
