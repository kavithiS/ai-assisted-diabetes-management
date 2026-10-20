import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';

class HomeDashboardScreen extends StatelessWidget {
  const HomeDashboardScreen({
    super.key,
    required this.onScanMeal,
    required this.onGlucoseCheck,
    required this.onRiskCheck,
    required this.onFootCheck,
    required this.onMealHistory,
    required this.onTodaySummary,
    this.userName,
    this.now,
  });

  final VoidCallback onScanMeal;
  final VoidCallback onGlucoseCheck;
  final VoidCallback onRiskCheck;
  final VoidCallback onFootCheck;
  final VoidCallback onMealHistory;
  final VoidCallback onTodaySummary;

  /// The signed-in patient's name (or e-mail); `null` until it has loaded.
  final String? userName;

  /// The current time, for the greeting. Tests pass a fixed value.
  final DateTime? now;

  String get _greeting {
    final hour = (now ?? DateTime.now()).hour;
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  @override
  Widget build(BuildContext context) => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: _buildList(),
        ),
      );

  Widget _buildList() => ListView(
        padding: const EdgeInsets.fromLTRB(22, 6, 22, 24),
        children: [
          // Greeting + Bell
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_greeting,
                            style: GoogleFonts.inter(
                                fontSize: 13.5, color: AppColors.textSecondary)),
                        Text(userName ?? 'Welcome',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: GoogleFonts.inter(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                                color: AppColors.text)),
                      ]),
                ),
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppColors.card,
                    borderRadius: BorderRadius.circular(11),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: const Icon(Icons.notifications_none,
                      size: 17, color: AppColors.text),
                ),
              ],
            ),
          ),

          // DHS Card
          Container(
            padding: const EdgeInsets.all(16),
            margin: const EdgeInsets.only(bottom: 14),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.primary, AppColors.primaryDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(children: [
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                      color: Colors.white.withAlpha(90), width: 4),
                ),
                child: Center(
                  child: Text('–',
                      style: GoogleFonts.inter(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          color: Colors.white)),
                ),
              ),
              const SizedBox(width: 16),
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('DIABETIC HEALTH SCORE',
                    style: GoogleFonts.inter(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        color: Colors.white.withAlpha(220))),
                const SizedBox(height: 2),
                Text('No score yet',
                    style: GoogleFonts.inter(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: Colors.white)),
              ]),
            ]),
          ),

          // Glucose Card
          Container(
            padding: const EdgeInsets.all(16),
            margin: const EdgeInsets.only(bottom: 14),
            decoration: appCardDecoration(),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('CURRENT GLUCOSE',
                      style: GoogleFonts.inter(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w700,
                          letterSpacing: .05,
                          color: AppColors.textSecondary)),
                  const SizedBox(height: 4),
                  Text('No readings yet',
                      style: GoogleFonts.inter(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: AppColors.text)),
                ]),
              ],
            ),
          ),

          // Quick Action Grid
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 11,
            mainAxisSpacing: 11,
            childAspectRatio: 1.2,
            children: [
              _QuickAction(
                  icon: Icons.camera_alt_outlined,
                  label: 'Scan Meal',
                  onTap: onScanMeal),
              _QuickAction(
                  icon: Icons.water_drop_outlined,
                  label: 'Glucose Check',
                  onTap: onGlucoseCheck),
              _QuickAction(
                  icon: Icons.shield_outlined,
                  label: 'Risk Check',
                  onTap: onRiskCheck),
              _QuickAction(
                  icon: Icons.healing_outlined,
                  label: 'Foot Check',
                  onTap: onFootCheck),
            ],
          ),
          const SizedBox(height: 14),

          // Meal log, saved to the patient's own account
          AppCard(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
            child: Column(children: [
              AppListRow(
                title: 'Meal history',
                subtitle: 'Meals you have logged',
                leading: const IconContainer(icon: Icons.restaurant_outlined),
                trailing: const Icon(Icons.chevron_right,
                    color: AppColors.textSecondary),
                onTap: onMealHistory,
              ),
              const Divider(height: 1, color: AppColors.border),
              AppListRow(
                title: "Today's summary",
                subtitle: 'Energy and nutrients so far today',
                leading: const IconContainer(icon: Icons.today_outlined),
                trailing: const Icon(Icons.chevron_right,
                    color: AppColors.textSecondary),
                onTap: onTodaySummary,
              ),
            ]),
          ),

          // Insights need real data, so none are shown yet.
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.primaryLight,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFCFEDEF)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const AiTag('AI Insight'),
                const SizedBox(height: 6),
                Text(
                  'No insights yet. They will appear here once your meals and health data have been analysed.',
                  style: GoogleFonts.inter(
                      fontSize: 13, height: 1.45, color: AppColors.text),
                ),
              ],
            ),
          ),
        ],
      );
}

class _QuickAction extends StatelessWidget {
  const _QuickAction(
      {required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.border),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF172B35).withAlpha(13),
                blurRadius: 2,
                offset: const Offset(0, 1),
              )
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 23, color: AppColors.primary),
              const SizedBox(height: 7),
              Text(label,
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: AppColors.text)),
            ],
          ),
        ),
      );
}
