import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../meal_history/data/meal_history_models.dart';

class HomeDashboardScreen extends StatelessWidget {
  const HomeDashboardScreen({
    super.key,
    required this.onScanMeal,
    required this.onGlucoseCheck,
    required this.onRiskCheck,
    required this.onFootCheck,
    required this.onMealHistory,
    required this.onTodaySummary,
    required this.onProfile,
    this.userName,
    this.todaySummary,
    this.now,
  });

  final VoidCallback onScanMeal;
  final VoidCallback onGlucoseCheck;
  final VoidCallback onRiskCheck;
  final VoidCallback onFootCheck;
  final VoidCallback onMealHistory;
  final VoidCallback onTodaySummary;
  final VoidCallback onProfile;
  final String? userName;
  final DailySummary? todaySummary;
  final DateTime? now;

  String get _greeting {
    final hour = (now ?? DateTime.now()).hour;
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  @override
  Widget build(BuildContext context) => SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 28),
              children: [
                Row(children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_greeting,
                            style: GoogleFonts.manrope(
                                fontSize: 12.5,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textSecondary)),
                        const SizedBox(height: 2),
                        Text(userName ?? 'Welcome',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: GoogleFonts.manrope(
                                fontSize: 24,
                                letterSpacing: -0.6,
                                fontWeight: FontWeight.w800,
                                color: AppColors.text)),
                      ],
                    ),
                  ),
                  IconButton.filledTonal(
                    onPressed: onProfile,
                    tooltip: 'Open profile',
                    icon: const Icon(Icons.person_outline_rounded, size: 20),
                  ),
                ]),
                const SizedBox(height: 18),
                Container(
                  padding: const EdgeInsets.all(19),
                  decoration: BoxDecoration(
                    color: AppColors.primaryDark,
                    borderRadius: BorderRadius.circular(26),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x24073F38),
                        blurRadius: 22,
                        offset: Offset(0, 10),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: AppColors.accent,
                            borderRadius: BorderRadius.circular(30),
                          ),
                          child: Text('TODAY',
                              style: GoogleFonts.manrope(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 1,
                                  color: AppColors.primaryDark)),
                        ),
                        const Spacer(),
                        Icon(Icons.auto_awesome,
                            size: 17, color: Colors.white.withAlpha(210)),
                      ]),
                      const SizedBox(height: 24),
                      Row(children: [
                        Expanded(
                          child: _HeroMetric(
                            label: 'HEALTH SCORE',
                            value: 'No score yet',
                            icon: Icons.favorite_outline_rounded,
                          ),
                        ),
                        Container(
                          width: 1,
                          height: 48,
                          color: Colors.white.withAlpha(35),
                        ),
                        const SizedBox(width: 18),
                        const Expanded(
                          child: _HeroMetric(
                            label: 'GLUCOSE',
                            value: 'No readings yet',
                            icon: Icons.water_drop_outlined,
                          ),
                        ),
                      ]),
                      const SizedBox(height: 18),
                      Text(
                        'Log your first meal or glucose reading to start building your daily picture.',
                        style: GoogleFonts.manrope(
                            fontSize: 11.5,
                            height: 1.4,
                            color: Colors.white.withAlpha(190)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 22),
                const _SectionHeading(
                  title: 'Quick actions',
                  subtitle: 'What would you like to do?',
                ),
                const SizedBox(height: 11),
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                  childAspectRatio: 1.55,
                  children: [
                    _QuickAction(Icons.camera_alt_outlined, 'Scan Meal',
                        'Analyse a plate', onScanMeal),
                    _QuickAction(Icons.water_drop_outlined, 'Glucose',
                        'Add a reading', onGlucoseCheck),
                    _QuickAction(Icons.shield_outlined, 'Risk profile',
                        'Review factors', onRiskCheck),
                    _QuickAction(Icons.healing_outlined, 'Foot check',
                        'Start a check', onFootCheck),
                  ],
                ),
                const SizedBox(height: 22),
                const _SectionHeading(
                  title: 'Your nutrition',
                  subtitle: 'Meals and daily totals',
                ),
                const SizedBox(height: 11),
                if (todaySummary != null) ...[
                  Container(
                    padding: const EdgeInsets.all(16),
                    margin: const EdgeInsets.only(bottom: 10),
                    decoration: appCardDecoration(),
                    child: Row(children: [
                      const IconContainer(icon: Icons.today_outlined, size: 42),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('${todaySummary!.mealCount} meals today',
                                style: Theme.of(context).textTheme.titleMedium),
                            Text(
                                todaySummary!.totals.energyKcal == null
                                    ? 'Nutrition totals need more food data'
                                    : '${todaySummary!.totals.energyKcal!.round()} estimated kcal',
                                style: const TextStyle(
                                    fontSize: 11.5,
                                    color: AppColors.textSecondary)),
                          ],
                        ),
                      ),
                    ]),
                  ),
                ],
                AppCard(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                  child: Column(children: [
                    AppListRow(
                      title: 'Meal history',
                      subtitle: 'Review everything you have logged',
                      leading: const IconContainer(
                          icon: Icons.restaurant_outlined, size: 40),
                      trailing: const Icon(Icons.arrow_forward_ios_rounded,
                          size: 14, color: AppColors.textSecondary),
                      onTap: onMealHistory,
                    ),
                    const Divider(),
                    AppListRow(
                      title: "Today's summary",
                      subtitle: 'Energy and nutrients at a glance',
                      leading: const IconContainer(
                          icon: Icons.donut_large_outlined, size: 40),
                      trailing: const Icon(Icons.arrow_forward_ios_rounded,
                          size: 14, color: AppColors.textSecondary),
                      onTap: onTodaySummary,
                    ),
                  ]),
                ),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.primaryLight,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppColors.primarySoft),
                  ),
                  child: Row(children: [
                    const IconContainer(
                      icon: Icons.auto_awesome,
                      size: 40,
                      color: AppColors.primary,
                      bg: Colors.white,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Insights are waiting',
                              style: GoogleFonts.manrope(
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w800,
                                  color: AppColors.text)),
                          const SizedBox(height: 3),
                          Text(
                            'They will appear after your meals and health data are analysed.',
                            style: GoogleFonts.manrope(
                                fontSize: 11.5,
                                height: 1.4,
                                color: AppColors.textSecondary),
                          ),
                        ],
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

class _HeroMetric extends StatelessWidget {
  const _HeroMetric(
      {required this.label, required this.value, required this.icon});
  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(icon, size: 14, color: Colors.white.withAlpha(190)),
            const SizedBox(width: 5),
            Text(label,
                style: GoogleFonts.manrope(
                    fontSize: 9.5,
                    letterSpacing: .8,
                    fontWeight: FontWeight.w700,
                    color: Colors.white.withAlpha(185))),
          ]),
          const SizedBox(height: 7),
          Text(value,
              style: GoogleFonts.manrope(
                  fontSize: 17,
                  fontWeight: FontWeight.w800,
                  color: Colors.white)),
        ],
      );
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title, required this.subtitle});
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Row(children: [
        Text(title,
            style: GoogleFonts.manrope(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: AppColors.text)),
        const Spacer(),
        Text(subtitle,
            style: GoogleFonts.manrope(
                fontSize: 10.5, color: AppColors.textSecondary)),
      ]);
}

class _QuickAction extends StatelessWidget {
  const _QuickAction(this.icon, this.label, this.subtitle, this.onTap);
  final IconData icon;
  final String label;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(19),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(19),
          child: Container(
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(19),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(children: [
              IconContainer(icon: icon, size: 39),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.manrope(
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                            color: AppColors.text)),
                    Text(subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.manrope(
                            fontSize: 9.5, color: AppColors.textSecondary)),
                  ],
                ),
              ),
            ]),
          ),
        ),
      );
}
