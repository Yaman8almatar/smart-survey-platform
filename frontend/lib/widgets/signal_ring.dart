import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../theme/tokens.dart';

/// The product's only progress shape: a ring whose arc and centred number show a 0-100 value.
///
/// The value always comes from the API; the client never computes it. The arc counts up from 0 on
/// the first build and from the previous value after that. When the value reaches 100 while the
/// widget is shown, one saffron ping plays once.
class SignalRing extends StatefulWidget {
  const SignalRing({
    super.key,
    required this.value,
    required this.semanticLabel,
    this.size = 88,
    this.onDark = true,
  });

  /// Progress from 0 to 100.
  final int value;

  /// Spoken label, for example "Profile 57 percent complete".
  final String semanticLabel;

  final double size;

  /// True on a brand-deep background, false on a light surface.
  final bool onDark;

  @override
  State<SignalRing> createState() => _SignalRingState();
}

class _SignalRingState extends State<SignalRing>
    with SingleTickerProviderStateMixin {
  static const double _pingGap = 8;
  static const double _pingStroke = 2;

  late final AnimationController _ping;
  bool _pingPending = false;
  bool _pinging = false;

  int get _target => widget.value.clamp(0, 100);

  @override
  void initState() {
    super.initState();
    _ping = AnimationController(vsync: this, duration: SsMotion.emphasized)
      ..addStatusListener(_onPingStatus);
  }

  @override
  void didUpdateWidget(SignalRing oldWidget) {
    super.didUpdateWidget(oldWidget);
    final animate = SsMotion.of(context, SsMotion.emphasized) > Duration.zero;
    if (animate && oldWidget.value < 100 && _target == 100) {
      _pingPending = true;
    } else if (_target != 100) {
      _pingPending = false;
    }
  }

  void _onFillEnd() {
    if (!_pingPending) return;
    _pingPending = false;
    setState(() => _pinging = true);
    _ping.forward(from: 0);
  }

  void _onPingStatus(AnimationStatus status) {
    if (status == AnimationStatus.completed && mounted) {
      setState(() => _pinging = false);
    }
  }

  @override
  void dispose() {
    _ping.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = widget.size;
    final onDark = widget.onDark;
    final track = onDark
        ? SsColors.surfaceRaised.withValues(alpha: 0.18)
        : SsColors.line;
    final arc = onDark ? SsColors.accent : SsColors.brand;
    final textColor = onDark ? SsColors.surfaceRaised : SsColors.ink;
    final textStyle =
        (size <= 48
                ? SsType.ring.copyWith(fontSize: 12, height: 16 / 12)
                : SsType.ring)
            .copyWith(color: textColor);

    return Semantics(
      label: widget.semanticLabel,
      child: ExcludeSemantics(
        child: SizedBox.square(
          dimension: size,
          child: Stack(
            clipBehavior: Clip.none,
            alignment: Alignment.center,
            children: [
              TweenAnimationBuilder<double>(
                tween: Tween(begin: 0, end: _target.toDouble()),
                duration: SsMotion.of(context, SsMotion.emphasized),
                curve: SsMotion.emphasizedCurve,
                onEnd: _onFillEnd,
                builder: (context, value, _) => CustomPaint(
                  size: Size.square(size),
                  painter: _RingPainter(
                    fraction: value / 100,
                    stroke: (size / 11).roundToDouble(),
                    track: track,
                    arc: arc,
                  ),
                  child: Center(
                    child: Text('${value.round()}%', style: textStyle),
                  ),
                ),
              ),
              if (_pinging)
                Positioned(
                  key: const ValueKey('signal-ring-ping'),
                  left: -_pingGap,
                  top: -_pingGap,
                  width: size + _pingGap * 2,
                  height: size + _pingGap * 2,
                  child: AnimatedBuilder(
                    animation: _ping,
                    builder: (context, child) {
                      final t = SsMotion.emphasizedCurve.transform(_ping.value);
                      return Opacity(
                        opacity: 0.35 * (1 - t),
                        child: Transform.scale(
                          scale: 1 + 0.15 * t,
                          child: child,
                        ),
                      );
                    },
                    child: const DecoratedBox(
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.fromBorderSide(
                          BorderSide(
                            color: SsColors.accent,
                            width: _pingStroke,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  const _RingPainter({
    required this.fraction,
    required this.stroke,
    required this.track,
    required this.arc,
  });

  final double fraction;
  final double stroke;
  final Color track;
  final Color arc;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = (Offset.zero & size).deflate(stroke / 2);
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawOval(rect, paint..color = track);
    if (fraction <= 0) return;
    if (fraction >= 1) {
      canvas.drawOval(rect, paint..color = arc);
      return;
    }
    canvas.drawArc(
      rect,
      -math.pi / 2,
      2 * math.pi * fraction,
      false,
      paint..color = arc,
    );
  }

  @override
  bool shouldRepaint(_RingPainter old) =>
      old.fraction != fraction ||
      old.stroke != stroke ||
      old.track != track ||
      old.arc != arc;
}
