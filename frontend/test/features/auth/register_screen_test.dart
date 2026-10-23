import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:smart_survey_app/features/auth/login_screen.dart';
import 'package:smart_survey_app/features/auth/register_screen.dart';
import 'package:smart_survey_app/features/surveys/eligible_surveys_screen.dart';

import '../../support/test_api.dart';

Future<void> pumpRegister(WidgetTester tester, TestApi test) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      home: RegisterScreen(
        authRepository: test.auth,
        surveysRepository: test.surveys,
      ),
    ),
  );
}

Future<void> fill(WidgetTester tester, String label, String text) =>
    tester.enterText(find.widgetWithText(TextFormField, label), text);

Future<void> fillAll(
  WidgetTester tester, {
  String age = '24',
  bool pickGender = true,
}) async {
  await fill(tester, 'Name', 'Sara');
  await fill(tester, 'Email', 'sara@example.com');
  await fill(tester, 'Password', 'secret-pass');
  await fill(tester, 'Age', age);
  await fill(tester, 'Region', 'Amman');
  await fill(tester, 'Interests', 'sports');
  if (pickGender) {
    await tester.tap(find.text('Female'));
    await tester.pump();
  }
}

Future<void> submit(WidgetTester tester) async {
  await tester.tap(find.widgetWithText(FilledButton, 'Create account'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('empty form is blocked without calling the API', (tester) async {
    var requests = 0;
    final test = TestApi((request) async {
      requests++;
      return jsonResponse({});
    });
    await pumpRegister(tester, test);

    await submit(tester);

    expect(find.text('Enter your name.'), findsOneWidget);
    expect(find.text('Enter your email.'), findsOneWidget);
    expect(find.text('Enter a password.'), findsOneWidget);
    expect(find.text('Enter an age from 1 to 120.'), findsOneWidget);
    expect(find.text('Choose a gender.'), findsOneWidget);
    expect(find.text('Enter your region.'), findsOneWidget);
    expect(find.text('Enter at least one interest.'), findsOneWidget);
    expect(requests, 0);
  });

  testWidgets('age outside 1 to 120 is blocked', (tester) async {
    final test = TestApi((request) async => jsonResponse({}));
    await pumpRegister(tester, test);
    await fillAll(tester, age: '121');

    await submit(tester);

    expect(find.text('Enter an age from 1 to 120.'), findsOneWidget);
    expect(find.text('Choose a gender.'), findsNothing);
  });

  testWidgets('a server field error appears under the matching field', (
    tester,
  ) async {
    final test = TestApi(
      (request) async => errorResponse(
        400,
        'validation_error',
        'Invalid input.',
        fields: {
          'email': ['A user with this email already exists.'],
        },
      ),
    );
    await pumpRegister(tester, test);
    await fillAll(tester);

    await submit(tester);

    expect(find.text('A user with this email already exists.'), findsOneWidget);
    expect(find.text('Invalid input.'), findsNothing);
    expect(find.byType(EligibleSurveysScreen), findsNothing);
  });

  testWidgets('an unreachable server shows the network message', (
    tester,
  ) async {
    final test = TestApi((request) async => throw http.ClientException('down'));
    await pumpRegister(tester, test);
    await fillAll(tester);

    await submit(tester);

    expect(
      find.text('Cannot reach the server. Is it running?'),
      findsOneWidget,
    );
  });

  testWidgets('success registers, logs in with the same credentials and '
      'opens the list', (tester) async {
    final registerBodies = <Map<String, dynamic>>[];
    final loginBodies = <Map<String, dynamic>>[];
    final test = TestApi((request) async {
      final path = request.url.path;
      if (path.endsWith('auth/register/')) {
        registerBodies.add(jsonDecode(request.body) as Map<String, dynamic>);
        return jsonResponse(respondentJson, 201);
      }
      if (path.endsWith('auth/token/')) {
        loginBodies.add(jsonDecode(request.body) as Map<String, dynamic>);
        return jsonResponse({'access': 'a', 'refresh': 'r'});
      }
      if (path.endsWith('me/')) return jsonResponse(respondentJson);
      return jsonResponse([]);
    });
    await pumpRegister(tester, test);
    await fillAll(tester);

    await submit(tester);

    expect(registerBodies.single, {
      'name': 'Sara',
      'email': 'sara@example.com',
      'password': 'secret-pass',
      'age': 24,
      'gender': 'FEMALE',
      'region': 'Amman',
      'interests': 'sports',
    });
    expect(loginBodies.single, {
      'email': 'sara@example.com',
      'password': 'secret-pass',
    });
    expect(find.byType(EligibleSurveysScreen), findsOneWidget);
    expect(test.tokens.refresh, 'r');
  });

  testWidgets('the login screen links to Create account', (tester) async {
    final test = TestApi((request) async => jsonResponse({}));
    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          authRepository: test.auth,
          surveysRepository: test.surveys,
        ),
      ),
    );

    await tester.tap(find.widgetWithText(TextButton, 'Create account'));
    await tester.pumpAndSettle();

    expect(find.byType(RegisterScreen), findsOneWidget);
  });
}
