import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/core/text_direction.dart';

void main() {
  test('Arabic text is right to left', () {
    expect(directionOf('الخدمة جيدة'), TextDirection.rtl);
  });

  test('English text is left to right', () {
    expect(directionOf('Good service'), TextDirection.ltr);
  });

  test('empty text is left to right', () {
    expect(directionOf(''), TextDirection.ltr);
  });

  test('digits before Arabic do not decide', () {
    expect(directionOf('12 - الخدمة'), TextDirection.rtl);
  });

  test('digits alone are left to right', () {
    expect(directionOf('123'), TextDirection.ltr);
  });
}
