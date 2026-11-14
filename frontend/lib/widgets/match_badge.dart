import 'package:flutter/material.dart';

import '../theme/tokens.dart';

/// The saffron badge on a survey that fits the respondent.
class MatchBadge extends StatelessWidget {
  const MatchBadge({super.key});

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
          'Matches your profile',
          style: Theme.of(
            context,
          ).textTheme.labelMedium?.copyWith(color: SsColors.ink),
        ),
      ),
    );
  }
}
