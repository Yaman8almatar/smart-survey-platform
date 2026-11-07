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
}
