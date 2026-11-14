import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/core/api/api_exception.dart';

import '../../support/test_api.dart';

Matcher get throwsUnexpected => throwsA(
  isA<ApiException>()
      .having((e) => e.code, 'code', ApiException.unexpectedResponseCode)
      .having((e) => e.statusCode, 'statusCode', 200),
);

void main() {
  group('answeredSurveys', () {
    test(
      'parses rows in server order; a null description becomes ""',
      () async {
        final test = TestApi((request) async {
          expect(request.method, 'GET');
          expect(request.url.path, endsWith('/api/v1/me/responses/'));
          return jsonResponse([
            {
              'survey_id': 4,
              'title': 'Newer',
              'description': 'Second survey',
              'submitted_at': '2026-11-10T17:42:00Z',
            },
            {
              'survey_id': 1,
              'title': 'Older',
              'description': null,
              'submitted_at': '2025-11-07T09:05:00Z',
            },
          ]);
        });

        final rows = await test.surveys.answeredSurveys();

        expect([for (final r in rows) r.surveyId], [4, 1]);
        expect(rows[0].title, 'Newer');
        expect(rows[0].description, 'Second survey');
        expect(rows[0].submittedAt, DateTime.utc(2026, 11, 10, 17, 42));
        expect(rows[1].description, '');
      },
    );

    test('a body that is not a list is unexpected', () {
      final test = TestApi((request) async => jsonResponse({'results': []}));

      expect(test.surveys.answeredSurveys(), throwsUnexpected);
    });

    test('a bad submitted_at is unexpected', () {
      final test = TestApi(
        (request) async => jsonResponse([
          {
            'survey_id': 1,
            'title': 'Older',
            'description': '',
            'submitted_at': 'yesterday',
          },
        ]),
      );

      expect(test.surveys.answeredSurveys(), throwsUnexpected);
    });
  });
}
