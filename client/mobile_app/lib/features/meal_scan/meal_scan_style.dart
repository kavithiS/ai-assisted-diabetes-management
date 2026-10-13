import 'package:flutter/material.dart';

/// Design tokens from the C1 prototype (SKILL.md section 10), used only by Meal Scan.
class MealScanStyle {
  const MealScanStyle._();

  static const Color primary = Color(0xFF087F8C);
  static const Color background = Color(0xFFF7FAFA);
  static const Color card = Color(0xFFFFFFFF);
  static const Color text = Color(0xFF172B35);
  static const Color textSecondary = Color(0xFF667780);
  static const Color border = Color(0xFFDCE5E7);
  static const Color success = Color(0xFF2E9B62);
  static const Color warning = Color(0xFFE6A23C);
  static const Color danger = Color(0xFFD9534F);

  /// [warning] at about 12 % opacity, for banner backgrounds.
  static const Color warningTint = Color(0x1FE6A23C);

  static const double cardRadius = 16;
  static const double controlRadius = 12;

  static BoxDecoration cardDecoration() => BoxDecoration(
        color: card,
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: border),
      );

  static ButtonStyle primaryButton() => FilledButton.styleFrom(
        backgroundColor: primary,
        minimumSize: const Size.fromHeight(48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(controlRadius)),
      );

  static ButtonStyle secondaryButton() => OutlinedButton.styleFrom(
        foregroundColor: primary,
        minimumSize: const Size.fromHeight(48),
        side: const BorderSide(color: border),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(controlRadius)),
      );
}
