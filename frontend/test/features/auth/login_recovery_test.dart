import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/core/api/api_config.dart';
import 'package:smart_survey_app/features/auth/login_screen.dart';
import 'package:smart_survey_app/features/surveys/eligible_surveys_screen.dart';

import '../../support/test_api.dart';

const String _notConfirmed =
    'Confirm your email address first. Open the link we sent you, or send a '
    'new one.';

Future<void> pumpLogin(WidgetTester tester, TestApi test) async {
  await tester.pumpWidget(
    MaterialApp(
      home: LoginScreen(
        authRepository: test.auth,
        surveysRepository: test.surveys,
        profileRepository: test.profile,
        answerRepository: test.answers,
      ),
    ),
  );
}

void main() {
  testWidgets('a 403 email_not_confirmed shows the server message', (
    tester,
  ) async {
    final test = TestApi(
      (request) async =>
          errorResponse(403, 'email_not_confirmed', _notConfirmed),
    );
    await pumpLogin(tester, test);

    await tester.enterText(
      find.widgetWithText(TextFormField, 'Email'),
      'sara@example.com',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Password'),
      'secret-pass',
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Log in'));
    await tester.pumpAndSettle();

    expect(find.text(_notConfirmed), findsOneWidget);
    expect(find.byType(EligibleSurveysScreen), findsNothing);
    expect(test.tokens.refresh, isNull);
  });

  testWidgets('the reset address is shown as selectable text under Create '
      'account', (tester) async {
    final test = TestApi((request) async => jsonResponse({}));
    await pumpLogin(tester, test);

    final address = ApiConfig.baseUrl.resolve('/users/password-reset/');
    final line = find.text(
      'Forgot your password? Reset it on the website: $address',
    );

    expect(address.path, '/users/password-reset/');
    expect(line, findsOneWidget);
    expect(
      find.ancestor(of: line, matching: find.byType(SelectableText)),
      findsOneWidget,
    );
    expect(
      tester.getTopLeft(line).dy,
      greaterThan(
        tester
            .getBottomLeft(find.widgetWithText(TextButton, 'Create account'))
            .dy,
      ),
    );
  });
}
