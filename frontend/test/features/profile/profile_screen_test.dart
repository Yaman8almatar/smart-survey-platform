import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:smart_survey_app/features/profile/profile_screen.dart';
import 'package:smart_survey_app/widgets/choice_select_field.dart';

import '../../support/test_api.dart';

final Map<String, Object> completeProfileJson = {
  ...profileJson,
  'education': 'BACHELOR',
  'occupation': 'STUDENT',
  'marital_status': 'PREFER_NOT_TO_SAY',
  'completion_percent': 100,
};

/// Serves the options, [profile] on GET (null: 404) and [onPut] on PUT.
TestApi profileApi({
  Object? profile = profileJson,
  Future<http.Response> Function(http.Request)? onPut,
  List<http.Request>? log,
}) => TestApi((request) async {
  log?.add(request);
  final path = request.url.path;
  if (path.endsWith('profile/options/')) {
    return jsonResponse(profileOptionsJson);
  }
  if (request.method == 'PUT') {
    return onPut == null ? jsonResponse(profile) : onPut(request);
  }
  return profile == null
      ? errorResponse(404, 'not_found', 'Not found.')
      : jsonResponse(profile);
});

Widget profileApp(TestApi test, {bool disableAnimations = false}) {
  return MaterialApp(
    home: Builder(
      builder: (context) => MediaQuery(
        data: MediaQuery.of(
          context,
        ).copyWith(disableAnimations: disableAnimations),
        child: ProfileScreen(
          authRepository: test.auth,
          surveysRepository: test.surveys,
          profileRepository: test.profile,
        ),
      ),
    ),
  );
}

Future<void> pumpProfile(WidgetTester tester, TestApi test) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(profileApp(test));
  await tester.pumpAndSettle();
}

Finder saveButton(String label) => find.widgetWithText(FilledButton, label);

Future<void> pickChoice(WidgetTester tester, String field, String item) async {
  await tester.tap(find.widgetWithText(ChoiceSelectField, field));
  await tester.pumpAndSettle();
  await tester.tap(find.text(item).last);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('loads, then shows the ring, hero copy and stored values', (
    tester,
  ) async {
    final gate = Completer<http.Response>();
    final test = TestApi((request) {
      if (request.url.path.endsWith('profile/options/')) {
        return Future.value(jsonResponse(profileOptionsJson));
      }
      return gate.future;
    });
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(profileApp(test));
    await tester.pump();

    expect(find.bySemanticsLabel('Loading your profile'), findsOneWidget);

    gate.complete(jsonResponse(profileJson));
    await tester.pumpAndSettle();

    expect(find.text('57%'), findsOneWidget);
    expect(
      find.bySemanticsLabel('Profile 57 percent complete'),
      findsOneWidget,
    );
    expect(find.text('4 of 7 details added'), findsOneWidget);
    expect(
      find.text(
        'Add your education, occupation and marital status so more surveys '
        'can find you.',
      ),
      findsOneWidget,
    );
    expect(
      tester.widget<TextField>(find.byType(TextField)).controller!.text,
      '24',
    );
    expect(
      tester
          .widget<SegmentedButton<String>>(find.byType(SegmentedButton<String>))
          .selected,
      {'FEMALE'},
    );
    expect(find.text('Damascus'), findsOneWidget);
    expect(
      tester.widget<FilledButton>(saveButton('Save changes')).onPressed,
      isNull,
    );
  });

  testWidgets('section statuses follow the form values', (tester) async {
    final log = <http.Request>[];
    await pumpProfile(tester, profileApi(log: log));

    expect(find.text('Done'), findsNWidgets(3));
    expect(find.text('Optional, 0 of 3'), findsOneWidget);

    await pickChoice(tester, 'Marital status', 'Single');
    expect(find.text('Optional, 1 of 3'), findsOneWidget);

    await tester.enterText(find.byType(TextField), '');
    await tester.pump();
    expect(find.text('1 to go'), findsOneWidget);

    await tester.tap(saveButton('Save changes'));
    await tester.pumpAndSettle();

    expect(find.text('Needs attention'), findsOneWidget);
    expect(find.text('Enter an age from 1 to 120.'), findsOneWidget);
    expect(
      find.text('Fix the 1 highlighted field, then save.'),
      findsOneWidget,
    );
    expect(log.where((r) => r.method == 'PUT'), isEmpty);

    await tester.enterText(find.byType(TextField), '25');
    await tester.pump();
    expect(find.text('Needs attention'), findsNothing);
    expect(find.text('Fix the 1 highlighted field, then save.'), findsNothing);
  });

  testWidgets('first time shows 0% and a disabled Save profile', (
    tester,
  ) async {
    await pumpProfile(tester, profileApi(profile: null));

    expect(find.text('0%'), findsOneWidget);
    expect(find.text('Set up your profile'), findsOneWidget);
    expect(
      tester.widget<FilledButton>(saveButton('Save profile')).onPressed,
      isNull,
    );
  });

  testWidgets('a load error shows Try again, and a retry succeeds', (
    tester,
  ) async {
    var down = true;
    final test = TestApi((request) async {
      if (down) throw http.ClientException('down');
      return request.url.path.endsWith('profile/options/')
          ? jsonResponse(profileOptionsJson)
          : jsonResponse(profileJson);
    });
    await pumpProfile(tester, test);

    expect(find.text('Could not load your profile'), findsOneWidget);
    expect(
      find.text(
        'Cannot reach the server. Check your connection and try again.',
      ),
      findsOneWidget,
    );

    down = false;
    await tester.tap(find.widgetWithText(FilledButton, 'Try again'));
    await tester.pumpAndSettle();

    expect(find.text('57%'), findsOneWidget);
  });

  testWidgets('save sends all seven fields and shows the new percent', (
    tester,
  ) async {
    Map<String, dynamic>? body;
    final test = profileApi(
      onPut: (request) async {
        body = jsonDecode(request.body) as Map<String, dynamic>;
        return jsonResponse({
          ...profileJson,
          'marital_status': 'SINGLE',
          'completion_percent': 71,
        });
      },
    );
    await pumpProfile(tester, test);

    await pickChoice(tester, 'Marital status', 'Single');
    await tester.tap(saveButton('Save changes'));
    await tester.pumpAndSettle();

    expect(body, {
      'age': 24,
      'gender': 'FEMALE',
      'region': 'DAMASCUS',
      'interests': ['TECHNOLOGY', 'EDUCATION', 'HEALTH'],
      'education': '',
      'occupation': '',
      'marital_status': 'SINGLE',
    });
    expect(find.text('Profile saved'), findsOneWidget);
    expect(find.text('71%'), findsOneWidget);
    expect(find.text('5 of 7 details added'), findsOneWidget);
    expect(
      tester.widget<FilledButton>(saveButton('Save changes')).onPressed,
      isNull,
    );
  });

  testWidgets('a network failure on save keeps the edits', (tester) async {
    final test = profileApi(
      onPut: (request) async => throw http.ClientException('down'),
    );
    await pumpProfile(tester, test);

    await pickChoice(tester, 'Marital status', 'Single');
    await tester.tap(saveButton('Save changes'));
    await tester.pumpAndSettle();

    expect(find.text('Not saved. Cannot reach the server.'), findsOneWidget);
    expect(find.widgetWithText(SnackBarAction, 'Try again'), findsOneWidget);
    expect(find.text('Single'), findsOneWidget);
    expect(find.text('Optional, 1 of 3'), findsOneWidget);
  });

  testWidgets('validation blocks the request and counts the fields', (
    tester,
  ) async {
    final log = <http.Request>[];
    await pumpProfile(tester, profileApi(profile: null, log: log));

    await tester.enterText(find.byType(TextField), '30');
    await tester.tap(find.text('Male'));
    await tester.pump();
    await tester.tap(saveButton('Save profile'));
    await tester.pumpAndSettle();

    expect(
      find.text('Fix the 2 highlighted fields, then save.'),
      findsOneWidget,
    );
    expect(find.text('Choose your governorate.'), findsOneWidget);
    expect(find.text('Choose at least one interest.'), findsOneWidget);
    expect(find.text('Needs attention'), findsNWidgets(2));
    expect(log.where((r) => r.method == 'PUT'), isEmpty);
  });

  testWidgets('a 400 region error appears under Governorate', (tester) async {
    final test = profileApi(
      onPut: (request) async => errorResponse(
        400,
        'validation_error',
        'Invalid input.',
        fields: {
          'region': ['Choose a governorate from the list.'],
        },
      ),
    );
    await pumpProfile(tester, test);

    await tester.enterText(find.byType(TextField), '25');
    await tester.pump();
    await tester.tap(saveButton('Save changes'));
    await tester.pumpAndSettle();

    expect(
      find.descendant(
        of: find.widgetWithText(ChoiceSelectField, 'Governorate'),
        matching: find.text('Choose a governorate from the list.'),
      ),
      findsOneWidget,
    );
    expect(find.text('Invalid input.'), findsNothing);
  });

  testWidgets('leaving with changes asks first', (tester) async {
    final test = profileApi();
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: TextButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => ProfileScreen(
                    authRepository: test.auth,
                    surveysRepository: test.surveys,
                    profileRepository: test.profile,
                  ),
                ),
              ),
              child: const Text('Open'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), '25');
    await tester.pump();
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();

    expect(find.text('Discard your changes?'), findsOneWidget);
    expect(
      find.text('Your edits to this profile will be lost.'),
      findsOneWidget,
    );

    await tester.tap(find.text('Keep editing'));
    await tester.pumpAndSettle();
    expect(find.byType(ProfileScreen), findsOneWidget);

    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Discard'));
    await tester.pumpAndSettle();

    expect(find.byType(ProfileScreen), findsNothing);
    expect(find.text('Open'), findsOneWidget);
  });

  testWidgets('100% shows the Complete badge', (tester) async {
    await pumpProfile(tester, profileApi(profile: completeProfileJson));

    expect(find.text('100%'), findsOneWidget);
    expect(find.text('Complete'), findsOneWidget);
    expect(find.text('All 7 details added'), findsOneWidget);
    expect(find.text('Done'), findsNWidgets(4));
  });

  testWidgets('with animations disabled the final values show at once', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(profileApp(profileApi(), disableAnimations: true));
    await tester.pump();
    await tester.pump();

    expect(find.text('57%'), findsOneWidget);
    expect(find.text('4 of 7 details added'), findsOneWidget);
    expect(tester.hasRunningAnimations, isFalse);
  });
}
