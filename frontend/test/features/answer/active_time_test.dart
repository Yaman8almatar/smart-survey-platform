import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/features/answer/active_time.dart';

/// A clock the test moves by hand.
class _Clock {
  int ms = 0;
  int call() => ms;
}

void main() {
  late _Clock clock;

  ActiveTimeTracker tracker([Map<int, int> initial = const {}]) =>
      ActiveTimeTracker(clock: clock.call, initial: initial);

  setUp(() => clock = _Clock());

  test('one question shown for 4,000 ms', () {
    final time = tracker()..show(1);
    clock.ms += 4000;

    expect(time.snapshot(), {1: 4000});
  });

  test('two visits add up', () {
    final time = tracker()..show(1);
    clock.ms += 1000;
    time.show(2);
    clock.ms += 500;
    time.show(1);
    clock.ms += 2000;

    expect(time.snapshot(), {1: 3000, 2: 500});
  });

  test('switching questions stops the first one', () {
    final time = tracker()..show(1);
    clock.ms += 1500;
    time.show(2);
    clock.ms += 2500;

    expect(time.snapshot(), {1: 1500, 2: 2500});
  });

  test('hide on the review adds nothing', () {
    final time = tracker()..show(1);
    clock.ms += 1000;
    time.hide();
    clock.ms += 30000;

    expect(time.snapshot(), {1: 1000});
  });

  test('pause adds nothing; resume continues the same question', () {
    final time = tracker()..show(1);
    clock.ms += 1000;
    time.pause();
    clock.ms += 60000;
    time.resume();
    clock.ms += 500;

    expect(time.snapshot(), {1: 1500});
  });

  test('resume on the review starts no question', () {
    final time = tracker()..show(1);
    clock.ms += 1000;
    time
      ..hide()
      ..pause()
      ..resume();
    clock.ms += 5000;

    expect(time.snapshot(), {1: 1000});
  });

  test('a question shown while paused waits for resume', () {
    final time = tracker()..pause();
    time.show(1);
    clock.ms += 5000;
    time.resume();
    clock.ms += 200;

    expect(time.snapshot(), {1: 200});
  });

  test('restored timings add to new time', () {
    final time = tracker({1: 3000})..show(1);
    clock.ms += 2000;

    expect(time.snapshot(), {1: 5000});
  });

  test('a value above 3,600,000 is clamped in the snapshot', () {
    final time = tracker({1: 3599000})..show(1);
    clock.ms += 5000;

    expect(time.snapshot(), {1: ActiveTimeTracker.maxMs});
  });

  test('questions at 0 are kept', () {
    final time = tracker({3: 0})..show(1);

    expect(time.snapshot(), {3: 0, 1: 0});
  });

  test('the default clock is a running stopwatch', () {
    final time = ActiveTimeTracker()..show(1);

    expect(time.snapshot()[1], greaterThanOrEqualTo(0));
  });
}
