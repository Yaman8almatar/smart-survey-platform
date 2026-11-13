import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:smart_survey_app/core/api/token_store.dart';
import 'package:smart_survey_app/features/auth/auth_models.dart';
import 'package:smart_survey_app/features/surveys/answered_surveys_screen.dart';
import 'package:smart_survey_app/features/surveys/eligible_surveys_screen.dart';

import '../../support/test_api.dart';

/// Fixed "now" for every test; rows use local times so the clock text is stable.
final DateTime now = DateTime(2026, 11, 13, 20);

const List<Map<String, Object?>> twoRows = [
  {
    'survey_id': 4,
    'title': 'Campus Services Survey',
    'description': 'How do you rate campus services?',
    'submitted_at': '2026-11-13T17:42:00',
  },
  {
    'survey_id': 1,
    'title': 'Library Hours Survey',
    'description': '',
    'submitted_at': '2025-11-07T09:05:00',
  },
];

class _PushCounter extends NavigatorObserver {
  int pushes = 0;

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    pushes++;
  }
}

Future<void> pumpAnswered(
  WidgetTester tester,
  TestApi test, {
  VoidCallback? onSessionExpired,
  List<NavigatorObserver> observers = const [],
}) async {
  await tester.pumpWidget(
    MaterialApp(
      navigatorObservers: observers,
      home: AnsweredSurveysScreen(
        surveysRepository: test.surveys,
        onSessionExpired: onSessionExpired ?? () {},
        clock: () => now,
      ),
    ),
  );
}

void main() {
  testWidgets('shows a progress indicator while loading', (tester) async {
    final gate = Completer<http.Response>();
    final test = TestApi((request) => gate.future);

    await pumpAnswered(tester, test);

    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    gate.complete(jsonResponse([]));
    await tester.pumpAndSettle();
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('shows the heading, the intro and the cards in server order', (
    tester,
  ) async {
    final test = TestApi((request) async => jsonResponse(twoRows));

    await pumpAnswered(tester, test);
    await tester.pumpAndSettle();

    expect(find.text('Answered surveys'), findsOneWidget);
    expect(find.text('Surveys you answered'), findsOneWidget);
    expect(
      find.text('You answer each survey once. Sent answers cannot be changed.'),
      findsOneWidget,
    );
    expect(find.byType(Card), findsNWidgets(2));
    expect(
      tester.getTopLeft(find.text('Campus Services Survey')).dy,
      lessThan(tester.getTopLeft(find.text('Library Hours Survey')).dy),
    );
    expect(find.text('How do you rate campus services?'), findsOneWidget);
    expect(
      find.descendant(
        of: find.ancestor(
          of: find.text('Library Hours Survey'),
          matching: find.byType(Card),
        ),
        matching: find.byType(Text),
      ),
      findsNWidgets(2),
    );
    expect(find.text('Sent today at 17:42.'), findsOneWidget);
    expect(find.text('Sent on 7 November 2025 at 09:05.'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle_outline), findsNWidgets(2));
  });

  testWidgets('a card has no chevron and a tap opens nothing', (tester) async {
    final test = TestApi((request) async => jsonResponse(twoRows));
    final counter = _PushCounter();

    await pumpAnswered(tester, test, observers: [counter]);
    await tester.pumpAndSettle();
    final before = counter.pushes;

    expect(find.byIcon(Icons.chevron_right), findsNothing);
    expect(
      find.descendant(of: find.byType(Card), matching: find.byType(InkWell)),
      findsNothing,
    );

    await tester.tap(find.text('Campus Services Survey'));
    await tester.pumpAndSettle();

    expect(counter.pushes, before);
    expect(find.byType(AnsweredSurveysScreen), findsOneWidget);
  });

  testWidgets('shows the empty state, and its button goes back to the list', (
    tester,
  ) async {
    final test = TestApi((request) async => jsonResponse([]));
    await tester.pumpWidget(
      MaterialApp(
        home: EligibleSurveysScreen(
          authRepository: test.auth,
          surveysRepository: test.surveys,
          profileRepository: test.profile,
          answerRepository: test.answers,
          user: const AppUser(
            id: 7,
            email: 'sara@example.com',
            name: 'Sara',
            role: 'RESPONDENT',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Answered surveys'));
    await tester.pumpAndSettle();

    expect(find.text('No answered surveys yet.'), findsOneWidget);
    expect(
      find.text('Surveys you send appear here with the day you sent them.'),
      findsOneWidget,
    );

    await tester.tap(
      find.widgetWithText(OutlinedButton, 'See surveys that match you'),
    );
    await tester.pumpAndSettle();

    expect(find.byType(AnsweredSurveysScreen), findsNothing);
    expect(find.byType(EligibleSurveysScreen), findsOneWidget);
  });

  testWidgets('a network error shows its copy, and Try again loads the cards', (
    tester,
  ) async {
    var calls = 0;
    final test = TestApi((request) async {
      calls++;
      if (calls == 1) throw http.ClientException('down');
      return jsonResponse(twoRows);
    });

    await pumpAnswered(tester, test);
    await tester.pumpAndSettle();

    expect(find.text('Could not load answered surveys'), findsOneWidget);
    expect(
      find.text(
        'Cannot reach the server. Check your connection and try again.',
      ),
      findsOneWidget,
    );
    expect(find.byIcon(Icons.cloud_off_outlined), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Try again'));
    await tester.pumpAndSettle();

    expect(find.byType(Card), findsNWidgets(2));
  });

  testWidgets('a server error shows the generic copy, not the server text', (
    tester,
  ) async {
    final test = TestApi(
      (request) async =>
          errorResponse(500, 'internal_error', 'Database is down.'),
    );

    await pumpAnswered(tester, test);
    await tester.pumpAndSettle();

    expect(
      find.text('Something went wrong. Please try again.'),
      findsOneWidget,
    );
    expect(find.text('Database is down.'), findsNothing);
  });

  testWidgets('an ended session calls onSessionExpired', (tester) async {
    var expired = 0;
    final test = TestApi(
      (request) async =>
          errorResponse(401, 'authentication_failed', 'Token invalid.'),
      tokens: MemoryTokenStore(access: 'a', refresh: 'r'),
    );

    await pumpAnswered(tester, test, onSessionExpired: () => expired++);
    await tester.pumpAndSettle();

    expect(expired, 1);
  });

  testWidgets('pull to refresh reloads the list', (tester) async {
    var calls = 0;
    final test = TestApi((request) async {
      calls++;
      return jsonResponse(twoRows);
    });
    await pumpAnswered(tester, test);
    await tester.pumpAndSettle();

    await tester.fling(find.byType(ListView), const Offset(0, 300), 1000);
    await tester.pumpAndSettle();

    expect(calls, 2);
  });
}
