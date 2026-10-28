import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/app.dart';
import 'package:smart_survey_app/core/api/token_store.dart';
import 'package:smart_survey_app/features/auth/login_screen.dart';
import 'package:smart_survey_app/features/surveys/eligible_surveys_screen.dart';

import 'support/test_api.dart';

Future<void> pumpGate(WidgetTester tester, TestApi test) async {
  await tester.pumpWidget(
    MaterialApp(
      home: AuthGate(
        authRepository: test.auth,
        surveysRepository: test.surveys,
      ),
    ),
  );
}

void main() {
  testWidgets('no stored session opens login after a progress indicator', (
    tester,
  ) async {
    final test = TestApi((request) async => jsonResponse({}));

    await pumpGate(tester, test);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await tester.pumpAndSettle();
    expect(find.byType(LoginScreen), findsOneWidget);
  });

  testWidgets('a valid stored session opens the eligible list', (tester) async {
    final test = TestApi((request) async {
      return request.url.path.endsWith('me/')
          ? jsonResponse(respondentJson)
          : jsonResponse([]);
    }, tokens: MemoryTokenStore(access: 'a', refresh: 'r'));

    await pumpGate(tester, test);
    await tester.pumpAndSettle();

    expect(find.byType(EligibleSurveysScreen), findsOneWidget);
    expect(find.text('Sara'), findsOneWidget);
  });

  testWidgets('a stored session the server rejects opens login', (
    tester,
  ) async {
    final test = TestApi(
      (request) async =>
          errorResponse(401, 'authentication_failed', 'Token invalid.'),
      tokens: MemoryTokenStore(access: 'a', refresh: 'r'),
    );

    await pumpGate(tester, test);
    await tester.pumpAndSettle();

    expect(find.byType(LoginScreen), findsOneWidget);
    expect(test.tokens.refresh, isNull);
  });
}
