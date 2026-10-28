import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:smart_survey_app/features/auth/login_screen.dart';
import 'package:smart_survey_app/features/surveys/eligible_surveys_screen.dart';

import '../../support/test_api.dart';

Future<void> pumpLogin(WidgetTester tester, TestApi test) async {
  await tester.pumpWidget(
    MaterialApp(
      home: LoginScreen(
        authRepository: test.auth,
        surveysRepository: test.surveys,
      ),
    ),
  );
}

Future<void> fillAndSubmit(
  WidgetTester tester, {
  String email = 'sara@example.com',
  String password = 'secret-pass',
}) async {
  await tester.enterText(find.widgetWithText(TextFormField, 'Email'), email);
  await tester.enterText(
    find.widgetWithText(TextFormField, 'Password'),
    password,
  );
  await tester.tap(find.widgetWithText(FilledButton, 'Log in'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('empty fields are blocked without calling the API', (
    tester,
  ) async {
    var requests = 0;
    final test = TestApi((request) async {
      requests++;
      return jsonResponse({});
    });
    await pumpLogin(tester, test);

    await tester.tap(find.widgetWithText(FilledButton, 'Log in'));
    await tester.pump();

    expect(find.text('Enter your email.'), findsOneWidget);
    expect(find.text('Enter your password.'), findsOneWidget);
    expect(requests, 0);
  });

  testWidgets('a badly shaped email is blocked', (tester) async {
    final test = TestApi((request) async => jsonResponse({}));
    await pumpLogin(tester, test);

    await fillAndSubmit(tester, email: 'not-an-email');

    expect(find.text('Enter a valid email address.'), findsOneWidget);
  });

  testWidgets('wrong password shows the credentials message', (tester) async {
    final test = TestApi(
      (request) async =>
          errorResponse(401, 'invalid_credentials', 'No active account.'),
    );
    await pumpLogin(tester, test);

    await fillAndSubmit(tester);

    expect(find.text('Email or password is incorrect.'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Log in'), findsOneWidget);
  });

  testWidgets('an unreachable server shows the network message', (
    tester,
  ) async {
    final test = TestApi((request) async => throw http.ClientException('down'));
    await pumpLogin(tester, test);

    await fillAndSubmit(tester);

    expect(
      find.text('Cannot reach the server. Is it running?'),
      findsOneWidget,
    );
  });

  testWidgets('server field errors appear under the matching field', (
    tester,
  ) async {
    final test = TestApi(
      (request) async => errorResponse(
        400,
        'validation_error',
        'Invalid input.',
        fields: {
          'email': ['Enter a valid email address.'],
        },
      ),
    );
    await pumpLogin(tester, test);

    await fillAndSubmit(tester);

    expect(find.text('Enter a valid email address.'), findsOneWidget);
    expect(find.text('Invalid input.'), findsNothing);
  });

  testWidgets('a provider account gets the respondent-only message', (
    tester,
  ) async {
    final test = TestApi((request) async {
      if (request.url.path.endsWith('auth/token/')) {
        return jsonResponse({'access': 'a', 'refresh': 'r'});
      }
      return errorResponse(403, 'permission_denied', 'Not allowed.');
    });
    await pumpLogin(tester, test);

    await fillAndSubmit(tester);

    expect(
      find.text(
        'This app is for respondents. Providers and admins use the website.',
      ),
      findsOneWidget,
    );
    expect(test.tokens.access, isNull);
    expect(test.tokens.refresh, isNull);
  });

  testWidgets('success stores tokens and opens the eligible list', (
    tester,
  ) async {
    final test = TestApi((request) async {
      if (request.url.path.endsWith('auth/token/')) {
        return jsonResponse({'access': 'a', 'refresh': 'r'});
      }
      if (request.url.path.endsWith('me/')) {
        return jsonResponse(respondentJson);
      }
      return jsonResponse([]);
    });
    await pumpLogin(tester, test);

    await fillAndSubmit(tester);

    expect(find.byType(EligibleSurveysScreen), findsOneWidget);
    expect(find.text('Sara'), findsOneWidget);
    expect(test.tokens.refresh, 'r');
  });

  testWidgets('the password toggle switches visibility', (tester) async {
    final test = TestApi((request) async => jsonResponse({}));
    await pumpLogin(tester, test);

    expect(find.byTooltip('Show password'), findsOneWidget);
    await tester.tap(find.byTooltip('Show password'));
    await tester.pump();

    expect(find.byTooltip('Hide password'), findsOneWidget);
  });
}
