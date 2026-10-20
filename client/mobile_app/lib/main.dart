import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'core/theme.dart';
import 'features/auth/data/account_api.dart';
import 'features/auth/data/auth_api.dart';
import 'features/auth/data/auth_tokens.dart';
import 'features/foot_monitor/foot_monitor_screen.dart';
import 'features/glucose/glucose_tabs.dart';
import 'features/home/home_dashboard_screen.dart';
import 'features/meal_history/meal_history_screen.dart';
import 'features/meal_history/data/meal_history_api.dart';
import 'features/meal_history/data/meal_history_models.dart';
import 'features/meal_history/today_summary_screen.dart';
import 'features/meal_scan/meal_scan_screen.dart';
import 'features/onboarding/splash_screen.dart';
import 'features/profile/profile_screen.dart';
import 'features/risk_profile/risk_profile_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  GoogleFonts.config.allowRuntimeFetching = false;
  await AuthSession.instance.restore();
  runApp(DiaCareApp(startSignedIn: AuthSession.instance.isSignedIn));
}

class DiaCareApp extends StatelessWidget {
  const DiaCareApp({
    super.key,
    this.startSignedIn = false,
    this.mealImagePicker,
  });

  /// True when a saved login was found, so the app opens on the home screen.
  final bool startSignedIn;
  final MealImagePicker? mealImagePicker;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'DiaCare AI',
      theme: buildAppTheme(),
      debugShowCheckedModeBanner: false,
      initialRoute: startSignedIn ? '/home' : '/',
      routes: {
        '/': (_) => const SplashScreen(),
        '/home': (_) => HomeShell(mealImagePicker: mealImagePicker),
      },
    );
  }
}

/// 5-tab shell matching the prototype navigation.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key, this.accountApi, this.mealImagePicker});

  final AccountApi? accountApi;
  final MealImagePicker? mealImagePicker;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  int _mealScanVersion = 0;
  UserProfile? _user;
  DailySummary? _today;

  void _setIndex(int i) {
    setState(() => _index = i);
    if (i == 0 || i == 2) _loadToday();
  }

  void _openMealScan() {
    setState(() {
      _index = 1;
      _mealScanVersion++;
    });
  }

  @override
  void initState() {
    super.initState();
    _loadUser();
    _loadToday();
  }

  Future<void> _loadToday() async {
    try {
      final now = DateTime.now();
      final summary = await MealHistoryApi().dailySummary(
        now,
        utcOffsetMinutes: now.timeZoneOffset.inMinutes,
      );
      if (mounted) setState(() => _today = summary);
    } catch (_) {
      // The dashboard remains usable while the meal service is offline.
    }
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

  void _open(Widget screen) => Navigator.of(context)
      .push(MaterialPageRoute<void>(builder: (_) => screen));

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
            userName: _user?.greetingName,
            todaySummary: _today,
            onScanMeal: _openMealScan,
            onGlucoseCheck: () => _open(Scaffold(
              appBar: AppBar(title: const Text('Glucose')),
              body: const GlucoseTabs(),
            )),
            onRiskCheck: () => _open(const RiskProfileScreen()),
            onFootCheck: () => _open(const FootMonitorScreen()),
            onMealHistory: () => _open(const MealHistoryScreen()),
            onTodaySummary: () => _open(const TodaySummaryScreen()),
            onProfile: () => _setIndex(4),
          ),
          MealScanScreen(
            key: ValueKey(_mealScanVersion),
            pickImage: widget.mealImagePicker,
          ),
          _InsightsTab(summary: _today),
          const FootMonitorScreen(),
          ProfileScreen(
            user: _user,
            api: widget.accountApi,
            onProfileUpdated: (user) => setState(() => _user = user),
            onMealHistory: () => _open(const MealHistoryScreen()),
            onTodaySummary: () => _open(const TodaySummaryScreen()),
          ),
        ],
      );

  Widget _buildNav() => Container(
        decoration: BoxDecoration(
          color: AppColors.card,
          border: const Border(top: BorderSide(color: AppColors.border)),
          boxShadow: const [
            BoxShadow(
              color: Color(0x0A14251F),
              blurRadius: 16,
              offset: Offset(0, -4),
            ),
          ],
        ),
        child: SafeArea(
          top: false,
          child: SizedBox(
            height: 70,
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
                    onTap: _openMealScan),
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
        borderRadius: BorderRadius.circular(16),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
          decoration: BoxDecoration(
            color: active ? AppColors.primaryLight : Colors.transparent,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(active ? activeIcon : icon,
                  size: 19,
                  color: active ? AppColors.primary : AppColors.textSecondary),
              const SizedBox(height: 3),
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
  const _InsightsTab({this.summary});

  final DailySummary? summary;

  @override
  Widget build(BuildContext context) => SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(18, 16, 18, 28),
              children: [
                Text('Health Insights',
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 5),
                const Text(
                  'A single view of your estimated trends and patterns.',
                  style: TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 18),
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: AppColors.primaryDark,
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(children: [
                        const Icon(Icons.insights_rounded,
                            color: Colors.white, size: 20),
                        const Spacer(),
                        _StatusPill(summary != null && summary!.mealCount > 0
                            ? 'MEALS LOGGED'
                            : 'AWAITING DATA'),
                      ]),
                      const SizedBox(height: 30),
                      Text(
                          summary != null && summary!.mealCount > 0
                              ? 'Your day is taking shape'
                              : 'Your trends will live here',
                          style: Theme.of(context)
                              .textTheme
                              .titleLarge
                              ?.copyWith(color: Colors.white)),
                      const SizedBox(height: 7),
                      Text(
                        summary != null && summary!.mealCount > 0
                            ? 'Your saved meals are linked below. Glucose and risk patterns need their own analysis data.'
                            : 'Log meals and readings to unlock estimated glucose, nutrition and risk patterns.',
                        style: TextStyle(
                            fontSize: 12.5,
                            height: 1.45,
                            color: Colors.white.withAlpha(205)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                if (summary != null) ...[
                  Container(
                    padding: const EdgeInsets.all(16),
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: appCardDecoration(),
                    child: Row(children: [
                      const Icon(Icons.restaurant_outlined,
                          color: AppColors.primary),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          '${summary!.mealCount} meals logged today'
                          '${summary!.totals.energyKcal == null ? '' : ' · ${summary!.totals.energyKcal!.round()} estimated kcal'}',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ),
                    ]),
                  ),
                ],
                const Row(children: [
                  Expanded(
                    child: _InsightPreview(
                      icon: Icons.water_drop_outlined,
                      title: 'Glucose',
                      caption: '4-hour prediction',
                    ),
                  ),
                  SizedBox(width: 10),
                  Expanded(
                    child: _InsightPreview(
                      icon: Icons.restaurant_outlined,
                      title: 'Nutrition',
                      caption: 'Daily patterns',
                    ),
                  ),
                ]),
                const SizedBox(height: 10),
                const _InsightPreview(
                  icon: Icons.shield_outlined,
                  title: 'Risk profile & explanations',
                  caption:
                      'Estimated risk bands and contributing factors will appear after analysis.',
                  wide: true,
                ),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.warningBg,
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: const Row(children: [
                    Icon(Icons.info_outline,
                        size: 18, color: Color(0xFF8A6116)),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Research prototype. Outputs are estimates and predictions, not diagnoses.',
                        style: TextStyle(
                            fontSize: 11.5,
                            height: 1.4,
                            color: Color(0xFF8A6116)),
                      ),
                    ),
                  ]),
                ),
              ],
            ),
          ),
        ),
      );
}

class _StatusPill extends StatelessWidget {
  const _StatusPill(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
          color: Colors.white.withAlpha(25),
          borderRadius: BorderRadius.circular(30),
        ),
        child: Text(text,
            style: const TextStyle(
                color: Colors.white,
                fontSize: 9,
                letterSpacing: .8,
                fontWeight: FontWeight.w800)),
      );
}

class _InsightPreview extends StatelessWidget {
  const _InsightPreview({
    required this.icon,
    required this.title,
    required this.caption,
    this.wide = false,
  });
  final IconData icon;
  final String title;
  final String caption;
  final bool wide;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.border),
        ),
        child: wide
            ? Row(children: [
                _icon(),
                const SizedBox(width: 12),
                Expanded(child: _copy()),
                const Icon(Icons.lock_outline,
                    size: 16, color: AppColors.textSecondary),
              ])
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [_icon(), const SizedBox(height: 14), _copy()],
              ),
      );

  Widget _icon() => Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: AppColors.primaryLight,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, size: 19, color: AppColors.primary),
      );

  Widget _copy() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  color: AppColors.text)),
          const SizedBox(height: 3),
          Text(caption,
              style: const TextStyle(
                  fontSize: 10.5,
                  height: 1.35,
                  color: AppColors.textSecondary)),
        ],
      );
}
