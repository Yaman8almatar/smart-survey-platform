import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:smart_survey_app/core/api/token_store.dart';
import 'package:smart_survey_app/features/answer/survey_answer_screen.dart';
import 'package:smart_survey_app/features/answer/survey_sent_screen.dart';
import 'package:smart_survey_app/features/answer/survey_start_screen.dart';
import 'package:smart_survey_app/features/auth/auth_models.dart';
import 'package:smart_survey_app/features/auth/login_screen.dart';
import 'package:smart_survey_app/features/surveys/eligible_surveys_screen.dart';
import 'package:smart_survey_app/theme/app_theme.dart';
import 'package:smart_survey_app/theme/tokens.dart';
import 'package:smart_survey_app/widgets/answer_option.dart';
import 'package:smart_survey_app/widgets/signal_ring.dart';

import '../../support/test_api.dart';

Map<String, Object> choiceQuestion({
  int id = 11,
  int order = 1,
  bool required = true,
}) => {
  'id': id,
  'text': 'Which kind of transport?',
  'type': 'MULTIPLE_CHOICE',
  'is_required': required,
  'order_index': order,
  'options': [
    {'id': 101, 'text': 'City bus'},
    {'id': 102, 'text': 'Taxi'},
  ],
  'rating_values': <int>[],
};

Map<String, Object> textQuestion({
  int id = 12,
  int order = 2,
  bool required = false,
}) => {
  'id': id,
  'text': 'Anything else?',
  'type': 'OPEN_TEXT',
  'is_required': required,
  'order_index': order,
  'options': <Object>[],
  'rating_values': <int>[],
};

Map<String, Object> ratingQuestion({int id = 13, int order = 3}) => {
  'id': id,
  'text': 'How clean are the vehicles?',
  'type': 'RATING_SCALE',
  'is_required': true,
  'order_index': order,
  'options': <Object>[],
  'rating_values': [1, 2, 3, 4, 5],
};

Map<String, Object> surveyJson(List<Map<String, Object>> questions) => {
  'id': 1,
  'title': 'Transport in Homs',
  'description': 'Tell us about buses.',
  'questions': questions,
};

final Map<String, Object> flowSurvey = surveyJson([
  choiceQuestion(),
  textQuestion(),
  ratingQuestion(),
]);

http.Response created() => jsonResponse({
  'id': 55,
  'survey_id': 1,
  'submitted_at': DateTime.now().toUtc().toIso8601String(),
}, 201);

/// The list, the survey and the send endpoint; counts list loads and keeps sent bodies.
class FlowApi {
  FlowApi({
    Map<String, Object>? survey,
    this.detail,
    Future<http.Response> Function()? submit,
    MemoryTokenStore? tokens,
  }) : survey = survey ?? flowSurvey,
       submit = submit ?? (() async => created()) {
    api = TestApi(_handle, tokens: tokens);
  }

  final Map<String, Object> survey;
  final Future<http.Response> Function()? detail;
  final Future<http.Response> Function() submit;
  late final TestApi api;
  int listLoads = 0;
  final List<Object?> sent = [];

  Future<http.Response> _handle(http.Request request) async {
    final path = request.url.path;
    if (path.endsWith('surveys/eligible/')) {
      listLoads++;
      return jsonResponse([
        {
          'id': 1,
          'title': 'Transport in Homs',
          'description': 'Tell us about buses.',
          'question_count': 3,
        },
      ]);
    }
    if (path.endsWith('auth/token/refresh/')) {
      return errorResponse(401, 'authentication_failed', 'Token invalid.');
    }
    if (path.endsWith('/responses/')) {
      sent.add(jsonDecode(request.body));
      return submit();
    }
    return detail == null ? jsonResponse(survey) : detail!();
  }
}

Future<void> pumpList(WidgetTester tester, FlowApi flow) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.light(),
      home: EligibleSurveysScreen(
        authRepository: flow.api.auth,
        surveysRepository: flow.api.surveys,
        profileRepository: flow.api.profile,
        answerRepository: flow.api.answers,
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
}

Future<void> tapText(WidgetTester tester, String text) async {
  await tester.tap(find.text(text));
  await tester.pumpAndSettle();
}

Future<void> openStart(WidgetTester tester, FlowApi flow) async {
  await pumpList(tester, flow);
  await tapText(tester, 'Transport in Homs');
}

Future<void> begin(WidgetTester tester, FlowApi flow) async {
  await openStart(tester, flow);
  await tapText(tester, 'Start survey');
}

/// Taxi, skip the optional text, rating 4, then the review.
Future<void> reachReview(WidgetTester tester, FlowApi flow) async {
  await begin(tester, flow);
  await tapText(tester, 'Taxi');
  await tapText(tester, 'Next');
  await tapText(tester, 'Skip');
  await tapText(tester, '4');
  await tapText(tester, 'Review answers');
}

bool isSelected(WidgetTester tester, String label) => tester
    .widget<AnswerOption>(find.widgetWithText(AnswerOption, label))
    .selected;

const _expectedBody = {
  'answers': [
    {'question_id': 11, 'selected_option_id': 102},
    {'question_id': 13, 'rating_value': 4},
  ],
};

void main() {
  group('list and start', () {
    testWidgets('the card opens the start screen, the list reloads on return', (
      tester,
    ) async {
      final flow = FlowApi();
      await openStart(tester, flow);

      expect(find.byType(SurveyStartScreen), findsOneWidget);
      expect(find.text('Before you start'), findsOneWidget);
      expect(find.text('Start survey'), findsOneWidget);
      expect(flow.listLoads, 1);

      await tester.pageBack();
      await tester.pumpAndSettle();

      expect(find.byType(EligibleSurveysScreen), findsOneWidget);
      expect(flow.listLoads, 2);
    });

    testWidgets('start counts questions and optional ones', (tester) async {
      final flow = FlowApi(
        survey: surveyJson([
          choiceQuestion(id: 1, order: 1),
          choiceQuestion(id: 2, order: 2),
          ratingQuestion(id: 3, order: 3),
          ratingQuestion(id: 4, order: 4),
          textQuestion(id: 5, order: 5, required: true),
          textQuestion(id: 6, order: 6),
        ]),
      );
      await openStart(tester, flow);

      expect(find.text('6 questions'), findsOneWidget);
      expect(find.text('1 optional'), findsOneWidget);
    });

    testWidgets('no optional count when every question is required', (
      tester,
    ) async {
      final flow = FlowApi(survey: surveyJson([choiceQuestion()]));
      await openStart(tester, flow);

      expect(find.text('1 question'), findsOneWidget);
      expect(find.textContaining('optional'), findsNothing);
    });

    testWidgets('shows progress while the detail loads', (tester) async {
      final gate = Completer<http.Response>();
      final flow = FlowApi(detail: () => gate.future);
      await pumpList(tester, flow);

      await tester.tap(find.text('Transport in Homs'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      gate.complete(jsonResponse(flowSurvey));
      await tester.pumpAndSettle();
      expect(find.text('Start survey'), findsOneWidget);
    });

    testWidgets('a network failure offers Try again, which reloads', (
      tester,
    ) async {
      var calls = 0;
      final flow = FlowApi(
        detail: () async {
          calls++;
          if (calls == 1) throw http.ClientException('down');
          return jsonResponse(flowSurvey);
        },
      );
      await openStart(tester, flow);

      expect(find.text('Could not load this survey'), findsOneWidget);
      expect(
        find.text(
          'Cannot reach the server. Check your connection and try again.',
        ),
        findsOneWidget,
      );

      await tapText(tester, 'Try again');

      expect(find.text('Start survey'), findsOneWidget);
    });

    final loadBlocks = <(int, String, String, String)>[
      (
        409,
        'not_editable',
        'This survey is closed',
        'It no longer takes answers.',
      ),
      (
        409,
        'duplicate_response',
        'You already answered this survey',
        'Each survey takes one response from you.',
      ),
      (
        403,
        'unauthorized_action',
        'This survey no longer matches your profile',
        'The survey or your profile changed after the list was loaded.',
      ),
      (
        404,
        'survey_not_found',
        'This survey is not available',
        'It may have been removed.',
      ),
    ];
    for (final (status, code, title, body) in loadBlocks) {
      testWidgets('$code while loading replaces the screen', (tester) async {
        final flow = FlowApi(
          detail: () async => errorResponse(status, code, 'API words.'),
        );
        await openStart(tester, flow);

        expect(find.text(title), findsOneWidget);
        expect(find.text(body), findsOneWidget);
        expect(find.text('Start survey'), findsNothing);

        await tapText(tester, 'Back to surveys');
        expect(find.byType(EligibleSurveysScreen), findsOneWidget);
      });
    }

    testWidgets('an ended session opens login with the notice', (tester) async {
      final flow = FlowApi(
        detail: () async =>
            errorResponse(401, 'authentication_failed', 'Token invalid.'),
        tokens: MemoryTokenStore(access: 'a', refresh: 'r'),
      );
      await openStart(tester, flow);

      expect(find.byType(LoginScreen), findsOneWidget);
      expect(
        find.text('Your session ended. Please log in again.'),
        findsOneWidget,
      );
      expect(find.byType(SurveyStartScreen), findsNothing);
    });
  });

  group('questions', () {
    testWidgets('the first question shows Next only', (tester) async {
      await begin(tester, FlowApi());

      expect(find.text('Question 1 of 3'), findsOneWidget);
      expect(find.text('1/3'), findsOneWidget);
      expect(find.text('Choose one.'), findsOneWidget);
      expect(find.text('Next'), findsOneWidget);
      expect(find.text('Back'), findsNothing);
    });

    testWidgets('Next without a required answer shows the error and stays', (
      tester,
    ) async {
      await begin(tester, FlowApi());

      await tapText(tester, 'Next');

      expect(find.text('Choose an answer to continue.'), findsOneWidget);
      expect(find.text('Question 1 of 3'), findsOneWidget);
      expect(
        tester
            .widget<AnswerOption>(find.widgetWithText(AnswerOption, 'Taxi'))
            .error,
        isTrue,
      );

      await tapText(tester, 'Taxi');
      expect(find.text('Choose an answer to continue.'), findsNothing);
    });

    testWidgets('a required text of spaces counts as no answer', (
      tester,
    ) async {
      final flow = FlowApi(
        survey: surveyJson([
          textQuestion(required: true),
          choiceQuestion(order: 3),
        ]),
      );
      await begin(tester, flow);

      await tester.enterText(find.byType(TextField), '   ');
      await tester.pump();
      await tapText(tester, 'Next');

      expect(find.text('Write an answer to continue.'), findsOneWidget);
      expect(find.text('Question 1 of 2'), findsOneWidget);
    });

    testWidgets('Skip on an optional question moves on', (tester) async {
      await begin(tester, FlowApi());
      await tapText(tester, 'Taxi');
      await tapText(tester, 'Next');

      expect(find.text('Optional'), findsOneWidget);
      expect(find.text('Next'), findsNothing);

      await tapText(tester, 'Skip');

      expect(find.text('Question 3 of 3'), findsOneWidget);
    });

    testWidgets('typing on an optional question turns Skip into Next', (
      tester,
    ) async {
      await begin(tester, FlowApi());
      await tapText(tester, 'Taxi');
      await tapText(tester, 'Next');

      await tester.enterText(find.byType(TextField), 'More buses');
      await tester.pump();

      expect(find.text('Skip'), findsNothing);
      expect(find.text('Next'), findsOneWidget);
    });

    testWidgets('Back keeps the answer', (tester) async {
      await begin(tester, FlowApi());
      await tapText(tester, 'Taxi');
      await tapText(tester, 'Next');

      await tapText(tester, 'Back');

      expect(find.text('Question 1 of 3'), findsOneWidget);
      expect(isSelected(tester, 'Taxi'), isTrue);
      expect(isSelected(tester, 'City bus'), isFalse);
    });

    testWidgets('Back keeps typed text', (tester) async {
      await begin(tester, FlowApi());
      await tapText(tester, 'Taxi');
      await tapText(tester, 'Next');
      await tester.enterText(find.byType(TextField), 'More buses');
      await tester.pump();
      await tapText(tester, 'Next');

      await tapText(tester, 'Back');

      expect(find.text('More buses'), findsOneWidget);
    });

    testWidgets('the last question shows Review answers', (tester) async {
      await begin(tester, FlowApi());
      await tapText(tester, 'Taxi');
      await tapText(tester, 'Next');
      await tapText(tester, 'Skip');

      expect(find.text('Review answers'), findsOneWidget);
      expect(find.text('Next'), findsNothing);
      expect(find.text('1 is the lowest, 5 the highest.'), findsOneWidget);
    });

    testWidgets('an optional empty last question still shows Review answers', (
      tester,
    ) async {
      final flow = FlowApi(
        survey: surveyJson([choiceQuestion(), textQuestion()]),
      );
      await begin(tester, flow);
      await tapText(tester, 'Taxi');
      await tapText(tester, 'Next');

      expect(find.text('Review answers'), findsOneWidget);
      expect(find.text('Skip'), findsNothing);
    });

    testWidgets('the open text is right to left for Arabic', (tester) async {
      await begin(tester, FlowApi());
      await tapText(tester, 'Taxi');
      await tapText(tester, 'Next');

      await tester.enterText(find.byType(TextField), 'الخدمة جيدة');
      await tester.pump();

      expect(
        tester.widget<TextField>(find.byType(TextField)).textDirection,
        TextDirection.rtl,
      );
    });

    testWidgets('with animations disabled a question changes at once', (
      tester,
    ) async {
      final flow = FlowApi();
      await tester.pumpWidget(
        MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: MaterialApp(
            theme: AppTheme.light(),
            home: SurveyAnswerScreen(
              answerRepository: flow.api.answers,
              survey: await flow.api.answers.survey(1),
              onSessionExpired: () {},
            ),
          ),
        ),
      );
      await tester.pump();
      await tester.tap(find.text('Taxi'));
      await tester.pump();
      await tester.tap(find.text('Next'));
      await tester.pump();
      await tester.pump();

      expect(find.text('Question 2 of 3'), findsOneWidget);
      expect(find.text('Question 1 of 3'), findsNothing);
    });
  });

  group('app-bar ring', () {
    testWidgets('the last question ring has no ping', (tester) async {
      await begin(tester, FlowApi());
      await tapText(tester, 'Taxi');
      await tapText(tester, 'Next');

      await tester.tap(find.text('Skip'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 600));
      await tester.pump();

      expect(find.text('3/3'), findsOneWidget);
      expect(find.byKey(const ValueKey('signal-ring-ping')), findsNothing);
      await tester.pumpAndSettle();
    });

    testWidgets('the review ring has no ping, the sent ring keeps it', (
      tester,
    ) async {
      await reachReview(tester, FlowApi());

      expect(tester.widget<SignalRing>(find.byType(SignalRing)).ping, isFalse);

      await tapText(tester, 'Send answers');

      expect(tester.widget<SignalRing>(find.byType(SignalRing)).ping, isTrue);
    });

    testWidgets('the ring sits 16 px from the screen edge', (tester) async {
      await begin(tester, FlowApi());

      final bar = tester.getTopRight(find.byType(AppBar)).dx;
      final ring = tester.getTopRight(find.byType(SignalRing)).dx;

      expect(bar - ring, SsSpace.s4);
    });
  });

  group('leaving', () {
    testWidgets('leaves at once with no answer', (tester) async {
      await begin(tester, FlowApi());

      await tester.tap(find.byTooltip('Leave survey'));
      await tester.pumpAndSettle();

      expect(find.text('Leave this survey?'), findsNothing);
      expect(find.byType(SurveyStartScreen), findsOneWidget);
      expect(find.byType(SurveyAnswerScreen), findsNothing);
    });

    testWidgets('asks after an answer; Keep answering stays', (tester) async {
      await begin(tester, FlowApi());
      await tapText(tester, 'Taxi');

      await tester.tap(find.byTooltip('Leave survey'));
      await tester.pumpAndSettle();

      expect(find.text('Leave this survey?'), findsOneWidget);
      expect(
        find.text('Your answers so far will not be kept.'),
        findsOneWidget,
      );

      await tapText(tester, 'Keep answering');

      expect(find.byType(SurveyAnswerScreen), findsOneWidget);
      expect(isSelected(tester, 'Taxi'), isTrue);
    });

    testWidgets('Leave closes the answer screen', (tester) async {
      await begin(tester, FlowApi());
      await tapText(tester, 'Taxi');
      await tester.tap(find.byTooltip('Leave survey'));
      await tester.pumpAndSettle();

      await tapText(tester, 'Leave');

      expect(find.byType(SurveyAnswerScreen), findsNothing);
      expect(find.byType(SurveyStartScreen), findsOneWidget);
    });

    testWidgets('the system back on the review asks too', (tester) async {
      await reachReview(tester, FlowApi());

      final handled = await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();

      expect(handled, isTrue);
      expect(find.text('Leave this survey?'), findsOneWidget);
    });
  });

  group('review', () {
    testWidgets('shows the answers and Skipped', (tester) async {
      await reachReview(tester, FlowApi());

      expect(find.text('Check your answers'), findsOneWidget);
      expect(find.text('3/3'), findsOneWidget);
      expect(
        find.text('Transport in Homs. Tap an answer to change it.'),
        findsOneWidget,
      );
      expect(find.text('Taxi'), findsOneWidget);
      expect(find.text('Skipped'), findsOneWidget);
      expect(find.text('Anything else? Optional'), findsOneWidget);
      expect(find.text('4 out of 5'), findsOneWidget);
    });

    testWidgets('a text answer shows in its own direction', (tester) async {
      await begin(tester, FlowApi());
      await tapText(tester, 'Taxi');
      await tapText(tester, 'Next');
      await tester.enterText(find.byType(TextField), '  الخدمة جيدة ');
      await tester.pump();
      await tapText(tester, 'Next');
      await tapText(tester, '4');
      await tapText(tester, 'Review answers');

      expect(
        tester.widget<Text>(find.text('الخدمة جيدة')).textDirection,
        TextDirection.rtl,
      );
    });

    testWidgets('a row opens its question with Back to review', (tester) async {
      await reachReview(tester, FlowApi());

      await tapText(tester, 'Taxi');

      expect(find.text('Question 1 of 3'), findsOneWidget);
      expect(find.text('Back to review'), findsOneWidget);

      await tapText(tester, 'City bus');
      await tapText(tester, 'Back to review');

      expect(find.text('Check your answers'), findsOneWidget);
      expect(find.text('City bus'), findsOneWidget);
      expect(find.text('Taxi'), findsNothing);
    });

    testWidgets('an optional row opened empty still offers Back to review', (
      tester,
    ) async {
      await reachReview(tester, FlowApi());

      await tapText(tester, 'Skipped');

      expect(find.text('Back to review'), findsOneWidget);
      expect(find.text('Skip'), findsNothing);
    });

    testWidgets('app bar back returns to the last question', (tester) async {
      await reachReview(tester, FlowApi());

      await tester.tap(find.byTooltip('Back'));
      await tester.pumpAndSettle();

      expect(find.text('Question 3 of 3'), findsOneWidget);
      expect(find.text('Review answers'), findsOneWidget);
    });
  });

  group('sending', () {
    testWidgets('Send posts the body and shows Answers sent', (tester) async {
      final flow = FlowApi();
      await reachReview(tester, flow);

      await tapText(tester, 'Send answers');

      expect(flow.sent.single, _expectedBody);
      expect(find.byType(SurveySentScreen), findsOneWidget);
      expect(find.byType(SurveyAnswerScreen), findsNothing);
      expect(find.text('Answers sent'), findsOneWidget);
      expect(find.text('2 of 3 questions answered'), findsOneWidget);
      expect(find.textContaining('Sent today at'), findsOneWidget);
    });

    testWidgets('Back to surveys returns to a reloaded list', (tester) async {
      final flow = FlowApi();
      await reachReview(tester, flow);
      await tapText(tester, 'Send answers');
      final loadsBefore = flow.listLoads;

      await tapText(tester, 'Back to surveys');

      expect(find.byType(EligibleSurveysScreen), findsOneWidget);
      expect(flow.listLoads, loadsBefore + 1);
    });

    testWidgets('while sending: one request, disabled rows, no leaving', (
      tester,
    ) async {
      final gate = Completer<http.Response>();
      final flow = FlowApi(submit: () => gate.future);
      await reachReview(tester, flow);

      await tester.tap(find.text('Send answers'));
      await tester.pump();

      expect(find.text('Sending…'), findsOneWidget);
      expect(
        find.text('Sending your answers. This can take a few seconds.'),
        findsOneWidget,
      );

      await tester.tap(find.text('Sending…'));
      await tester.pump();
      expect(flow.sent, hasLength(1));

      await tester.tap(find.text('Taxi'));
      await tester.pump();
      expect(find.text('Check your answers'), findsOneWidget);

      await tester.tap(find.byTooltip('Back'));
      await tester.pump();
      expect(find.text('Check your answers'), findsOneWidget);

      await tester.binding.handlePopRoute();
      await tester.pump();
      expect(find.text('Leave this survey?'), findsNothing);
      expect(find.byType(SurveyAnswerScreen), findsOneWidget);

      gate.complete(created());
      await tester.pumpAndSettle();
      expect(find.text('Answers sent'), findsOneWidget);
    });

    testWidgets('a network failure shows the snackbar and keeps the answers', (
      tester,
    ) async {
      var calls = 0;
      final flow = FlowApi(
        submit: () async {
          calls++;
          if (calls == 1) throw http.ClientException('down');
          return created();
        },
      );
      await reachReview(tester, flow);

      await tapText(tester, 'Send answers');

      expect(find.text('Not sent. Cannot reach the server.'), findsOneWidget);
      expect(find.text('Check your answers'), findsOneWidget);
      expect(find.text('Taxi'), findsOneWidget);
      expect(find.text('4 out of 5'), findsOneWidget);

      await tapText(tester, 'Try again');

      expect(find.text('Answers sent'), findsOneWidget);
      expect(flow.sent.last, _expectedBody);
    });

    testWidgets('409 duplicate_response shows its message', (tester) async {
      final flow = FlowApi(
        submit: () async =>
            errorResponse(409, 'duplicate_response', 'Already.'),
      );
      await reachReview(tester, flow);

      await tapText(tester, 'Send answers');

      expect(find.text('You already answered this survey'), findsOneWidget);
      expect(
        find.text('Each survey takes one response from you.'),
        findsOneWidget,
      );
      expect(find.text('Send answers'), findsNothing);
      expect(find.text('Answers sent'), findsNothing);

      await tapText(tester, 'Back to surveys');
      expect(find.byType(EligibleSurveysScreen), findsOneWidget);
    });

    testWidgets('a network failure then 409 on Try again counts as sent', (
      tester,
    ) async {
      var calls = 0;
      final flow = FlowApi(
        submit: () async {
          calls++;
          if (calls == 1) throw http.ClientException('timed out');
          return errorResponse(409, 'duplicate_response', 'Already.');
        },
      );
      await reachReview(tester, flow);

      await tapText(tester, 'Send answers');
      await tapText(tester, 'Try again');

      expect(find.text('Answers sent'), findsOneWidget);
      expect(find.textContaining('Sent today at'), findsOneWidget);
      expect(find.text('You already answered this survey'), findsNothing);
    });

    testWidgets('409 not_editable while sending says so', (tester) async {
      final flow = FlowApi(
        submit: () async => errorResponse(409, 'not_editable', 'Closed.'),
      );
      await reachReview(tester, flow);

      await tapText(tester, 'Send answers');

      expect(find.text('This survey is closed'), findsOneWidget);
      expect(
        find.text(
          'It stopped taking answers before yours arrived, so they were '
          'not saved.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('400 marks the answer named by its position', (tester) async {
      final flow = FlowApi(
        submit: () async => jsonResponse({
          'error': {
            'code': 'validation_error',
            'message': 'Invalid input.',
            'fields': {
              'answers': [
                <String, Object>{},
                {
                  'rating_value': ['Bad value.'],
                },
              ],
            },
          },
        }, 400),
      );
      await reachReview(tester, flow);

      await tapText(tester, 'Send answers');

      expect(find.text('Needs an answer'), findsOneWidget);
      expect(find.text('4 out of 5'), findsNothing);
      expect(find.text('Taxi'), findsOneWidget);
      expect(find.text('Fix the marked answer, then send.'), findsOneWidget);
    });

    testWidgets('400 naming no question shows the API message', (tester) async {
      final flow = FlowApi(
        submit: () async => errorResponse(
          400,
          'validation_error',
          'Required questions must have answers.',
        ),
      );
      await reachReview(tester, flow);

      await tapText(tester, 'Send answers');

      expect(
        find.text('Required questions must have answers.'),
        findsOneWidget,
      );
      expect(find.text('Needs an answer'), findsNothing);
      expect(find.text('Send answers'), findsOneWidget);
    });

    testWidgets('an ended session while sending opens login', (tester) async {
      final flow = FlowApi(
        submit: () async =>
            errorResponse(401, 'authentication_failed', 'Token invalid.'),
        tokens: MemoryTokenStore(access: 'a', refresh: 'r'),
      );
      await reachReview(tester, flow);

      await tapText(tester, 'Send answers');

      expect(find.byType(LoginScreen), findsOneWidget);
      expect(
        find.text('Your session ended. Please log in again.'),
        findsOneWidget,
      );
    });
  });
}
