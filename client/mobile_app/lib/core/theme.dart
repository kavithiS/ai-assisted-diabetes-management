import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  const AppColors._();

  static const primary = Color(0xFF087F8C);
  static const primaryDark = Color(0xFF05636D);
  static const primaryLight = Color(0xFFE6F6F7);
  static const background = Color(0xFFF7FAFA);
  static const card = Color(0xFFFFFFFF);
  static const text = Color(0xFF172B35);
  static const textSecondary = Color(0xFF667780);
  static const border = Color(0xFFDCE5E7);
  static const success = Color(0xFF2E9B62);
  static const successBg = Color(0xFFE9F6EF);
  static const warning = Color(0xFFE6A23C);
  static const warningBg = Color(0xFFFCF3E3);
  static const danger = Color(0xFFD9534F);
  static const dangerBg = Color(0xFFFBEAE9);
}

ThemeData buildAppTheme() {
  final base = ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      primary: AppColors.primary,
      onPrimary: Colors.white,
      surface: AppColors.card,
      onSurface: AppColors.text,
    ),
    useMaterial3: true,
    scaffoldBackgroundColor: AppColors.background,
  );
  return base.copyWith(
    textTheme: GoogleFonts.interTextTheme(base.textTheme).apply(
      bodyColor: AppColors.text,
      displayColor: AppColors.text,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(50),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: GoogleFonts.inter(fontWeight: FontWeight.w700, fontSize: 15),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        minimumSize: const Size.fromHeight(50),
        side: const BorderSide(color: AppColors.primary, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: GoogleFonts.inter(fontWeight: FontWeight.w700, fontSize: 15),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: AppColors.card,
      selectedColor: AppColors.primary,
      labelStyle: GoogleFonts.inter(
          fontSize: 12.5, fontWeight: FontWeight.w600, color: AppColors.text),
      side: const BorderSide(color: AppColors.border, width: 1.5),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 5),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.card,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.border, width: 1.5),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
    ),
  );
}

/// Shared card decoration used across features.
BoxDecoration appCardDecoration({Color? color}) => BoxDecoration(
      color: color ?? AppColors.card,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: AppColors.border),
    );

/// Primary filled button style.
ButtonStyle primaryButtonStyle() => FilledButton.styleFrom(
      backgroundColor: AppColors.primary,
      foregroundColor: Colors.white,
      minimumSize: const Size.fromHeight(50),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      textStyle: GoogleFonts.inter(fontWeight: FontWeight.w700, fontSize: 15),
    );

/// Secondary outlined button style.
ButtonStyle secondaryButtonStyle() => OutlinedButton.styleFrom(
      foregroundColor: AppColors.primary,
      minimumSize: const Size.fromHeight(50),
      side: const BorderSide(color: AppColors.primary, width: 1.5),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      textStyle: GoogleFonts.inter(fontWeight: FontWeight.w700, fontSize: 15),
    );

/// Ghost button style.
ButtonStyle ghostButtonStyle() => OutlinedButton.styleFrom(
      foregroundColor: AppColors.textSecondary,
      minimumSize: const Size.fromHeight(50),
      side: const BorderSide(color: AppColors.border, width: 1.5),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      textStyle: GoogleFonts.inter(fontWeight: FontWeight.w700, fontSize: 15),
    );
