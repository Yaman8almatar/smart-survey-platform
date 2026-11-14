import 'package:flutter/material.dart';

import '../features/profile/interest_icons.dart';
import '../features/profile/profile_models.dart';
import '../theme/app_theme.dart';
import '../theme/tokens.dart';

/// Interest topics as filter chips; an unselected chip shows its topic icon, a selected one the check.
class InterestChips extends StatelessWidget {
  const InterestChips({
    super.key,
    required this.options,
    required this.selected,
    required this.onChanged,
    this.errorText,
    this.enabled = true,
  });

  final List<ChoiceOption> options;
  final Set<String> selected;
  final ValueChanged<Set<String>> onChanged;
  final String? errorText;
  final bool enabled;

  void _toggle(String code, bool on) {
    final next = {...selected};
    on ? next.add(code) : next.remove(code);
    onChanged(next);
  }

  @override
  Widget build(BuildContext context) {
    final errorText = this.errorText;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: SsSpace.s2,
          runSpacing: SsSpace.s2,
          children: [
            for (final option in options)
              FilterChip(
                label: Text(option.label),
                selected: selected.contains(option.code),
                avatar: selected.contains(option.code)
                    ? null
                    : Icon(
                        interestIcon(option.code),
                        size: SsLayout.iconSmall,
                        color: SsColors.inkMuted,
                      ),
                onSelected: enabled ? (on) => _toggle(option.code, on) : null,
              ),
          ],
        ),
        if (errorText != null) ...[
          const SizedBox(height: SsSpace.s1),
          Text(
            errorText,
            style: SsType.caption.copyWith(color: SsColors.danger),
          ),
        ],
      ],
    );
  }
}
