import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:smart_survey_app/app.dart';

void main() {
  testWidgets('home screen shows the app bar and two startable surveys', (
    tester,
  ) async {
    await tester.pumpWidget(const SmartSurveyApp());
    await tester.pumpAndSettle();

    expect(find.text('Smart Survey'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Start'), findsNWidgets(2));
  });
}
