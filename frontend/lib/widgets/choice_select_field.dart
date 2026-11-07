import 'package:flutter/material.dart';

import '../features/profile/profile_models.dart';
import '../theme/app_theme.dart';
import '../theme/tokens.dart';

/// Answers set apart from the rest of their list by a divider above them.
const Set<String> setApartCodes = {'PREFER_NOT_TO_SAY', 'OUTSIDE_SYRIA'};

/// A dropdown over `{code, label}` options: shows the label, reports the code.
class ChoiceSelectField extends StatelessWidget {
  const ChoiceSelectField({
    super.key,
    required this.label,
    required this.options,
    required this.value,
    required this.onChanged,
    this.errorText,
  });

  final String label;
  final List<ChoiceOption> options;

  /// The selected code, or null when nothing is chosen.
  final String? value;

  /// Null disables the field.
  final ValueChanged<String?>? onChanged;
  final String? errorText;

  @override
  Widget build(BuildContext context) {
    final items = <DropdownMenuItem<String>>[];
    final closed = <Widget>[];
    for (final option in options) {
      if (setApartCodes.contains(option.code)) {
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
      // The closed field shows the value in regular weight; colour stays the dropdown's.
      closed.add(Text(option.label, style: SsType.body));
    }

    // The menu paints the selected item with the theme focus colour.
    return Theme(
      data: Theme.of(context).copyWith(focusColor: SsColors.brandTint),
      child: DropdownButtonFormField<String>(
        initialValue: value,
        isExpanded: true,
        items: items,
        selectedItemBuilder: (_) => closed,
        onChanged: onChanged,
        icon: const Icon(Icons.expand_more),
        borderRadius: BorderRadius.circular(SsRadius.md),
        decoration: InputDecoration(labelText: label, errorText: errorText),
      ),
    );
  }
}
