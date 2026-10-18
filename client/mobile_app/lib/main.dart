import 'package:flutter/material.dart';

import 'core/theme.dart';
import 'features/auth/data/account_api.dart';
import 'features/auth/data/auth_api.dart';
import 'features/auth/data/auth_tokens.dart';
import 'features/foot_monitor/foot_monitor_screen.dart';
import 'features/glucose/glucose_screen.dart';
import 'features/home/home_dashboard_screen.dart';
import 'features/meal_history/meal_history_screen.dart';
import 'features/meal_history/today_summary_screen.dart';
import 'features/meal_scan/meal_scan_screen.dart';
import 'features/onboarding/splash_screen.dart';
import 'features/profile/profile_screen.dart';
import 'features/risk_profile/risk_profile_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AuthSession.instance.restore();
  runApp(DiaCareApp(startSignedIn: AuthSession.instance.isSignedIn));
}

class DiaCareApp extends StatelessWidget {
  const DiaCareApp({super.key, this.startSignedIn = false});

  /// True when a saved login was found, so the app opens on the home screen.
  final bool startSignedIn;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'DiaCare AI',
      theme: buildAppTheme(),
      debugShowCheckedModeBanner: false,
      initialRoute: startSignedIn ? '/home' : '/',
      routes: {
        '/': (_) => const SplashScreen(),
        '/home': (_) => const HomeShell(),
      },
    );
  }
}

/// 5-tab shell matching the prototype navigation.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key, this.accountApi});

  final AccountApi? accountApi;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  UserProfile? _user;

  void _setIndex(int i) => setState(() => _index = i);

  @override
  void initState() {
    super.initState();
    _loadUser();
  }

  /// Asks the gateway who is signed in. This also proves the saved login is still valid.
  Future<void> _loadUser() async {
    try {
      final user = await (widget.accountApi ?? AccountApi()).me();
      if (mounted) setState(() => _user = user);
    } on AuthApiException catch (e) {
      if (e.code == 'UNAUTHORIZED') {
        await AuthSession.instance.signOut();
        if (mounted) {
          Navigator.of(context).pushNamedAndRemoveUntil('/', (_) => false);
        }
      }
      // Any other problem (offline, slow server): keep the screen, greet without a name.
    }
  }

  void _open(Widget screen) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => screen));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _buildBody(),
      bottomNavigationBar: _buildNav(),
    );
  }

  Widget _buildBody() => IndexedStack(
        index: _index,
        children: [
          HomeDashboardScreen(
            userName: _user?.label,
            onScanMeal: () => _setIndex(1),
            onGlucoseCheck: () => _open(const GlucoseScreen()),
            onRiskCheck: () => _open(const RiskProfileScreen()),
            onFootCheck: () => _open(const FootMonitorScreen()),
            onMealHistory: () => _open(const MealHistoryScreen()),
            onTodaySummary: () => _open(const TodaySummaryScreen()),
          ),
          const MealScanScreen(),
          const _InsightsTab(),
          const FootMonitorScreen(),
          ProfileScreen(user: _user, api: widget.accountApi),
        ],
      );

  Widget _buildNav() => Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(top: BorderSide(color: AppColors.border)),
        ),
        child: SafeArea(
          top: false,
          child: SizedBox(
            height: 62,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _NavItem(
                    icon: Icons.home_outlined,
                    activeIcon: Icons.home,
                    label: 'Home',
                    active: _index == 0,
                    onTap: () => _setIndex(0)),
                _NavItem(
                    icon: Icons.camera_alt_outlined,
                    activeIcon: Icons.camera_alt,
                    label: 'Meals',
                    active: _index == 1,
                    onTap: () => _setIndex(1)),
                _NavItem(
                    icon: Icons.show_chart_outlined,
                    activeIcon: Icons.show_chart,
                    label: 'Insights',
                    active: _index == 2,
                    onTap: () => _setIndex(2)),
                _NavItem(
                    icon: Icons.healing_outlined,
                    activeIcon: Icons.healing,
                    label: 'Foot',
                    active: _index == 3,
                    onTap: () => _setIndex(3)),
                _NavItem(
                    icon: Icons.person_outline,
                    activeIcon: Icons.person,
                    label: 'Profile',
                    active: _index == 4,
                    onTap: () => _setIndex(4)),
              ],
            ),
          ),
        ),
      );
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
    required this.active,
    required this.onTap,
  });
  final IconData icon;
  final IconData activeIcon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(active ? activeIcon : icon,
                  size: 19,
                  color: active ? AppColors.primary : AppColors.textSecondary),
              const SizedBox(height: 4),
              Text(label,
                  style: TextStyle(
                      fontSize: 10.5,
                      fontWeight: FontWeight.w600,
                      color: active
                          ? AppColors.primary
                          : AppColors.textSecondary)),
            ],
          ),
        ),
      );
}

class _InsightsTab extends StatelessWidget {
  const _InsightsTab();

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        body: Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.show_chart, size: 48, color: AppColors.primary),
            const SizedBox(height: 12),
            Text('Health Insights',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: AppColors.text)),
            const SizedBox(height: 6),
            Text('Coming in a future release.',
                style: TextStyle(color: AppColors.textSecondary)),
          ]),
        ),
      );
}
