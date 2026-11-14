import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../theme/tokens.dart';

/// Equal number buttons, one per value, with the two ends named underneath.
class RatingScale extends StatelessWidget {
  const RatingScale({
    super.key,
    required this.values,
    required this.selected,
    required this.onChanged,
    this.error = false,
  });

  final List<int> values;
  final int? selected;

  /// Null disables the scale.
  final ValueChanged<int>? onChanged;

  /// Marks a required question that was left without an answer.
  final bool error;

  @override
  Widget build(BuildContext context) {
    final onChanged = this.onChanged;
    final endStyle = SsType.caption.copyWith(color: SsColors.inkMuted);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            for (var i = 0; i < values.length; i++) ...[
              if (i > 0) const SizedBox(width: SsSpace.s2),
              Expanded(
                child: _RatingButton(
                  value: values[i],
                  max: values.last,
                  selected: values[i] == selected,
                  error: error,
                  onTap: onChanged == null ? null : () => onChanged(values[i]),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: SsSpace.s2),
        ExcludeSemantics(
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Lowest', style: endStyle),
              Text('Highest', style: endStyle),
            ],
          ),
        ),
      ],
    );
  }
}

class _RatingButton extends StatelessWidget {
  const _RatingButton({
    required this.value,
    required this.max,
    required this.selected,
    required this.error,
    required this.onTap,
  });

  final int value;
  final int max;
  final bool selected;
  final bool error;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final duration = SsMotion.of(context, SsMotion.fast);
    final shape = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(SsRadius.sm),
      side: BorderSide(
        color: selected
            ? SsColors.brand
            : (error ? SsColors.danger : SsColors.lineStrong),
        width: selected ? SsLayout.selectedBorder : SsLayout.hairline,
      ),
    );

    return Semantics(
      container: true,
      label: '$value out of $max',
      inMutuallyExclusiveGroup: true,
      checked: selected,
      enabled: onTap != null,
      onTap: onTap,
      child: ExcludeSemantics(
        child: Material(
          color: selected ? SsColors.brandTint : SsColors.surfaceRaised,
          shape: shape,
          animationDuration: duration,
          child: InkWell(
            customBorder: shape,
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(
                minHeight: SsLayout.ratingHeight,
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Text(
                    '$value',
                    style: SsType.ring.copyWith(color: SsColors.ink),
                  ),
                  PositionedDirectional(
                    top: SsSpace.s1,
                    end: SsSpace.s1,
                    child: AnimatedOpacity(
                      duration: duration,
                      opacity: selected ? 1 : 0,
                      child: const Icon(
                        Icons.check,
                        size: SsLayout.ratingCheck,
                        color: SsColors.brand,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
