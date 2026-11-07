import 'package:flutter/material.dart';

import '../features/profile/profile_models.dart';
import '../theme/app_theme.dart';
import '../theme/tokens.dart';

/// The answer code that is set apart from the real answers in optional lists.
const String preferNotToSay = 'PREFER_NOT_TO_SAY';

/// A dropdown over `{code, label}` options: shows the label, reports the code.
class ChoiceSelectField extends StatelessWidget {
  const ChoiceSelectField({
    super.key,
    required this.label,
    required this.options,
    required this.value,
    required this.onChanged,
    this.errorText,
    this.separatePreferNotToSay = false,
  });

  final String label;
  final List<ChoiceOption> options;

  /// The selected code, or null when nothing is chosen.
  final String? value;

  /// Null disables the field.
  final ValueChanged<String?>? onChanged;
  final String? errorText;

  /// Puts a divider above "Prefer not to say" (the three optional lists).
  final bool separatePreferNotToSay;

  @override
  Widget build(BuildContext context) {
    final items = <DropdownMenuItem<String>>[];
    final closed = <Widget>[];
    for (final option in options) {
      if (separatePreferNotToSay && option.code == preferNotToSay) {
        items.add(
          const DropdownMenuItem<String>(enabled: false, child: Divider()),
        );
        closed.add(const SizedBox.shrink());
      }
      final selected = option.code == value;
      items.add(
        DropdownMenuItem<String>(
          value: option.code,
          child: Row(
            children: [
              Expanded(
                child: Text(
                  option.label,
                  style: SsType.body.copyWith(
                    color: SsColors.ink,
                    fontWeight: selected ? FontWeight.w600 : null,
                  ),
                ),
              ),
              if (selected)
                const Icon(
                  Icons.check,
                  size: SsLayout.iconSmall,
                  color: SsColors.brand,
                ),
            ],
          ),
        ),
      );
      closed.add(Text(option.label));
    }

    return DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      items: items,
      selectedItemBuilder: (_) => closed,
      onChanged: onChanged,
      decoration: InputDecoration(labelText: label, errorText: errorText),
    );
  }
}
