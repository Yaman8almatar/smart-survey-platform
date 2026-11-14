import 'package:flutter/material.dart';

import '../core/text_direction.dart';
import '../theme/app_theme.dart';
import '../theme/tokens.dart';

/// The longest open answer the API accepts.
const int maxOpenTextLength = 2000;

/// A multi-line answer whose direction follows the language typed.
class OpenTextField extends StatefulWidget {
  const OpenTextField({
    super.key,
    required this.initialText,
    required this.onChanged,
    this.error = false,
  });

  final String initialText;
  final ValueChanged<String> onChanged;

  /// Marks a required question that was left without an answer.
  final bool error;

  @override
  State<OpenTextField> createState() => _OpenTextFieldState();
}

class _OpenTextFieldState extends State<OpenTextField> {
  late final TextEditingController _controller = TextEditingController(
    text: widget.initialText,
  );
  bool _atLimit = false;

  @override
  void initState() {
    super.initState();
    _atLimit = _controller.text.characters.length >= maxOpenTextLength;
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _changed(String text) {
    setState(() {
      _atLimit = text.characters.length >= maxOpenTextLength;
    });
    widget.onChanged(text);
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: _controller,
      maxLength: maxOpenTextLength,
      minLines: 5,
      maxLines: 5,
      keyboardType: TextInputType.multiline,
      textDirection: directionOf(_controller.text),
      onChanged: _changed,
      buildCounter:
          (
            context, {
            required currentLength,
            required isFocused,
            required maxLength,
          }) => Text(
            '$currentLength / $maxLength',
            style: SsType.caption.copyWith(
              color: _atLimit ? SsColors.danger : SsColors.inkMuted,
            ),
          ),
      decoration: InputDecoration(
        labelText: 'Your answer',
        alignLabelWithHint: true,
        errorText: _atLimit ? 'You reached the 2,000 character limit.' : null,
        error: !_atLimit && widget.error ? const SizedBox.shrink() : null,
      ),
    );
  }
}
