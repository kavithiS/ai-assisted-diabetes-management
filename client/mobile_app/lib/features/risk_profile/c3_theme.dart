import 'package:flutter/material.dart';

/// Colours and shapes of the team's interactive prototype (Module 3 · Risk + XAI),
/// applied only inside the C3 feature. The shared app theme (`lib/core/theme.dart`)
/// is not changed.
class C3Colors {
  const C3Colors._();

  static const primary = Color(0xFF087F8C);
  static const primaryDark = Color(0xFF05636D);
  static const primaryLight = Color(0xFFE6F6F7);
  static const background = Color(0xFFF7FAFA);
  static const card = Color(0xFFFFFFFF);
  static const text = Color(0xFF172B35);
  static const text2 = Color(0xFF667780);
  static const border = Color(0xFFDCE5E7);
  static const success = Color(0xFF2E9B62);
  static const successBg = Color(0xFFE9F6EF);
  static const warning = Color(0xFFB7791F); // prototype #E6A23C darkened for text contrast
  static const warningBg = Color(0xFFFCF3E3);
  static const danger = Color(0xFFC0392B); // prototype #D9534F darkened for text contrast
  static const dangerBg = Color(0xFFFBEAE9);
}

ThemeData c3Theme({Brightness brightness = Brightness.light}) {
  final dark = brightness == Brightness.dark;
  final surface = dark ? const Color(0xFF111C20) : C3Colors.background;
  final card = dark ? const Color(0xFF1B2A2F) : C3Colors.card;
  final border = dark ? const Color(0xFF34464C) : C3Colors.border;
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: C3Colors.primary,
      brightness: brightness,
      primary: C3Colors.primary,
      surface: surface,
      error: C3Colors.danger,
    ),
    scaffoldBackgroundColor: surface,
  );
  final buttonShape = RoundedRectangleBorder(borderRadius: BorderRadius.circular(12));
  const buttonSize = Size.fromHeight(50);
  const buttonText = TextStyle(fontSize: 15, fontWeight: FontWeight.w700);
  return base.copyWith(
    appBarTheme: AppBarTheme(
      backgroundColor: surface,
      foregroundColor: dark ? Colors.white : C3Colors.text,
      elevation: 0,
      titleTextStyle: TextStyle(
          fontSize: 18, fontWeight: FontWeight.w700, color: dark ? Colors.white : C3Colors.text),
    ),
    cardTheme: CardThemeData(
      color: card,
      elevation: 0,
      margin: const EdgeInsets.symmetric(vertical: 6),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: border),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: C3Colors.primary,
        // White on teal in both modes: the dark scheme's onPrimary is too dark to read.
        foregroundColor: Colors.white,
        minimumSize: buttonSize,
        shape: buttonShape,
        textStyle: buttonText,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: C3Colors.primary,
        minimumSize: buttonSize,
        shape: buttonShape,
        side: const BorderSide(color: C3Colors.primary),
        textStyle: buttonText,
      ),
    ),
    chipTheme: base.chipTheme.copyWith(
      selectedColor: dark ? const Color(0xFF20484C) : C3Colors.primaryLight,
      side: BorderSide(color: border),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: card,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
    ),
  );
}

/// Opens [screen] unless this screen is already opening another one. A fast double tap
/// would otherwise open it twice and, for a check, send and save it twice.
Future<T?> c3Push<T>(BuildContext context, Widget screen) {
  final route = ModalRoute.of(context);
  if (route != null && !route.isCurrent) return Future<T?>.value();
  return Navigator.of(context).push(c3Route<T>(screen));
}

/// Every C3 screen is pushed with the C3 theme (routes do not inherit a local Theme).
MaterialPageRoute<T> c3Route<T>(Widget screen) => MaterialPageRoute<T>(
      builder: (context) => Theme(
        data: c3Theme(brightness: MediaQuery.platformBrightnessOf(context)),
        child: screen,
      ),
    );
