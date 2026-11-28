import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/features/auth/auth_models.dart';
import 'package:smart_survey_app/features/surveys/eligible_surveys_screen.dart';
import 'package:smart_survey_app/features/surveys/surveys_models.dart';

import '../../support/test_api.dart';

const AppUser sara = AppUser(
  id: 7,
  email: 'sara@example.com',
  name: 'Sara',
  role: 'RESPONDENT',
);

DateTime fixedToday() => DateTime(2026, 11, 20, 15, 30);

const List<Map<String, Object?>> surveys = [
  {
    'id': 1,
    'title': 'Campus Services Survey',
    'description': '',
    'question_count': 5,
    'expected_minutes': 2,
    'published_on': '2026-11-20',
    'closes_on': '2026-11-30',
  },
  {
    'id': 2,
    'title': 'Library hours',
    'description': '',
    'question_count': 4,
    'expected_minutes': 3,
    'published_on': '2026-11-18',
    'closes_on': null,
  },
  {
    'id': 3,
    'title': 'Spring fair',
    'description': '',
    'question_count': 1,
    'expected_minutes': 1,
    'published_on': '2026-11-19',
    'closes_on': '2027-01-05',
  },
];

Future<void> pumpList(WidgetTester tester) async {
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

void main() {
  testWidgets('the meta line shows the closing date when there is one', (
    tester,
  ) async {
    await pumpList(tester);

    expect(
      find.text('5 questions · About 2 min · Closes 30 Nov'),
      findsOneWidget,
    );
    expect(
      find.text('1 question · About 1 min · Closes 5 Jan'),
      findsOneWidget,
    );
  });

  testWidgets('the meta line is unchanged without a closing date', (
    tester,
  ) async {
    await pumpList(tester);

    expect(find.text('4 questions · About 3 min'), findsOneWidget);
  });

  test('closes_on is parsed as a date, and a missing key gives null', () {
    final dated = EligibleSurvey.fromJson(surveys.first);
    expect(dated.closesOn, DateTime(2026, 11, 30));

    final withoutKey = EligibleSurvey.fromJson({
      'id': 9,
      'title': 'Old poll',
      'question_count': 2,
      'expected_minutes': 1,
      'published_on': null,
    });
    expect(withoutKey.closesOn, isNull);
  });
}
