import 'package:flutter/material.dart';

import 'core/theme.dart';
import 'features/dashboard/dashboard_screen.dart';
import 'features/foot_monitor/foot_monitor_screen.dart';
import 'features/glucose/glucose_screen.dart';
import 'features/meal_scan/meal_scan_screen.dart';
import 'features/risk_profile/risk_profile_screen.dart';

void main() {
  runApp(const DiaCareApp());
}

class DiaCareApp extends StatelessWidget {
  const DiaCareApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'DiaCare AI',
      theme: buildAppTheme(),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  static const List<Widget> _screens = [
    MealScanScreen(),
    GlucoseScreen(),
    RiskProfileScreen(),
    FootMonitorScreen(),
    DashboardScreen(),
  ];

  static const List<NavigationDestination> _destinations = [
    NavigationDestination(icon: Icon(Icons.camera_alt_outlined), label: 'Meal Scan'),
    NavigationDestination(icon: Icon(Icons.show_chart), label: 'Glucose'),
    NavigationDestination(icon: Icon(Icons.assignment_outlined), label: 'Risk Profile'),
    NavigationDestination(icon: Icon(Icons.healing), label: 'Foot Monitor'),
    NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Dashboard'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_destinations[_index].label)),
      body: _screens[_index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (index) => setState(() => _index = index),
        destinations: _destinations,
      ),
    );
  }
}
