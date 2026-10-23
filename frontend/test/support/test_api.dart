import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:smart_survey_app/core/api/api_client.dart';
import 'package:smart_survey_app/core/api/token_store.dart';
import 'package:smart_survey_app/features/auth/auth_repository.dart';
import 'package:smart_survey_app/features/surveys/surveys_repository.dart';

final Uri testBaseUrl = Uri.parse('https://api.test/api/v1/');

http.Response jsonResponse(Object? body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);

http.Response errorResponse(
  int status,
  String code,
  String message, {
  Map<String, List<String>>? fields,
}) => jsonResponse({
  'error': {'code': code, 'message': message, 'fields': ?fields},
}, status);

const Map<String, Object> respondentJson = {
  'id': 7,
  'email': 'sara@example.com',
  'name': 'Sara',
  'role': 'RESPONDENT',
};

/// Real client and repositories over a fake HTTP handler; no network.
class TestApi {
  TestApi(
    Future<http.Response> Function(http.Request request) handler, {
    MemoryTokenStore? tokens,
  }) : tokens = tokens ?? MemoryTokenStore() {
    api = ApiClient(
      httpClient: MockClient(handler),
      tokenStore: this.tokens,
      baseUrl: testBaseUrl,
    );
    auth = AuthRepository(api: api, tokens: this.tokens);
    surveys = SurveysRepository(api: api);
  }

  final MemoryTokenStore tokens;
  late final ApiClient api;
  late final AuthRepository auth;
  late final SurveysRepository surveys;
}
