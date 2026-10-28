import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'app.dart';
import 'core/api/api_client.dart';
import 'core/api/api_config.dart';
import 'core/api/token_store.dart';
import 'features/auth/auth_repository.dart';
import 'features/surveys/surveys_repository.dart';

void main() {
  final tokens = SecureTokenStore();
  final api = ApiClient(
    httpClient: http.Client(),
    tokenStore: tokens,
    baseUrl: ApiConfig.baseUrl,
  );

  runApp(
    SmartSurveyApp(
      authRepository: AuthRepository(api: api, tokens: tokens),
      surveysRepository: SurveysRepository(api: api),
    ),
  );
}
