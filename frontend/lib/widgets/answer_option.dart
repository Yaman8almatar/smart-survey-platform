import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../theme/tokens.dart';

/// One choice of a question: a full-width row in a mutually exclusive group.
class AnswerOption extends StatelessWidget {
  const AnswerOption({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
    this.error = false,
  });

  final String label;
  final bool selected;

  /// Null disables the row.
  final VoidCallback? onTap;

  /// Marks a required question that was left without an answer.
  final bool error;

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
      label: label,
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
                minHeight: SsLayout.answerOptionHeight,
              ),
              child: Padding(
                padding: const EdgeInsetsDirectional.symmetric(
                  horizontal: SsSpace.s4,
                  vertical: SsSpace.s3,
                ),
                child: Row(
                  children: [
                    _Check(selected: selected, duration: duration),
                    const SizedBox(width: SsSpace.s3),
                    Expanded(
                      child: Text(
                        label,
                        style: SsType.body.copyWith(color: SsColors.ink),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Check extends StatelessWidget {
  const _Check({required this.selected, required this.duration});

  final bool selected;
  final Duration duration;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: duration,
      width: SsLayout.answerCheck,
      height: SsLayout.answerCheck,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: selected ? SsColors.brand : null,
        border: Border.all(
          color: selected ? SsColors.brand : SsColors.lineStrong,
          width: SsLayout.selectedBorder,
        ),
      ),
      child: AnimatedOpacity(
        duration: duration,
        opacity: selected ? 1 : 0,
        child: const Icon(
          Icons.check,
          size: SsLayout.iconSmall,
          color: SsColors.surfaceRaised,
        ),
      ),
    );
  }
}
