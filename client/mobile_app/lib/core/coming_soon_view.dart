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
            padding: const EdgeInsets.fromLTRB(22, 6, 22, 24),
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
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Row(children: [
                  IconContainer(icon: icon, size: 48),
                  const SizedBox(width: 13),
                  Expanded(
                    child: Text(title,
                        style: GoogleFonts.inter(
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                            color: AppColors.text)),
                  ),
                  const AppBadge('Coming soon',
                      variant: AppBadgeVariant.warning, icon: Icons.schedule),
                ]),
              ),
              AppCard(
                child: Text(summary,
                    style: GoogleFonts.inter(
                        fontSize: 14, height: 1.5, color: AppColors.text)),
              ),
              AppCard(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const SectionLabel('What it will do'),
                  for (final feature in features)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Padding(
                              padding: EdgeInsets.only(top: 1),
                              child: Icon(Icons.check_circle_outline,
                                  size: 17, color: AppColors.primary),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(feature,
                                  style: GoogleFonts.inter(
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
                child: Text(
                    'This feature is still being built. Nothing is recorded or shown here yet.',
                    style: GoogleFonts.inter(
                        fontSize: 13, height: 1.45, color: AppColors.primaryDark)),
              ),
              const DisclaimerBanner(
                  'Research prototype. Outputs will be estimates and predictions, not diagnoses.'),
            ],
          ),
        ),
      );
}
