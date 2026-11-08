import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/theme/app_theme.dart';
import 'package:smart_survey_app/widgets/signal_ring.dart';

const pingKey = ValueKey('signal-ring-ping');

Widget host(int value, {bool disableAnimations = false, bool ping = true}) =>
    MaterialApp(
      theme: AppTheme.light(),
      home: MediaQuery(
        data: MediaQueryData(disableAnimations: disableAnimations),
        child: Scaffold(
          body: Center(
            child: SignalRing(
              value: value,
              semanticLabel: 'Profile $value percent complete',
              ping: ping,
            ),
          ),
        ),
      ),
    );

void main() {
  testWidgets('renders 0, 57 and 100', (tester) async {
    for (final value in [0, 57, 100]) {
      await tester.pumpWidget(host(value));
      await tester.pumpAndSettle();
      expect(find.text('$value%'), findsOneWidget);
    }
  });

  testWidgets('counts up to the value', (tester) async {
    await tester.pumpWidget(host(57));
    expect(find.text('0%'), findsOneWidget);

    await tester.pumpAndSettle();
    expect(find.text('57%'), findsOneWidget);
  });

  testWidgets('exposes the caller label to semantics', (tester) async {
    final semantics = tester.ensureSemantics();
    await tester.pumpWidget(host(57));
    await tester.pumpAndSettle();

    expect(
      find.bySemanticsLabel('Profile 57 percent complete'),
      findsOneWidget,
    );
    semantics.dispose();
  });

  testWidgets('with animations disabled shows the final value at once', (
    tester,
  ) async {
    await tester.pumpWidget(host(57, disableAnimations: true));
    await tester.pump();

    expect(find.text('57%'), findsOneWidget);
  });

  testWidgets('reaching 100 plays one ping that is removed when it ends', (
    tester,
  ) async {
    await tester.pumpWidget(host(57));
    await tester.pumpAndSettle();
    expect(find.byKey(pingKey), findsNothing);

    await tester.pumpWidget(host(100));
    await tester.pump(const Duration(milliseconds: 600));
    await tester.pump();
    expect(find.byKey(pingKey), findsOneWidget);

    await tester.pumpAndSettle();
    expect(find.byKey(pingKey), findsNothing);
    expect(find.text('100%'), findsOneWidget);
  });

  testWidgets('ping false builds no ping layer at 100', (tester) async {
    await tester.pumpWidget(host(57, ping: false));
    await tester.pumpAndSettle();

    await tester.pumpWidget(host(100, ping: false));
    await tester.pump(const Duration(milliseconds: 600));
    await tester.pump();

    expect(find.byKey(pingKey), findsNothing);
    expect(find.text('100%'), findsOneWidget);
  });

  testWidgets('centerLabel replaces the percent text', (tester) async {
    await tester.pumpWidget(
      const Directionality(
        textDirection: TextDirection.ltr,
        child: SignalRing(value: 33, semanticLabel: 'x', centerLabel: '2/6'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('2/6'), findsOneWidget);
    expect(find.text('33%'), findsNothing);
  });

  testWidgets('centerIcon replaces the text', (tester) async {
    await tester.pumpWidget(
      const Directionality(
        textDirection: TextDirection.ltr,
        child: SignalRing(
          value: 100,
          semanticLabel: 'x',
          centerLabel: 'ignored',
          centerIcon: Icons.check,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.check), findsOneWidget);
    expect(find.text('ignored'), findsNothing);
    expect(find.text('100%'), findsNothing);
  });

  testWidgets('never pings when first built at 100', (tester) async {
    await tester.pumpWidget(host(100));
    await tester.pump(const Duration(milliseconds: 600));
    await tester.pump();

    expect(find.byKey(pingKey), findsNothing);
  });
}
