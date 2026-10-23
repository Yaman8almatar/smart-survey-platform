import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:smart_survey_app/core/api/token_store.dart';
import 'package:smart_survey_app/features/auth/auth_models.dart';
import 'package:smart_survey_app/features/auth/login_screen.dart';
import 'package:smart_survey_app/features/surveys/eligible_surveys_screen.dart';

import '../../support/test_api.dart';

const AppUser sara = AppUser(
  id: 7,
  email: 'sara@example.com',
  name: 'Sara',
  role: 'RESPONDENT',
);

const Map<String, Object> demoSurvey = {
  'id': 1,
  'title': 'Campus Services Survey',
  'description': 'How do you rate campus services?',
  'question_count': 5,
};

Future<void> pumpList(WidgetTester tester, TestApi test) async {
  await tester.pumpWidget(
    MaterialApp(
      home: EligibleSurveysScreen(
        authRepository: test.auth,
        surveysRepository: test.surveys,
        user: sara,
      ),
    ),
  );
}

void main() {
  testWidgets('shows a progress indicator while loading', (tester) async {
    final gate = Completer<http.Response>();
    final test = TestApi((request) => gate.future);

    await pumpList(tester, test);

    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    gate.complete(jsonResponse([]));
    await tester.pumpAndSettle();
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('shows the error with Retry, and Retry reloads', (tester) async {
    var calls = 0;
    final test = TestApi((request) async {
      calls++;
      return calls == 1
          ? errorResponse(500, 'internal_error', 'Something went wrong.')
          : jsonResponse([demoSurvey]);
    });

    await pumpList(tester, test);
    await tester.pumpAndSettle();

    expect(find.text('Something went wrong.'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Retry'));
    await tester.pumpAndSettle();

    expect(find.text('Campus Services Survey'), findsOneWidget);
  });

  testWidgets('an unreachable server shows the network message', (
    tester,
  ) async {
    final test = TestApi((request) async => throw http.ClientException('down'));

    await pumpList(tester, test);
    await tester.pumpAndSettle();

    expect(
      find.text('Cannot reach the server. Is it running?'),
      findsOneWidget,
    );
    expect(find.widgetWithText(FilledButton, 'Retry'), findsOneWidget);
  });

  testWidgets('shows the empty state', (tester) async {
    final test = TestApi((request) async => jsonResponse([]));

    await pumpList(tester, test);
    await tester.pumpAndSettle();

    expect(find.text('No surveys match your profile yet.'), findsOneWidget);
    expect(
      find.text(
        'New surveys appear here when a provider targets your age, gender '
        'and region.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('shows title, description and question count, no Start', (
    tester,
  ) async {
    final test = TestApi((request) async => jsonResponse([demoSurvey]));

    await pumpList(tester, test);
    await tester.pumpAndSettle();

    expect(find.text('Sara'), findsOneWidget);
    expect(find.text('Campus Services Survey'), findsOneWidget);
    expect(find.text('How do you rate campus services?'), findsOneWidget);
    expect(find.text('5 questions'), findsOneWidget);
    expect(find.text('Matches your profile'), findsOneWidget);
    expect(find.text('Start'), findsNothing);
  });

  testWidgets('pull to refresh reloads the list', (tester) async {
    var calls = 0;
    final test = TestApi((request) async {
      calls++;
      return jsonResponse([demoSurvey]);
    });
    await pumpList(tester, test);
    await tester.pumpAndSettle();

    await tester.fling(find.byType(ListView), const Offset(0, 300), 1000);
    await tester.pumpAndSettle();

    expect(calls, 2);
  });

  testWidgets('logout clears tokens and returns to login', (tester) async {
    final test = TestApi(
      (request) async => jsonResponse([]),
      tokens: MemoryTokenStore(access: 'a', refresh: 'r'),
    );
    await pumpList(tester, test);
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Log out'));
    await tester.pumpAndSettle();

    expect(find.byType(LoginScreen), findsOneWidget);
    expect(test.tokens.refresh, isNull);
  });

  testWidgets('an ended session goes back to login with a notice', (
    tester,
  ) async {
    final test = TestApi(
      (request) async =>
          errorResponse(401, 'authentication_failed', 'Token invalid.'),
      tokens: MemoryTokenStore(access: 'a', refresh: 'r'),
    );

    await pumpList(tester, test);
    await tester.pumpAndSettle();

    expect(find.byType(LoginScreen), findsOneWidget);
    expect(
      find.text('Your session ended. Please log in again.'),
      findsOneWidget,
    );
  });
}
