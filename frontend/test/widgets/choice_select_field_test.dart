import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/features/profile/profile_models.dart';
import 'package:smart_survey_app/theme/app_theme.dart';
import 'package:smart_survey_app/widgets/choice_select_field.dart';

const List<ChoiceOption> governorates = [
  ChoiceOption(code: 'ALEPPO', label: 'Aleppo'),
  ChoiceOption(code: 'DAMASCUS', label: 'Damascus'),
  ChoiceOption(code: 'HOMS', label: 'Homs'),
  ChoiceOption(code: 'OUTSIDE_SYRIA', label: 'Outside Syria'),
];

Future<void> pumpField(WidgetTester tester, {String? value}) {
  return tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.light(),
      home: Scaffold(
        body: ChoiceSelectField(
          label: 'Governorate',
          options: governorates,
          value: value,
          onChanged: (_) {},
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('the field shows the selected label in regular weight', (
    tester,
  ) async {
    await pumpField(tester, value: 'DAMASCUS');

    final shown = tester.widget<RichText>(
      find.descendant(
        of: find.text('Damascus'),
        matching: find.byType(RichText),
      ),
    );
    expect(shown.text.style?.fontWeight, isNot(FontWeight.w600));
  });

  testWidgets('a divider sits above Outside Syria in the menu', (tester) async {
    await pumpField(tester);

    await tester.tap(find.text('Governorate'));
    await tester.pumpAndSettle();

    final divider = find.byType(Divider);
    expect(divider, findsOneWidget);
    final dividerRect = tester.getRect(divider);
    expect(
      dividerRect.top,
      greaterThanOrEqualTo(tester.getRect(find.text('Homs').last).bottom),
    );
    expect(
      dividerRect.bottom,
      lessThanOrEqualTo(tester.getRect(find.text('Outside Syria').last).top),
    );
  });
}
