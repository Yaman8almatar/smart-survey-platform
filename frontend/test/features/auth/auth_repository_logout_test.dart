import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:smart_survey_app/core/api/token_store.dart';

import '../../support/test_api.dart';

MemoryTokenStore signedIn() =>
    MemoryTokenStore(access: 'access-1', refresh: 'refresh-1');

void main() {
  test(
    'logout sends the stored refresh token and clears both tokens',
    () async {
      final requests = <http.Request>[];
      final test = TestApi((request) async {
        requests.add(request);
        return http.Response('', 204);
      }, tokens: signedIn());

      await test.auth.logout();

      expect(requests, hasLength(1));
      final request = requests.single;
      expect(request.method, 'POST');
      expect(request.url, testBaseUrl.resolve('auth/logout/'));
      expect(jsonDecode(request.body), {'refresh': 'refresh-1'});
      expect(request.headers.containsKey('Authorization'), isFalse);
      expect(test.tokens.access, isNull);
      expect(test.tokens.refresh, isNull);
    },
  );

  test('a 400 from the server still clears both tokens', () async {
    final test = TestApi(
      (request) async =>
          errorResponse(400, 'invalid_token', 'Token is blacklisted.'),
      tokens: signedIn(),
    );

    await test.auth.logout();

    expect(test.tokens.access, isNull);
    expect(test.tokens.refresh, isNull);
  });

  test('a network failure still clears both tokens', () async {
    final test = TestApi(
      (request) async => throw http.ClientException('offline'),
      tokens: signedIn(),
    );

    await test.auth.logout();

    expect(test.tokens.access, isNull);
    expect(test.tokens.refresh, isNull);
  });

  test('with no refresh token stored, no request is sent', () async {
    var requests = 0;
    final test = TestApi((request) async {
      requests++;
      return http.Response('', 204);
    }, tokens: MemoryTokenStore(access: 'access-1'));

    await test.auth.logout();

    expect(requests, 0);
    expect(test.tokens.access, isNull);
    expect(test.tokens.refresh, isNull);
  });
}
