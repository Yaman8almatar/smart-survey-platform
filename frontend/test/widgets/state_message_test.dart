import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/theme/app_theme.dart';
import 'package:smart_survey_app/widgets/state_message.dart';

Widget host(Widget child) => MaterialApp(
  theme: AppTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  testWidgets('shows icon, title and body', (tester) async {
    await tester.pumpWidget(
      host(
        const StateMessage(
          icon: Icons.inbox_outlined,
          title: 'Nothing here yet',
          body: 'New items appear here.',
        ),
      ),
    );

    expect(find.byIcon(Icons.inbox_outlined), findsOneWidget);
    expect(find.text('Nothing here yet'), findsOneWidget);
    expect(find.text('New items appear here.'), findsOneWidget);
  });

  testWidgets('the action is shown and can be tapped', (tester) async {
    var taps = 0;
    await tester.pumpWidget(
      host(
        StateMessage(
          title: 'Could not load',
          action: FilledButton(
            onPressed: () => taps++,
            child: const Text('Retry'),
          ),
        ),
      ),
    );

    await tester.tap(find.widgetWithText(FilledButton, 'Retry'));
    await tester.pump();

    expect(taps, 1);
  });
}
