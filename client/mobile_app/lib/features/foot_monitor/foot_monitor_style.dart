import 'package:flutter/material.dart';

/// Design tokens for Foot Monitor. Same values as C1's `MealScanStyle` and `AppColors`
/// (on C1's branch); replace with `AppColors` once that theme is merged into `main`.
class FootMonitorStyle {
  const FootMonitorStyle._();

  static const Color primary = Color(0xFF087F8C);
  static const Color primaryDark = Color(0xFF05636D);
  static const Color primaryLight = Color(0xFFE6F6F7);
  static const Color background = Color(0xFFF7FAFA);
  static const Color card = Color(0xFFFFFFFF);
  static const Color text = Color(0xFF172B35);
  static const Color textSecondary = Color(0xFF667780);
  static const Color border = Color(0xFFDCE5E7);
  static const Color success = Color(0xFF2E9B62);
  static const Color successBg = Color(0xFFE9F6EF);
  static const Color warning = Color(0xFFE6A23C);
  static const Color warningBg = Color(0xFFFCF3E3);
  static const Color warningText = Color(0xFF8A6116);
  static const Color danger = Color(0xFFD9534F);
  static const Color dangerBg = Color(0xFFFBEAE9);

  static const double cardRadius = 16;
  static const double controlRadius = 12;

  static BoxDecoration cardDecoration({Color? color, Color? borderColor}) => BoxDecoration(
        color: color ?? card,
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: borderColor ?? border),
      );

  static ButtonStyle primaryButton() => FilledButton.styleFrom(
        backgroundColor: primary,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(50),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(controlRadius)),
        textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
      );

  static ButtonStyle secondaryButton() => OutlinedButton.styleFrom(
        foregroundColor: primary,
        minimumSize: const Size.fromHeight(50),
        side: const BorderSide(color: primary, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(controlRadius)),
        textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
      );

  static const TextStyle title =
      TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: text);
  static const TextStyle body = TextStyle(fontSize: 14, height: 1.5, color: text);
  static const TextStyle sectionLabel = TextStyle(
      fontSize: 11.5, fontWeight: FontWeight.w700, letterSpacing: .05, color: textSecondary);
}
