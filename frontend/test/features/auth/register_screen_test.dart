import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:smart_survey_app/features/auth/login_screen.dart';
import 'package:smart_survey_app/features/auth/register_screen.dart';
import 'package:smart_survey_app/features/surveys/eligible_surveys_screen.dart';

import '../../support/test_api.dart';

/// Answers `profile/options/`; every other request goes to [handler].
TestApi registerApi(Future<http.Response> Function(http.Request) handler) =>
    TestApi((request) async {
      if (request.url.path.endsWith('profile/options/')) {
        return jsonResponse(profileOptionsJson);
      }
      return handler(request);
    });

Future<void> pumpRegister(WidgetTester tester, TestApi test) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      home: RegisterScreen(
        authRepository: test.auth,
        surveysRepository: test.surveys,
        profileRepository: test.profile,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> fill(WidgetTester tester, String label, String text) =>
    tester.enterText(find.widgetWithText(TextFormField, label), text);

Future<void> pickGovernorate(WidgetTester tester, String label) async {
  await tester.tap(find.text('Governorate'));
  await tester.pumpAndSettle();
  await tester.tap(find.text(label).last);
  await tester.pumpAndSettle();
}

Future<void> fillAll(
  WidgetTester tester, {
  String age = '24',
  bool pickGender = true,
  bool pickInterest = true,
}) async {
  await fill(tester, 'Name', 'Sara');
  await fill(tester, 'Email', 'sara@example.com');
  await fill(tester, 'Password', 'secret-pass');
  await fill(tester, 'Age', age);
  await pickGovernorate(tester, 'Damascus');
  if (pickInterest) {
    await tester.tap(find.widgetWithText(FilterChip, 'Sports'));
    await tester.pump();
  }
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
    final test = registerApi((request) async {
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
    expect(find.text('Choose your governorate.'), findsOneWidget);
    expect(find.text('Choose at least one interest.'), findsOneWidget);
    expect(requests, 0);
  });

  testWidgets('empty interests are blocked without calling the API', (
    tester,
  ) async {
    var requests = 0;
    final test = registerApi((request) async {
      requests++;
      return jsonResponse({});
    });
    await pumpRegister(tester, test);
    await fillAll(tester, pickInterest: false);

    await submit(tester);

    expect(find.text('Choose at least one interest.'), findsOneWidget);
    expect(requests, 0);
  });

  testWidgets('age outside 1 to 120 is blocked', (tester) async {
    final test = registerApi((request) async => jsonResponse({}));
    await pumpRegister(tester, test);
    await fillAll(tester, age: '121');

    await submit(tester);

    expect(find.text('Enter an age from 1 to 120.'), findsOneWidget);
    expect(find.text('Choose a gender.'), findsNothing);
  });

  testWidgets('a server field error appears under the matching field', (
    tester,
  ) async {
    final test = registerApi(
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
    final test = registerApi(
      (request) async => throw http.ClientException('down'),
    );
    await pumpRegister(tester, test);
    await fillAll(tester);

    await submit(tester);

    expect(
      find.text('Cannot reach the server. Is it running?'),
      findsOneWidget,
    );
  });

  testWidgets('options that fail to load show a retry', (tester) async {
    var calls = 0;
    final test = TestApi((request) async {
      calls++;
      return calls == 1
          ? throw http.ClientException('down')
          : jsonResponse(profileOptionsJson);
    });
    await pumpRegister(tester, test);

    expect(find.text('Could not load the form'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Try again'));
    await tester.pumpAndSettle();

    expect(find.text('Governorate'), findsOneWidget);
    expect(
      find.text(
        'Your age, gender and governorate decide which surveys you see.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('success sends codes, logs in with the same credentials and '
      'opens the list', (tester) async {
    final registerBodies = <Map<String, dynamic>>[];
    final loginBodies = <Map<String, dynamic>>[];
    final test = registerApi((request) async {
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
      'region': 'DAMASCUS',
      'interests': ['SPORTS'],
    });
    expect(loginBodies.single, {
      'email': 'sara@example.com',
      'password': 'secret-pass',
    });
    expect(find.byType(EligibleSurveysScreen), findsOneWidget);
    expect(test.tokens.refresh, 'r');
  });

  testWidgets('the login screen links to Create account', (tester) async {
    final test = registerApi((request) async => jsonResponse({}));
    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          authRepository: test.auth,
          surveysRepository: test.surveys,
          profileRepository: test.profile,
        ),
      ),
    );

    await tester.tap(find.widgetWithText(TextButton, 'Create account'));
    await tester.pumpAndSettle();

    expect(find.byType(RegisterScreen), findsOneWidget);
  });
}
