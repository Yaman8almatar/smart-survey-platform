import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:smart_survey_app/core/api/api_exception.dart';
import 'package:smart_survey_app/core/api/token_store.dart';

import '../../support/test_api.dart';

void main() {
  test('adds the Bearer header when an access token exists', () async {
    String? seen;
    final test = TestApi((request) async {
      seen = request.headers['Authorization'];
      return jsonResponse(respondentJson);
    }, tokens: MemoryTokenStore(access: 'abc', refresh: 'ref'));

    await test.api.get('me/');

    expect(seen, 'Bearer abc');
  });

  test('sends no Authorization header without a token', () async {
    String? seen = 'unset';
    final test = TestApi((request) async {
      seen = request.headers['Authorization'];
      return jsonResponse({});
    });

    await test.api.get('surveys/eligible/');

    expect(seen, isNull);
  });

  test('401 -> refresh -> retry succeeds with the new token', () async {
    final calls = <String>[];
    final test = TestApi((request) async {
      calls.add('${request.method} ${request.url.path}');
      if (request.url.path.endsWith('auth/token/refresh/')) {
        return jsonResponse({'access': 'new'});
      }
      return request.headers['Authorization'] == 'Bearer new'
          ? jsonResponse(respondentJson)
          : errorResponse(401, 'authentication_failed', 'Token expired.');
    }, tokens: MemoryTokenStore(access: 'old', refresh: 'ref'));

    final json = await test.api.get('me/');

    expect(json, respondentJson);
    expect(test.tokens.access, 'new');
    expect(test.tokens.refresh, 'ref');
    expect(calls, [
      'GET /api/v1/me/',
      'POST /api/v1/auth/token/refresh/',
      'GET /api/v1/me/',
    ]);
  });

  test('two parallel 401s trigger exactly one refresh call', () async {
    var refreshCalls = 0;
    final test = TestApi((request) async {
      if (request.url.path.endsWith('auth/token/refresh/')) {
        refreshCalls++;
        await Future<void>.delayed(const Duration(milliseconds: 20));
        return jsonResponse({'access': 'new'});
      }
      return request.headers['Authorization'] == 'Bearer new'
          ? jsonResponse(respondentJson)
          : errorResponse(401, 'authentication_failed', 'Token expired.');
    }, tokens: MemoryTokenStore(access: 'old', refresh: 'ref'));

    final results = await Future.wait([
      test.api.get('me/'),
      test.api.get('surveys/eligible/'),
    ]);

    expect(refreshCalls, 1);
    expect(results, everyElement(respondentJson));
  });

  test('failed refresh clears the tokens and throws SessionExpired', () async {
    final test = TestApi((request) async {
      if (request.url.path.endsWith('auth/token/refresh/')) {
        return errorResponse(401, 'authentication_failed', 'Token invalid.');
      }
      return errorResponse(401, 'authentication_failed', 'Token expired.');
    }, tokens: MemoryTokenStore(access: 'old', refresh: 'ref'));

    await expectLater(
      test.api.get('me/'),
      throwsA(isA<SessionExpiredException>()),
    );

    expect(test.tokens.access, isNull);
    expect(test.tokens.refresh, isNull);
  });

  test('a 401 from an unauthenticated call is not refreshed', () async {
    var refreshCalls = 0;
    final test = TestApi((request) async {
      if (request.url.path.endsWith('auth/token/refresh/')) refreshCalls++;
      return errorResponse(401, 'invalid_credentials', 'Bad login.');
    }, tokens: MemoryTokenStore(refresh: 'ref'));

    await expectLater(
      test.api.post('auth/token/', body: {'email': 'a'}, authenticated: false),
      throwsA(
        isA<ApiException>().having(
          (e) => e.code,
          'code',
          'invalid_credentials',
        ),
      ),
    );
    expect(refreshCalls, 0);
  });

  test('parses the error shape including fields', () async {
    final test = TestApi(
      (request) async => errorResponse(
        400,
        'validation_error',
        'Invalid input.',
        fields: {
          'email': ['Already registered.'],
        },
      ),
    );

    await expectLater(
      test.api.post('auth/register/', body: {}, authenticated: false),
      throwsA(
        isA<ApiException>()
            .having((e) => e.statusCode, 'statusCode', 400)
            .having((e) => e.code, 'code', 'validation_error')
            .having((e) => e.message, 'message', 'Invalid input.')
            .having((e) => e.fields['email'], 'fields', [
              'Already registered.',
            ]),
      ),
    );
  });

  test('an HTML body becomes unexpected_response', () async {
    final test = TestApi(
      (request) async => http.Response('<html>Not Found</html>', 404),
    );

    await expectLater(
      test.api.get('nope/'),
      throwsA(
        isA<ApiException>()
            .having((e) => e.code, 'code', 'unexpected_response')
            .having((e) => e.statusCode, 'statusCode', 404),
      ),
    );
  });

  test('a connection failure becomes network_error', () async {
    final test = TestApi((request) async => throw http.ClientException('down'));

    await expectLater(
      test.api.get('me/'),
      throwsA(
        isA<ApiException>()
            .having((e) => e.code, 'code', 'network_error')
            .having((e) => e.message, 'message', isNot(contains('down'))),
      ),
    );
  });
}
