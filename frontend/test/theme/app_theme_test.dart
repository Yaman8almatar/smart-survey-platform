import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/theme/app_theme.dart';
import 'package:smart_survey_app/theme/tokens.dart';

void main() {
  testWidgets('app bars use the brand-deep band', (tester) async {
    final theme = AppTheme.light();

    expect(theme.appBarTheme.backgroundColor, SsColors.brandDeep);
    expect(theme.appBarTheme.shape, isNull);
  });

  testWidgets('selection uses brand tint, never saffron', (tester) async {
    final theme = AppTheme.light();

    expect(theme.colorScheme.secondaryContainer, SsColors.brandTint);
    expect(theme.colorScheme.onSecondaryContainer, SsColors.ink);
  });

  testWidgets('buttons use radius 12 and the snackbar radius 6', (
    tester,
  ) async {
    final theme = AppTheme.light();
    final button =
        theme.filledButtonTheme.style!.shape!.resolve({})!
            as RoundedRectangleBorder;
    final snackBar = theme.snackBarTheme.shape! as RoundedRectangleBorder;

    expect(button.borderRadius, BorderRadius.circular(SsRadius.md));
    expect(SsRadius.md, 12);
    expect(snackBar.borderRadius, BorderRadius.circular(SsRadius.sm));
    expect(SsRadius.sm, 6);
  });
}
