import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/features/profile/profile_models.dart';
import 'package:smart_survey_app/theme/app_theme.dart';
import 'package:smart_survey_app/widgets/interest_chips.dart';

void main() {
  const options = [
    ChoiceOption(code: 'TECHNOLOGY', label: 'Technology'),
    ChoiceOption(code: 'SPORTS', label: 'Sports'),
  ];

  testWidgets('an unselected chip shows its topic icon, a selected one the '
      'check', (tester) async {
    Set<String>? changed;
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light(),
        home: Scaffold(
          body: InterestChips(
            options: options,
            selected: const {'TECHNOLOGY'},
            onChanged: (next) => changed = next,
          ),
        ),
      ),
    );

    final technology = tester.widget<FilterChip>(
      find.widgetWithText(FilterChip, 'Technology'),
    );
    final sports = tester.widget<FilterChip>(
      find.widgetWithText(FilterChip, 'Sports'),
    );
    expect(technology.selected, isTrue);
    expect(technology.avatar, isNull);
    expect(sports.selected, isFalse);
    expect((sports.avatar! as Icon).icon, Icons.sports_soccer_outlined);
    expect(find.byIcon(Icons.sports_soccer_outlined), findsOneWidget);

    await tester.tap(find.text('Sports'));
    expect(changed, {'TECHNOLOGY', 'SPORTS'});
  });

  testWidgets('shows the error line under the chips', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: InterestChips(
            options: options,
            selected: const {},
            onChanged: (_) {},
            errorText: 'Choose at least one interest.',
          ),
        ),
      ),
    );

    final error = tester.getTopLeft(find.text('Choose at least one interest.'));
    final chip = tester.getBottomLeft(find.byType(FilterChip).first);
    expect(error.dy, greaterThanOrEqualTo(chip.dy));
  });
}
