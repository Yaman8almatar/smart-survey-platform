import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';
import '../../theme/tokens.dart';
import '../../widgets/signal_ring.dart';
import 'profile_models.dart';

/// The white sheet that rises over the hero band.
const BoxDecoration profileSheetDecoration = BoxDecoration(
  color: SsColors.surfaceRaised,
  borderRadius: BorderRadius.vertical(top: Radius.circular(SsRadius.lg)),
);

/// The sheet over the hero: pulled up, and on first paint it rises and fades in.
class RisingSheet extends StatelessWidget {
  const RisingSheet({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 1, end: 0),
      duration: SsMotion.of(context, SsMotion.standard),
      curve: SsMotion.standardCurve,
      builder: (context, t, child) => Transform.translate(
        offset: Offset(0, -SsSpace.s6 + SsSpace.s4 * t),
        child: Opacity(opacity: 1 - t, child: child),
      ),
      child: DecoratedBox(decoration: profileSheetDecoration, child: child),
    );
  }
}

/// Centres [child] and keeps it within the content width.
class ProfileContentWidth extends StatelessWidget {
  const ProfileContentWidth({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: AlignmentDirectional.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: SsLayout.contentMaxWidth),
        child: child,
      ),
    );
  }
}

/// Hero copy for a saved profile (null: none yet).
({String title, String body}) heroCopy(Profile? saved) {
  final percent = saved?.completionPercent ?? 0;
  final missing = missingDetails(saved);
  final filled = 7 - missing.length;
  if (percent == 0) {
    return (
      title: 'Set up your profile',
      body:
          'Add your details so surveys that fit you can find you. '
          'It takes about a minute.',
    );
  }
  if (percent == 100) {
    return (
      title: 'All 7 details added',
      body: 'Keep them up to date so the right surveys reach you.',
    );
  }
  return (
    title: '$filled of 7 details added',
    body: 'Add your ${joinWithAnd(missing)} so more surveys can find you.',
  );
}

/// The details a saved profile lacks, in form order and lower case.
List<String> missingDetails(Profile? p) => [
  if (p == null) 'age',
  if (p == null || p.gender.isEmpty) 'gender',
  if (p == null || p.region.isEmpty) 'governorate',
  if (p == null || p.interests.isEmpty) 'interests',
  if (p == null || p.education.isEmpty) 'education',
  if (p == null || p.occupation.isEmpty) 'occupation',
  if (p == null || p.maritalStatus.isEmpty) 'marital status',
];

/// "a", "a and b", "a, b and c".
String joinWithAnd(List<String> items) {
  if (items.length <= 1) return items.join();
  return '${items.sublist(0, items.length - 1).join(', ')} and ${items.last}';
}

/// The brand-deep band: decorative circles, padding and content width.
class HeroBand extends StatelessWidget {
  const HeroBand({super.key, required this.child, this.decorCenterY});

  final Widget child;

  /// Centres the circles horizontally at this height; null puts them beyond the top-end corner.
  final double? decorCenterY;

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: DecoratedBox(
        decoration: const BoxDecoration(color: SsColors.brandDeep),
        child: Stack(
          children: [
            Positioned.fill(
              child: ExcludeSemantics(
                child: CustomPaint(
                  painter: _HeroDecorPainter(
                    textDirection: Directionality.of(context),
                    centerY: decorCenterY,
                  ),
                ),
              ),
            ),
            // Padding inside the width, as on the sheet, so their edges line up.
            ProfileContentWidth(
              child: Padding(
                padding: const EdgeInsetsDirectional.fromSTEB(
                  SsSpace.s4,
                  SsSpace.s4,
                  SsSpace.s4,
                  SsSpace.s10,
                ),
                child: child,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Ring, badge and copy from the saved profile.
class ProfileHero extends StatelessWidget {
  const ProfileHero({super.key, required this.saved});

  final Profile? saved;

  @override
  Widget build(BuildContext context) {
    final percent = saved?.completionPercent ?? 0;
    final copy = heroCopy(saved);
    return HeroBand(
      child: Row(
        children: [
          SignalRing(
            value: percent,
            size: SsLayout.ringSize,
            semanticLabel: 'Profile $percent percent complete',
          ),
          const SizedBox(width: SsSpace.s4),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (percent == 100) ...[
                  const _FadeIn(child: _CompleteBadge()),
                  const SizedBox(height: SsSpace.s1),
                ],
                Text(
                  copy.title,
                  style: SsType.heading.copyWith(color: SsColors.surfaceRaised),
                ),
                const SizedBox(height: SsSpace.s1),
                Text(
                  copy.body,
                  style: SsType.body.copyWith(color: SsColors.onBrandMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CompleteBadge extends StatelessWidget {
  const _CompleteBadge();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: SsColors.accent,
        borderRadius: BorderRadius.circular(SsRadius.pill),
      ),
      child: Padding(
        padding: const EdgeInsetsDirectional.symmetric(
          horizontal: SsSpace.s2,
          vertical: SsSpace.s1,
        ),
        child: Text(
          'Complete',
          style: SsType.label.copyWith(color: SsColors.ink),
        ),
      ),
    );
  }
}

/// Fades its child in once, when it first appears.
class _FadeIn extends StatelessWidget {
  const _FadeIn({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: SsMotion.of(context, SsMotion.standard),
      curve: SsMotion.standardCurve,
      builder: (context, opacity, child) =>
          Opacity(opacity: opacity, child: child),
      child: child,
    );
  }
}

/// Three thin circles centred beyond the top-end corner, or mid-band at [centerY].
class _HeroDecorPainter extends CustomPainter {
  const _HeroDecorPainter({required this.textDirection, this.centerY});

  final TextDirection textDirection;
  final double? centerY;

  @override
  void paint(Canvas canvas, Size size) {
    final x = textDirection == TextDirection.rtl
        ? -SsSpace.s6
        : size.width + SsSpace.s6;
    final centerY = this.centerY;
    final center = centerY == null
        ? Offset(x, -SsSpace.s6)
        : Offset(size.width / 2, centerY);
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = SsLayout.hairline
      ..color = SsColors.onBrandDecor;
    for (final radius in SsLayout.heroDecorRadii) {
      canvas.drawCircle(center, radius, paint);
    }
  }

  @override
  bool shouldRepaint(_HeroDecorPainter old) =>
      old.textDirection != textDirection || old.centerY != centerY;
}

/// Loading placeholder: hero with an empty ring and bars, sheet with grey bars.
class ProfileSkeleton extends StatefulWidget {
  const ProfileSkeleton({super.key});

  @override
  State<ProfileSkeleton> createState() => _ProfileSkeletonState();
}

class _ProfileSkeletonState extends State<ProfileSkeleton>
    with SingleTickerProviderStateMixin {
  static const double _dimmest = 0.5;

  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: SsMotion.pulse,
    value: 1,
  );
  late final Animation<double> _opacity = Tween<double>(
    begin: _dimmest,
    end: 1,
  ).animate(_pulse);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final animate = SsMotion.of(context, SsMotion.pulse) > Duration.zero;
    if (animate && !_pulse.isAnimating) {
      _pulse.repeat(reverse: true);
    } else if (!animate) {
      _pulse
        ..stop()
        ..value = 1;
    }
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const heroBar = SsColors.onBrandSkeleton;
    const sheetBar = SsColors.line;
    return Semantics(
      label: 'Loading your profile',
      child: ExcludeSemantics(
        child: FadeTransition(
          opacity: _opacity,
          // Scroll view only so short screens clip instead of overflowing.
          child: SingleChildScrollView(
            physics: const NeverScrollableScrollPhysics(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const HeroBand(
                  child: Row(
                    children: [
                      SizedBox.square(
                        dimension: SsLayout.ringSize,
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.fromBorderSide(
                              BorderSide(color: heroBar, width: SsSpace.s2),
                            ),
                          ),
                        ),
                      ),
                      SizedBox(width: SsSpace.s4),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _Bar(widthFactor: 0.6, color: heroBar),
                            SizedBox(height: SsSpace.s2),
                            _Bar(widthFactor: 1, color: heroBar),
                            SizedBox(height: SsSpace.s2),
                            _Bar(widthFactor: 0.8, color: heroBar),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                Transform.translate(
                  offset: const Offset(0, -SsSpace.s6),
                  child: const DecoratedBox(
                    decoration: profileSheetDecoration,
                    child: ProfileContentWidth(
                      child: Padding(
                        padding: EdgeInsetsDirectional.symmetric(
                          horizontal: SsSpace.s4,
                          vertical: SsSpace.s5,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            _Bar(widthFactor: 0.3, color: sheetBar),
                            SizedBox(height: SsSpace.s4),
                            _Bar(
                              widthFactor: 1,
                              color: sheetBar,
                              height: SsLayout.skeletonField,
                            ),
                            SizedBox(height: SsSpace.s4),
                            _Bar(
                              widthFactor: 1,
                              color: sheetBar,
                              height: SsLayout.skeletonField,
                              radius: SsRadius.pill,
                            ),
                            SizedBox(height: SsSpace.s8),
                            _Bar(widthFactor: 0.4, color: sheetBar),
                            SizedBox(height: SsSpace.s4),
                            _Bar(
                              widthFactor: 1,
                              color: sheetBar,
                              height: SsLayout.skeletonField,
                            ),
                            SizedBox(height: SsSpace.s8),
                            _Bar(widthFactor: 0.25, color: sheetBar),
                            SizedBox(height: SsSpace.s4),
                            _Bar(
                              widthFactor: 0.7,
                              color: sheetBar,
                              height: SsLayout.skeletonField,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Bar extends StatelessWidget {
  const _Bar({
    required this.widthFactor,
    required this.color,
    this.height = SsLayout.skeletonLine,
    this.radius = SsRadius.sm,
  });

  final double widthFactor;
  final Color color;
  final double height;
  final double radius;

  @override
  Widget build(BuildContext context) {
    return FractionallySizedBox(
      alignment: AlignmentDirectional.centerStart,
      widthFactor: widthFactor,
      child: SizedBox(
        height: height,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.all(Radius.circular(radius)),
          ),
        ),
      ),
    );
  }
}
