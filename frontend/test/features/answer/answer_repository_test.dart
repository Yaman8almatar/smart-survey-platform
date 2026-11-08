import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:smart_survey_app/core/api/api_client.dart';
import 'package:smart_survey_app/core/api/api_exception.dart';
import 'package:smart_survey_app/core/api/token_store.dart';
import 'package:smart_survey_app/features/answer/answer_models.dart';
import 'package:smart_survey_app/features/answer/answer_repository.dart';
import 'package:smart_survey_app/features/answer/survey_sent_screen.dart';

import '../../support/test_api.dart';

/// Records the timeout a POST was given and answers 201.
class _RecordingApi extends ApiClient {
  _RecordingApi()
    : super(
        httpClient: MockClient((request) async => http.Response('', 500)),
        tokenStore: MemoryTokenStore(),
        baseUrl: testBaseUrl,
      );

  Duration? timeout;

  @override
  Future<Object?> post(
    String path, {
    Object? body,
    bool authenticated = true,
    Duration? timeout,
  }) async {
    this.timeout = timeout;
    return {'id': 1, 'survey_id': 1, 'submitted_at': '2026-11-08T14:42:00Z'};
  }
}

void main() {
  group('survey', () {
    test('parses the detail with questions in order_index order', () async {
      final test = TestApi(
        (request) async => jsonResponse({
          'id': 1,
          'title': 'Transport',
          'description': 'About buses',
          'questions': [
            {
              'id': 13,
              'text': 'Rate it',
              'type': 'RATING_SCALE',
              'is_required': true,
              'order_index': 3,
              'options': <Object>[],
              'rating_values': [1, 2, 3, 4, 5],
            },
            {
              'id': 11,
              'text': 'Which one?',
              'type': 'MULTIPLE_CHOICE',
              'is_required': true,
              'order_index': 1,
              'options': [
                {'id': 101, 'text': 'Bus'},
              ],
              'rating_values': <Object>[],
            },
            {
              'id': 12,
              'text': 'Anything else?',
              'type': 'OPEN_TEXT',
              'is_required': false,
              'order_index': 2,
              'options': <Object>[],
              'rating_values': <Object>[],
            },
          ],
        }),
      );

      final survey = await test.answers.survey(1);

      expect(survey.title, 'Transport');
      expect(survey.questions.map((q) => q.id), [11, 12, 13]);
      expect(survey.questions.map((q) => q.type), [
        QuestionType.choice,
        QuestionType.text,
        QuestionType.rating,
      ]);
      expect(survey.questions[0].options.single.text, 'Bus');
      expect(survey.questions[2].ratingValues, [1, 2, 3, 4, 5]);
      expect(survey.optionalCount, 1);
    });

    test('a body that breaks the contract is an unexpected response', () {
      final test = TestApi((request) async => jsonResponse({'id': 'one'}));

      expect(
        test.answers.survey(1),
        throwsA(
          isA<ApiException>().having(
            (e) => e.code,
            'code',
            ApiException.unexpectedResponseCode,
          ),
        ),
      );
    });

    test('an unknown question type is an unexpected response', () {
      final test = TestApi(
        (request) async => jsonResponse({
          'id': 1,
          'title': 'T',
          'description': '',
          'questions': [
            {
              'id': 1,
              'text': 'Q',
              'type': 'DRAWING',
              'is_required': true,
              'order_index': 1,
            },
          ],
        }),
      );

      expect(test.answers.survey(1), throwsA(isA<ApiException>()));
    });
  });

  group('submit', () {
    late http.Request captured;

    TestApi submitApi() => TestApi((request) async {
      captured = request;
      return jsonResponse({
        'id': 55,
        'survey_id': 1,
        'submitted_at': '2026-11-08T14:42:00Z',
      }, 201);
    });

    test('sends each answer type under its own key', () async {
      final test = submitApi();

      final result = await test.answers.submit(1, const {
        11: Answer.option(101),
        13: Answer.rating(4),
        12: Answer.text('Clear and quick.'),
      });

      expect(captured.method, 'POST');
      expect(captured.url.path, endsWith('surveys/1/responses/'));
      expect(jsonDecode(captured.body), {
        'answers': [
          {'question_id': 11, 'selected_option_id': 101},
          {'question_id': 13, 'rating_value': 4},
          {'question_id': 12, 'answer_value': 'Clear and quick.'},
        ],
      });
      expect(result.responseId, 55);
      expect(result.submittedAt, DateTime.utc(2026, 11, 8, 14, 42));
    });

    test('submit passes the 60 s timeout', () async {
      final api = _RecordingApi();

      await AnswerRepository(api: api).submit(1, const {});

      expect(api.timeout, const Duration(seconds: 60));
    });

    test('trims text and leaves out a blank one', () async {
      final test = submitApi();

      await test.answers.submit(1, const {
        12: Answer.text('  spaced  '),
        14: Answer.text('   '),
      });

      expect(jsonDecode(captured.body), {
        'answers': [
          {'question_id': 12, 'answer_value': 'spaced'},
        ],
      });
    });

    test('unanswered questions are left out', () async {
      final test = submitApi();

      await test.answers.submit(1, const {});

      expect(jsonDecode(captured.body), {'answers': <Object>[]});
    });

    test('passes on the API error', () {
      final test = TestApi(
        (request) async =>
            errorResponse(409, 'duplicate_response', 'Already answered.'),
      );

      expect(
        test.answers.submit(1, const {}),
        throwsA(
          isA<ApiException>().having(
            (e) => e.code,
            'code',
            'duplicate_response',
          ),
        ),
      );
    });
  });

  group('sentAtText', () {
    test('today', () {
      expect(
        sentAtText(DateTime(2026, 11, 8, 17, 42), DateTime(2026, 11, 8, 23)),
        'Sent today at 17:42.',
      );
    });

    test('another day names the month and pads the time', () {
      expect(
        sentAtText(DateTime(2026, 11, 7, 7, 5), DateTime(2026, 11, 8, 9)),
        'Sent on 7 November at 07:05.',
      );
    });
  });
}
