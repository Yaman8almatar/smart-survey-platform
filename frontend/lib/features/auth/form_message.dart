import 'package:flutter/material.dart';

/// A short status or error line shown inside an auth form.
class FormMessage extends StatelessWidget {
  const FormMessage({super.key, required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Text(
        text,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: color),
      ),
    );
  }
}
