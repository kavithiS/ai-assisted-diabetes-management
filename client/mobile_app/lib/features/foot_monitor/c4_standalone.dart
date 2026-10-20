import 'package:flutter/material.dart';

import '../../core/theme.dart';
import 'foot_monitor_screen.dart';

/// C4-only entry point: opens straight on the Foot Monitor feature.
///
/// The full app (`lib/main.dart`, shared) stays the normal way to run. This one is for the
/// C4 demo and for testing the foot screen on its own:
///   flutter run -t lib/features/foot_monitor/c4_standalone.dart
void main() => runApp(const C4StandaloneApp());

class C4StandaloneApp extends StatelessWidget {
  const C4StandaloneApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'DiaCare AI - Foot Monitor (C4)',
        theme: buildAppTheme(),
        debugShowCheckedModeBanner: false,
        home: const FootMonitorScreen(),
      );
}
