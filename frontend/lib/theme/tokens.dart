import 'package:flutter/painting.dart';

/// Smart Survey design system colors.
abstract final class SsColors {
  static const Color brand = Color(0xFF0E5A66);
  static const Color brandTint = Color(0xFFE3EFF1);
  static const Color accent = Color(0xFFE3A21A);
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
}

/// Smart Survey spacing scale in logical pixels.
abstract final class SsSpace {
  static const double s1 = 4;
  static const double s2 = 8;
  static const double s4 = 16;
  static const double s6 = 24;
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
  static const double pill = 999;
}
