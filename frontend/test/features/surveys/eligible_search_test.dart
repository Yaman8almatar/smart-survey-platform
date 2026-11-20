import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/features/auth/auth_models.dart';
import 'package:smart_survey_app/features/surveys/eligible_surveys_screen.dart';

import '../../support/test_api.dart';

const AppUser sara = AppUser(
  id: 7,
  email: 'sara@example.com',
  name: 'Sara',
  role: 'RESPONDENT',
);

/// The fixed device date of every test here.
DateTime fixedToday() => DateTime(2026, 11, 20, 15, 30);

/// Four surveys in the server's order.
const List<Map<String, Object?>> rankedSurveys = [
  {
    'id': 1,
    'title': 'Campus Services Survey',
    'description': 'How do you rate campus services?',
    'question_count': 1,
    'expected_minutes': 2,
    'published_on': '2026-11-20', // today
  },
  {
    'id': 2,
    'title': 'Transport in Homs',
    'description': 'Tell us about BUSES.',
    'question_count': 12,
    'expected_minutes': 8,
    'published_on': '2026-11-14', // six days ago: still this week
  },
  {
    'id': 3,
    'title': 'Library hours',
    'description': 'Opening times',
    'question_count': 4,
    'expected_minutes': 3,
    'published_on': '2026-11-13', // seven days ago: not this week
  },
  {
    'id': 4,
    'title': 'Old poll',
    'description': '',
    'question_count': 20,
    'expected_minutes': 10,
    'published_on': null,
  },
];

const List<String> allTitles = [
  'Campus Services Survey',
  'Transport in Homs',
  'Library hours',
  'Old poll',
];

Future<void> pumpList(
  WidgetTester tester, [
  List<Map<String, Object?>> surveys = rankedSurveys,
]) async {
  // Tall enough that every card is built.
  tester.view.physicalSize = const Size(800, 3000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  final test = TestApi((request) async => jsonResponse(surveys));
  await tester.pumpWidget(
    MaterialApp(
      home: EligibleSurveysScreen(
        authRepository: test.auth,
        surveysRepository: test.surveys,
        profileRepository: test.profile,
        answerRepository: test.answers,
        user: sara,
        today: fixedToday,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

/// The card titles shown, top to bottom.
List<String> shownTitles(WidgetTester tester) {
  final shown = [
    for (final title in allTitles)
      if (find.text(title).evaluate().isNotEmpty) title,
  ];
  shown.sort(
    (a, b) => tester
        .getTopLeft(find.text(a))
        .dy
        .compareTo(tester.getTopLeft(find.text(b)).dy),
  );
  return shown;
}

Future<void> search(WidgetTester tester, String text) async {
  await tester.enterText(find.byType(TextField), text);
  await tester.pumpAndSettle();
}

Future<void> chooseChip(WidgetTester tester, String label) async {
  await tester.tap(find.widgetWithText(ChoiceChip, label));
  await tester.pumpAndSettle();
}

bool chipSelected(WidgetTester tester, String label) =>
    tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, label)).selected;

void main() {
  testWidgets(
    'the meta line shows questions and minutes, singular and plural',
    (tester) async {
      await pumpList(tester);

      expect(find.text('1 question · About 2 min'), findsOneWidget);
      expect(find.text('12 questions · About 8 min'), findsOneWidget);
    },
  );

  testWidgets('shows the search field and three chips, All selected', (
    tester,
  ) async {
    await pumpList(tester);

    expect(find.widgetWithText(TextField, 'Search surveys'), findsOneWidget);
    expect(find.byType(ChoiceChip), findsNWidgets(3));
    expect(chipSelected(tester, 'All'), isTrue);
    expect(chipSelected(tester, 'Under 5 min'), isFalse);
    expect(chipSelected(tester, 'New this week'), isFalse);
    expect(shownTitles(tester), allTitles);
  });

  testWidgets('search matches the title, ignoring case and spaces', (
    tester,
  ) async {
    await pumpList(tester);

    await search(tester, '  TRANSPORT ');

    expect(shownTitles(tester), ['Transport in Homs']);
  });

  testWidgets('search matches the description, ignoring case', (tester) async {
    await pumpList(tester);

    await search(tester, 'buses');

    expect(shownTitles(tester), ['Transport in Homs']);
  });

  testWidgets('Under 5 min keeps surveys under five minutes, in order', (
    tester,
  ) async {
    await pumpList(tester);

    await chooseChip(tester, 'Under 5 min');

    expect(chipSelected(tester, 'Under 5 min'), isTrue);
    expect(chipSelected(tester, 'All'), isFalse);
    expect(shownTitles(tester), ['Campus Services Survey', 'Library hours']);
  });

  testWidgets('New this week keeps the last seven days, today included', (
    tester,
  ) async {
    await pumpList(tester);

    await chooseChip(tester, 'New this week');

    expect(shownTitles(tester), [
      'Campus Services Survey',
      'Transport in Homs',
    ]);
  });

  testWidgets('All brings every survey back after a chip', (tester) async {
    await pumpList(tester);
    await chooseChip(tester, 'New this week');

    await chooseChip(tester, 'All');

    expect(shownTitles(tester), allTitles);
  });

  testWidgets('search and chip apply together', (tester) async {
    await pumpList(tester);

    await search(tester, 'survey');
    await chooseChip(tester, 'Under 5 min');

    expect(shownTitles(tester), ['Campus Services Survey']);
  });

  testWidgets('no result shows the message, and Clear search resets', (
    tester,
  ) async {
    await pumpList(tester);
    await search(tester, 'transport');
    await chooseChip(tester, 'Under 5 min');

    expect(shownTitles(tester), isEmpty);
    expect(find.text('No surveys match your search.'), findsOneWidget);

    await tester.tap(find.widgetWithText(OutlinedButton, 'Clear search'));
    await tester.pumpAndSettle();

    expect(find.text('No surveys match your search.'), findsNothing);
    expect(
      tester.widget<TextField>(find.byType(TextField)).controller!.text,
      '',
    );
    expect(chipSelected(tester, 'All'), isTrue);
    expect(shownTitles(tester), allTitles);
  });

  testWidgets('an empty list shows no search field and no chips', (
    tester,
  ) async {
    await pumpList(tester, const []);

    expect(find.text('No surveys match your profile yet.'), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
    expect(find.byType(ChoiceChip), findsNothing);
  });
}
