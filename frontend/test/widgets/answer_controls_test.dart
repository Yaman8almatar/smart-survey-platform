import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/theme/app_theme.dart';
import 'package:smart_survey_app/widgets/answer_option.dart';
import 'package:smart_survey_app/widgets/open_text_field.dart';
import 'package:smart_survey_app/widgets/rating_scale.dart';

Widget host(Widget child) => MaterialApp(
  theme: AppTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AnswerOption', () {
    testWidgets('reports a tap', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        host(AnswerOption(label: 'Taxi', selected: false, onTap: () => taps++)),
      );

      await tester.tap(find.text('Taxi'));

      expect(taps, 1);
    });

    testWidgets('is a checked item of an exclusive group', (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(
        host(AnswerOption(label: 'Taxi', selected: true, onTap: () {})),
      );

      expect(
        tester.getSemantics(find.byType(AnswerOption)),
        isSemantics(
          label: 'Taxi',
          isInMutuallyExclusiveGroup: true,
          hasCheckedState: true,
          isChecked: true,
          hasTapAction: true,
        ),
      );
      semantics.dispose();
    });

    testWidgets('an unselected row is not checked', (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(
        host(AnswerOption(label: 'Taxi', selected: false, onTap: () {})),
      );

      expect(
        tester.getSemantics(find.byType(AnswerOption)),
        isSemantics(hasCheckedState: true, isChecked: false),
      );
      semantics.dispose();
    });
  });

  group('RatingScale', () {
    Widget scale({int? selected, ValueChanged<int>? onChanged}) => host(
      RatingScale(
        values: const [1, 2, 3, 4, 5],
        selected: selected,
        onChanged: onChanged ?? (_) {},
      ),
    );

    testWidgets('reports the value tapped', (tester) async {
      int? chosen;
      await tester.pumpWidget(scale(onChanged: (value) => chosen = value));

      await tester.tap(find.text('4'));

      expect(chosen, 4);
    });

    testWidgets('each button is read as N out of 5', (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(scale(selected: 4));

      expect(
        tester.getSemantics(find.bySemanticsLabel('4 out of 5')),
        isSemantics(
          isInMutuallyExclusiveGroup: true,
          hasCheckedState: true,
          isChecked: true,
        ),
      );
      expect(
        tester.getSemantics(find.bySemanticsLabel('2 out of 5')),
        isSemantics(hasCheckedState: true, isChecked: false),
      );
      semantics.dispose();
    });

    testWidgets('the end names are shown but not read', (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(scale());

      expect(find.text('Lowest'), findsOneWidget);
      expect(find.text('Highest'), findsOneWidget);
      expect(find.bySemanticsLabel('Lowest'), findsNothing);
      expect(find.bySemanticsLabel('Highest'), findsNothing);
      semantics.dispose();
    });
  });

  group('OpenTextField', () {
    Widget field() => host(OpenTextField(initialText: '', onChanged: (_) {}));

    testWidgets('counts the characters typed', (tester) async {
      await tester.pumpWidget(field());

      await tester.enterText(find.byType(TextField), 'Hello');
      await tester.pump();

      expect(find.text('5 / 2000'), findsOneWidget);
      expect(find.text('You reached the 2,000 character limit.'), findsNothing);
    });

    testWidgets('says so at the limit', (tester) async {
      await tester.pumpWidget(field());

      await tester.enterText(find.byType(TextField), 'a' * 2000);
      await tester.pump();

      expect(find.text('2000 / 2000'), findsOneWidget);
      expect(
        find.text('You reached the 2,000 character limit.'),
        findsOneWidget,
      );
    });

    testWidgets('follows the language typed', (tester) async {
      await tester.pumpWidget(field());

      await tester.enterText(find.byType(TextField), 'الخدمة جيدة');
      await tester.pump();
      expect(
        tester.widget<TextField>(find.byType(TextField)).textDirection,
        TextDirection.rtl,
      );

      await tester.enterText(find.byType(TextField), 'Good service');
      await tester.pump();
      expect(
        tester.widget<TextField>(find.byType(TextField)).textDirection,
        TextDirection.ltr,
      );
    });
  });
}
