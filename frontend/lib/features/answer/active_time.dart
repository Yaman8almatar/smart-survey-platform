/// Monotonic elapsed time in milliseconds.
typedef ElapsedClock = int Function();

/// FR-04: active time per question, in milliseconds.
///
/// A question adds time only while it is shown and the app is in the
/// foreground, over every visit (DESIGN-INC2 2.4, D-046 rule 3).
class ActiveTimeTracker {
  ActiveTimeTracker({ElapsedClock? clock, Map<int, int> initial = const {}})
    : _clock = clock ?? _stopwatchClock(),
      _totals = Map.of(initial);

  /// The largest `active_ms` the server accepts.
  static const int maxMs = 3600000;

  final ElapsedClock _clock;
  final Map<int, int> _totals;

  /// The question on screen; null on the review or after leaving.
  int? _shown;
  bool _paused = false;

  /// The clock value when the shown question last started counting.
  int? _since;

  static ElapsedClock _stopwatchClock() {
    final stopwatch = Stopwatch()..start();
    return () => stopwatch.elapsedMilliseconds;
  }

  /// Stops the running question and starts [questionId].
  void show(int questionId) {
    _stop();
    _shown = questionId;
    _totals.putIfAbsent(questionId, () => 0);
    if (!_paused) _since = _clock();
  }

  /// Stops counting with no question on screen.
  void hide() {
    _stop();
    _shown = null;
  }

  /// The app left the foreground.
  void pause() {
    _stop();
    _paused = true;
  }

  /// The app is back in the foreground: the shown question counts again.
  void resume() {
    if (!_paused) return;
    _paused = false;
    if (_shown != null) _since = _clock();
  }

  /// Totals so far, the running question included, each within 0..[maxMs].
  Map<int, int> snapshot() {
    final since = _since;
    final shown = _shown;
    return {
      for (final entry in _totals.entries)
        entry.key: _clamp(
          entry.value +
              (since != null && entry.key == shown ? _clock() - since : 0),
        ),
    };
  }

  void _stop() {
    final since = _since;
    final shown = _shown;
    if (since != null && shown != null) {
      _totals[shown] = _totals[shown]! + (_clock() - since);
    }
    _since = null;
  }

  static int _clamp(int ms) => ms.clamp(0, maxMs);
}
