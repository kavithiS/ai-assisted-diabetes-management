import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  const AppColors._();

  static const primary = Color(0xFF0A6B5E);
  static const primaryDark = Color(0xFF073F38);
  static const primarySoft = Color(0xFFA8DED2);
  static const primaryLight = Color(0xFFE7F5F1);
  static const accent = Color(0xFFCBEA68);
  static const accentLight = Color(0xFFF2F8DA);
  static const background = Color(0xFFF6F8F6);
  static const card = Color(0xFFFFFFFF);
  static const text = Color(0xFF14251F);
  static const textSecondary = Color(0xFF687872);
  static const border = Color(0xFFE1E8E4);
  static const success = Color(0xFF25815E);
  static const successBg = Color(0xFFE8F5EE);
  static const warning = Color(0xFFD28B2D);
  static const warningBg = Color(0xFFFFF5E5);
  static const danger = Color(0xFFC94C4C);
  static const dangerBg = Color(0xFFFCECEC);
}

ThemeData buildAppTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    primary: AppColors.primary,
    onPrimary: Colors.white,
    surface: AppColors.card,
    onSurface: AppColors.text,
    error: AppColors.danger,
    brightness: Brightness.light,
  );
  final base = ThemeData(
    colorScheme: scheme,
    useMaterial3: true,
    scaffoldBackgroundColor: AppColors.background,
  );
  final type = GoogleFonts.manropeTextTheme(base.textTheme).apply(
    bodyColor: AppColors.text,
    displayColor: AppColors.text,
  );

  return base.copyWith(
    textTheme: type.copyWith(
      headlineSmall: GoogleFonts.manrope(
        fontSize: 26,
        height: 1.12,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.8,
        color: AppColors.text,
      ),
      titleLarge: GoogleFonts.manrope(
        fontSize: 20,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.4,
        color: AppColors.text,
      ),
      titleMedium: GoogleFonts.manrope(
        fontSize: 15,
        fontWeight: FontWeight.w800,
        color: AppColors.text,
      ),
      bodyMedium: GoogleFonts.manrope(
        fontSize: 13.5,
        height: 1.45,
        color: AppColors.text,
      ),
      labelLarge: GoogleFonts.manrope(
        fontSize: 13,
        fontWeight: FontWeight.w800,
        color: AppColors.text,
      ),
    ),
    appBarTheme: AppBarTheme(
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      backgroundColor: AppColors.background,
      foregroundColor: AppColors.text,
      surfaceTintColor: Colors.transparent,
      titleTextStyle: GoogleFonts.manrope(
        fontSize: 19,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.3,
        color: AppColors.text,
      ),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      margin: EdgeInsets.zero,
      color: AppColors.card,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: AppColors.border),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        disabledBackgroundColor: const Color(0xFFDCE6E2),
        disabledForegroundColor: const Color(0xFF94A39D),
        minimumSize: const Size.fromHeight(54),
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle:
            GoogleFonts.manrope(fontWeight: FontWeight.w800, fontSize: 14),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.text,
        minimumSize: const Size.fromHeight(54),
        side: const BorderSide(color: AppColors.border, width: 1.3),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle:
            GoogleFonts.manrope(fontWeight: FontWeight.w800, fontSize: 14),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: AppColors.card,
      selectedColor: AppColors.primaryLight,
      labelStyle: GoogleFonts.manrope(
          fontSize: 12.5, fontWeight: FontWeight.w700, color: AppColors.text),
      side: const BorderSide(color: AppColors.border),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 5),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: const Color(0xFFFBFCFB),
      hintStyle: const TextStyle(color: Color(0xFF94A09C)),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.border, width: 1.2),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.6),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.danger),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.border, space: 1),
    floatingActionButtonTheme: FloatingActionButtonThemeData(
      elevation: 2,
      backgroundColor: AppColors.primaryDark,
      foregroundColor: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
    ),
    progressIndicatorTheme:
        const ProgressIndicatorThemeData(color: AppColors.primary),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: AppColors.text,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: AppColors.card,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
    ),
    searchBarTheme: SearchBarThemeData(
      elevation: const WidgetStatePropertyAll(0),
      backgroundColor: const WidgetStatePropertyAll(AppColors.card),
      surfaceTintColor: const WidgetStatePropertyAll(Colors.transparent),
      side: const WidgetStatePropertyAll(BorderSide(color: AppColors.border)),
      shape: WidgetStatePropertyAll(
        RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
    ),
  );
}

BoxDecoration appCardDecoration({Color? color}) => BoxDecoration(
      color: color ?? AppColors.card,
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: AppColors.border),
      boxShadow: const [
        BoxShadow(
          color: Color(0x0A14251F),
          blurRadius: 20,
          offset: Offset(0, 8),
        ),
      ],
    );

ButtonStyle primaryButtonStyle() => FilledButton.styleFrom(
      backgroundColor: AppColors.primary,
      foregroundColor: Colors.white,
      minimumSize: const Size.fromHeight(54),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      textStyle:
          GoogleFonts.manrope(fontWeight: FontWeight.w800, fontSize: 14),
    );

ButtonStyle secondaryButtonStyle() => OutlinedButton.styleFrom(
      foregroundColor: AppColors.primary,
      minimumSize: const Size.fromHeight(54),
      side: const BorderSide(color: AppColors.primary, width: 1.3),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      textStyle:
          GoogleFonts.manrope(fontWeight: FontWeight.w800, fontSize: 14),
    );

ButtonStyle ghostButtonStyle() => OutlinedButton.styleFrom(
      foregroundColor: AppColors.text,
      minimumSize: const Size.fromHeight(54),
      side: const BorderSide(color: AppColors.border, width: 1.3),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      textStyle:
          GoogleFonts.manrope(fontWeight: FontWeight.w800, fontSize: 14),
    );
