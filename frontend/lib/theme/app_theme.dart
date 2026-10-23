import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'tokens.dart';

/// Smart Survey type scale: Readex Pro for display text, IBM Plex Sans for reading text.
abstract final class SsType {
  static TextStyle get display => GoogleFonts.readexPro(
    fontSize: 32,
    height: 38 / 32,
    fontWeight: FontWeight.w600,
  );

  static TextStyle get title => GoogleFonts.readexPro(
    fontSize: 22,
    height: 28 / 22,
    fontWeight: FontWeight.w600,
  );

  static TextStyle get stat => GoogleFonts.readexPro(
    fontSize: 28,
    height: 32 / 28,
    fontWeight: FontWeight.w600,
  );

  static TextStyle get heading => GoogleFonts.ibmPlexSans(
    fontSize: 17,
    height: 24 / 17,
    fontWeight: FontWeight.w600,
  );

  static TextStyle get body => GoogleFonts.ibmPlexSans(
    fontSize: 15,
    height: 22 / 15,
    fontWeight: FontWeight.w400,
  );

  static TextStyle get label => GoogleFonts.ibmPlexSans(
    fontSize: 13,
    height: 18 / 13,
    fontWeight: FontWeight.w500,
  );

  static TextStyle get caption => GoogleFonts.ibmPlexSans(
    fontSize: 12,
    height: 16 / 12,
    fontWeight: FontWeight.w400,
  );
}

/// Builds the app ThemeData from the Smart Survey design tokens.
abstract final class AppTheme {
  static ThemeData light() {
    const colorScheme = ColorScheme(
      brightness: Brightness.light,
      primary: SsColors.brand,
      onPrimary: SsColors.surfaceRaised,
      secondary: SsColors.accent,
      onSecondary: SsColors.ink,
      error: SsColors.danger,
      onError: SsColors.surfaceRaised,
      surface: SsColors.surfaceRaised,
      onSurface: SsColors.ink,
      onSurfaceVariant: SsColors.inkMuted,
      outline: SsColors.lineStrong,
      outlineVariant: SsColors.line,
    );

    final textTheme = TextTheme(
      displaySmall: SsType.display,
      headlineMedium: SsType.stat,
      titleLarge: SsType.title,
      titleMedium: SsType.heading,
      bodyLarge: SsType.body,
      bodyMedium: SsType.body,
      bodySmall: SsType.caption,
      labelLarge: SsType.label,
      labelMedium: SsType.label,
    ).apply(bodyColor: SsColors.ink, displayColor: SsColors.ink);

    final mediumShape = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(SsRadius.md),
    );
    final smallRadius = BorderRadius.circular(SsRadius.sm);

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: SsColors.surface,
      textTheme: textTheme,
      appBarTheme: AppBarTheme(
        backgroundColor: SsColors.surfaceRaised,
        foregroundColor: SsColors.ink,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        titleTextStyle: textTheme.titleLarge,
        shape: const Border(bottom: BorderSide(color: SsColors.line)),
      ),
      cardTheme: CardThemeData(
        color: SsColors.surfaceRaised,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: mediumShape.copyWith(
          side: const BorderSide(color: SsColors.line),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          shape: mediumShape,
          textStyle: textTheme.labelLarge,
          padding: const EdgeInsets.symmetric(
            horizontal: SsSpace.s6,
            vertical: SsSpace.s2,
          ),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(shape: mediumShape),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(shape: mediumShape),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(shape: mediumShape),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: smallRadius),
        enabledBorder: OutlineInputBorder(
          borderRadius: smallRadius,
          borderSide: const BorderSide(color: SsColors.lineStrong),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: smallRadius,
          borderSide: const BorderSide(color: SsColors.brand, width: 2),
        ),
      ),
    );
  }
}
