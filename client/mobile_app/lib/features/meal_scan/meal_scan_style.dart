import 'package:flutter/material.dart';

/// Design tokens from the C1 prototype (SKILL.md section 10), used only by Meal Scan.
class MealScanStyle {
  const MealScanStyle._();

  static const Color primary = Color(0xFF0A6B5E);
  static const Color background = Color(0xFFF6F8F6);
  static const Color card = Color(0xFFFFFFFF);
  static const Color text = Color(0xFF14251F);
  static const Color textSecondary = Color(0xFF687872);
  static const Color border = Color(0xFFE1E8E4);
  static const Color success = Color(0xFF25815E);
  static const Color warning = Color(0xFFD28B2D);
  static const Color danger = Color(0xFFC94C4C);

  /// [warning] at about 12 % opacity, for banner backgrounds.
  static const Color warningTint = Color(0x1FE6A23C);

  static const double cardRadius = 18;
  static const double controlRadius = 16;

  static BoxDecoration cardDecoration() => BoxDecoration(
        color: card,
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: border),
      );

  static ButtonStyle primaryButton() => FilledButton.styleFrom(
        backgroundColor: primary,
        minimumSize: const Size.fromHeight(48),
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(controlRadius)),
      );

  static ButtonStyle secondaryButton() => OutlinedButton.styleFrom(
        foregroundColor: primary,
        minimumSize: const Size.fromHeight(48),
        side: const BorderSide(color: border),
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(controlRadius)),
      );
}
