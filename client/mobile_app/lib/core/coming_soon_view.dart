import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'theme.dart';
import 'widgets.dart';

/// A screen for a feature whose service is not built yet. It shows what the feature will do,
/// and no data: the service behind it still answers 501.
class ComingSoonView extends StatelessWidget {
  const ComingSoonView({
    super.key,
    required this.icon,
    required this.title,
    required this.summary,
    required this.features,
  });

  final IconData icon;
  final String title;
  final String summary;
  final List<String> features;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 10, 20, 28),
            children: [
              if (Navigator.of(context).canPop())
                Align(
                  alignment: Alignment.centerLeft,
                  child: IconButton(
                    onPressed: () => Navigator.of(context).maybePop(),
                    icon: const Icon(Icons.arrow_back, color: AppColors.text),
                    tooltip: 'Back',
                  ),
                )
              else
                const SizedBox(height: 8),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(20),
                margin: const EdgeInsets.only(bottom: 14),
                decoration: BoxDecoration(
                  color: AppColors.primaryDark,
                  borderRadius: BorderRadius.circular(24),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Container(
                        width: 48,
                        height: 48,
                        decoration: BoxDecoration(
                          color: Colors.white.withAlpha(22),
                          borderRadius: BorderRadius.circular(15),
                        ),
                        child: Icon(icon, color: Colors.white, size: 23),
                      ),
                      const Spacer(),
                      const AppBadge('Coming soon',
                          variant: AppBadgeVariant.warning,
                          icon: Icons.schedule_rounded),
                    ]),
                    const SizedBox(height: 26),
                    Text(title,
                        style: GoogleFonts.manrope(
                            fontSize: 25,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -.6,
                            color: Colors.white)),
                    const SizedBox(height: 8),
                    Text(summary,
                        style: GoogleFonts.manrope(
                            fontSize: 13,
                            height: 1.5,
                            color: Colors.white.withAlpha(190))),
                  ],
                ),
              ),
              AppCard(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionLabel('What it will do'),
                      for (final feature in features)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  width: 24,
                                  height: 24,
                                  decoration: BoxDecoration(
                                    color: AppColors.primaryLight,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: const Icon(Icons.check_rounded,
                                      size: 14, color: AppColors.primary),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(feature,
                                      style: GoogleFonts.manrope(
                                          fontSize: 13.5,
                                          height: 1.45,
                                          color: AppColors.text)),
                                ),
                              ]),
                        ),
                    ]),
              ),
              AppCard(
                color: AppColors.primaryLight,
                child: Row(children: [
                  const Icon(Icons.lock_outline_rounded,
                      size: 19, color: AppColors.primary),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                        'Nothing is recorded here while this feature is being built.',
                        style: GoogleFonts.manrope(
                            fontSize: 12.5,
                            height: 1.45,
                            color: AppColors.primaryDark)),
                  ),
                ]),
              ),
              const DisclaimerBanner(
                  'Research prototype. Outputs will be estimates and predictions, not diagnoses.'),
            ],
          ),
        ),
      );
}
