import 'package:flutter/widgets.dart';

/// Smart Survey design system colors.
abstract final class SsColors {
  static const Color brandDeep = Color(0xFF0A3F48);
  static const Color brand = Color(0xFF0E5A66);
  static const Color brandTint = Color(0xFFE3EFF1);
  static const Color brand50 = Color(0xFFEEF6F7);
  static const Color onBrandMuted = Color(0xFFBFDCE0);
  static const Color accent = Color(0xFFE3A21A);
  static const Color accentTint = Color(0xFFFCF3E0);
  static const Color ink = Color(0xFF13252A);
  static const Color inkMuted = Color(0xFF4E6268);
  static const Color surface = Color(0xFFF4F7F7);
  static const Color surfaceRaised = Color(0xFFFFFFFF);
  static const Color line = Color(0xFFD5E0E2);
  static const Color lineStrong = Color(0xFF7A8F95);
  static const Color sentimentPositive = Color(0xFF1F5F8B);
  static const Color sentimentNeutral = Color(0xFF9AA9AE);
  static const Color sentimentNegative = Color(0xFFB54C15);
  static const Color danger = sentimentNegative;
  static const Color dangerTint = Color(0xFFFBEDE6);
  static const Color chart1 = Color(0xFF0A3F48);
  static const Color chart2 = Color(0xFFE3A21A);
  static const Color chart3 = Color(0xFF4C9BD6);
  static const Color chart4 = Color(0xFF9C5A9A);
  static const Color chart5 = Color(0xFF6FA287);
  static const Color chartOther = Color(0xFF9AA9AE);
}

/// Smart Survey spacing scale in logical pixels.
abstract final class SsSpace {
  static const double s1 = 4;
  static const double s2 = 8;
  static const double s3 = 12;
  static const double s4 = 16;
  static const double s6 = 24;
  static const double s8 = 32;
  static const double s12 = 48;
}

/// Smart Survey layout and control sizes in logical pixels.
abstract final class SsLayout {
  static const double contentMaxWidth = 640;
  static const double formMaxWidth = 420;
  static const double indicatorSize = 20;
  static const double indicatorStroke = 2;
}

/// Smart Survey corner radii in logical pixels.
abstract final class SsRadius {
  static const double sm = 6;
  static const double md = 12;
  static const double lg = 20;
  static const double pill = 999;
}

/// Shadows for floating layers only (menus, snackbars, dialogs).
/// Cards and sections use a 1px line border instead.
abstract final class SsShadow {
  static const List<BoxShadow> float = [
    BoxShadow(color: Color(0x2E13252A), offset: Offset(0, 8), blurRadius: 24),
    BoxShadow(color: Color(0x1F13252A), offset: Offset(0, 1), blurRadius: 2),
  ];

  static const List<BoxShadow> dialog = [
    BoxShadow(color: Color(0x3D13252A), offset: Offset(0, 12), blurRadius: 32),
  ];
}

/// Smart Survey motion durations and curves.
abstract final class SsMotion {
  static const Duration fast = Duration(milliseconds: 150);
  static const Duration standard = Duration(milliseconds: 300);

  /// Only for the signal ring fill, its count-up and the single 100% ping.
  static const Duration emphasized = Duration(milliseconds: 500);

  /// Skeleton opacity pulse, repeating.
  static const Duration pulse = Duration(milliseconds: 1200);

  static const Curve standardCurve = Cubic(0.2, 0, 0, 1);
  static const Curve emphasizedCurve = Cubic(0.05, 0.7, 0.1, 1);

  /// [d], or [Duration.zero] when the platform asks for reduced motion.
  static Duration of(BuildContext context, Duration d) =>
      (MediaQuery.maybeDisableAnimationsOf(context) ?? false)
      ? Duration.zero
      : d;
}
