import 'package:flutter/widgets.dart';

final RegExp _letter = RegExp(r'\p{L}', unicode: true);
final RegExp _arabicLetter = RegExp(r'\p{Script=Arabic}', unicode: true);

/// Right to left when the first letter of [text] is Arabic, left to right otherwise.
TextDirection directionOf(String text) {
  final first = _letter.firstMatch(text)?.group(0);
  return first != null && _arabicLetter.hasMatch(first)
      ? TextDirection.rtl
      : TextDirection.ltr;
}
