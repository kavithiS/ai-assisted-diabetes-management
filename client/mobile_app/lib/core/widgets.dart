import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'theme.dart';

// ─── Badge ──────────────────────────────────────────────────────────────────

enum AppBadgeVariant { success, warning, danger, neutral }

class AppBadge extends StatelessWidget {
  const AppBadge(this.label, {super.key, this.variant = AppBadgeVariant.neutral, this.icon});

  final String label;
  final AppBadgeVariant variant;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = switch (variant) {
      AppBadgeVariant.success => (AppColors.successBg, AppColors.success),
      AppBadgeVariant.warning => (AppColors.warningBg, AppColors.warning),
      AppBadgeVariant.danger  => (AppColors.dangerBg,  AppColors.danger),
      AppBadgeVariant.neutral => (AppColors.primaryLight, AppColors.primaryDark),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(20)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 12, color: fg),
            const SizedBox(width: 5),
          ],
          Text(label,
              style: GoogleFonts.inter(
                  fontSize: 12, fontWeight: FontWeight.w700, color: fg)),
        ],
      ),
    );
  }
}

// ─── AI Tag ──────────────────────────────────────────────────────────────────

class AiTag extends StatelessWidget {
  const AiTag(this.label, {super.key});
  final String label;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.auto_awesome, size: 16, color: AppColors.primaryDark),
          const SizedBox(width: 5),
          Text(label,
              style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primaryDark)),
        ],
      );
}

// ─── AI Card ─────────────────────────────────────────────────────────────────

class AiCard extends StatelessWidget {
  const AiCard({super.key, required this.text, this.footer});
  final String text;
  final String? footer;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        margin: const EdgeInsets.only(bottom: 14),
        decoration: BoxDecoration(
          color: AppColors.primaryLight,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFCFEDEF)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const AiTag('AI Insight'),
          const SizedBox(height: 6),
          Text(text,
              style: GoogleFonts.inter(
                  fontSize: 13, height: 1.45, color: AppColors.text)),
          if (footer != null) ...[
            const SizedBox(height: 6),
            Text(footer!,
                style: GoogleFonts.inter(
                    fontSize: 10.5, color: AppColors.textSecondary)),
          ],
        ]),
      );
}

// ─── App Card ────────────────────────────────────────────────────────────────

class AppCard extends StatelessWidget {
  const AppCard({super.key, required this.child, this.padding, this.color});
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? color;

  @override
  Widget build(BuildContext context) => Container(
        padding: padding ?? const EdgeInsets.all(16),
        margin: const EdgeInsets.only(bottom: 14),
        decoration: appCardDecoration(color: color),
        child: child,
      );
}

// ─── Section Label ────────────────────────────────────────────────────────────

class SectionLabel extends StatelessWidget {
  const SectionLabel(this.text, {super.key, this.color});
  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(text.toUpperCase(),
            style: GoogleFonts.inter(
                fontSize: 11.5,
                fontWeight: FontWeight.w700,
                letterSpacing: .05,
                color: color ?? AppColors.textSecondary)),
      );
}

// ─── Nutrition Bar Row ────────────────────────────────────────────────────────

class NutritionBarRow extends StatelessWidget {
  const NutritionBarRow({
    super.key,
    required this.label,
    required this.value,
    required this.fraction,
    this.color,
  });

  final String label;
  final String value;
  final double fraction; // 0.0–1.0
  final Color? color;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 11),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label,
                  style: GoogleFonts.inter(
                      fontSize: 13.5, color: AppColors.text)),
              Text(value,
                  style: GoogleFonts.inter(
                      fontSize: 13.5, color: AppColors.textSecondary)),
            ],
          ),
          const SizedBox(height: 5),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: fraction.clamp(0, 1),
              minHeight: 8,
              color: color ?? AppColors.primary,
              backgroundColor: AppColors.border,
            ),
          ),
        ]),
      );
}

// ─── List Row ─────────────────────────────────────────────────────────────────

class AppListRow extends StatelessWidget {
  const AppListRow({
    super.key,
    required this.title,
    this.subtitle,
    this.leading,
    this.trailing,
    this.onTap,
  });

  final String title;
  final String? subtitle;
  final Widget? leading;
  final Widget? trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 2),
          child: Row(children: [
            if (leading != null) ...[leading!, const SizedBox(width: 11)],
            Expanded(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                  Text(title,
                      style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: AppColors.text)),
                  if (subtitle != null)
                    Text(subtitle!,
                        style: GoogleFonts.inter(
                            fontSize: 12, color: AppColors.textSecondary)),
                ])),
            if (trailing != null) trailing!,
          ]),
        ),
      );
}

// ─── Icon Container ──────────────────────────────────────────────────────────

class IconContainer extends StatelessWidget {
  const IconContainer({
    super.key,
    required this.icon,
    this.size = 34,
    this.color,
    this.bg,
  });

  final IconData icon;
  final double size;
  final Color? color;
  final Color? bg;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
            color: bg ?? AppColors.primaryLight,
            borderRadius: BorderRadius.circular(9)),
        child: Icon(icon, size: size * 0.5, color: color ?? AppColors.primary),
      );
}

// ─── Disclaimer Banner ────────────────────────────────────────────────────────

class DisclaimerBanner extends StatelessWidget {
  const DisclaimerBanner(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: AppColors.warningBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFF1DDB1)),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.warning_amber_rounded,
              size: 15, color: Color(0xFF8A6116)),
          const SizedBox(width: 8),
          Expanded(
              child: Text(text,
                  style: GoogleFonts.inter(
                      fontSize: 12,
                      height: 1.45,
                      color: const Color(0xFF8A6116)))),
        ]),
      );
}

// ─── Chip Row ─────────────────────────────────────────────────────────────────

class ChipRow extends StatelessWidget {
  const ChipRow({super.key, required this.options, required this.selected, required this.onChanged});

  final List<String> options;
  final String? selected;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final opt in options)
            GestureDetector(
              onTap: () => onChanged(opt),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 9),
                decoration: BoxDecoration(
                  color: selected == opt ? AppColors.primary : AppColors.card,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: selected == opt ? AppColors.primary : AppColors.border,
                    width: 1.5,
                  ),
                ),
                child: Text(opt,
                    style: GoogleFonts.inter(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                        color: selected == opt ? Colors.white : AppColors.text)),
              ),
            ),
        ],
      );
}
