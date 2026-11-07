import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../theme/tokens.dart';

/// Empty, error and info message shared by every screen: icon, title, optional body and action.
class StateMessage extends StatelessWidget {
  const StateMessage({
    super.key,
    this.icon,
    required this.title,
    this.body,
    this.action,
  });

  static const double _iconCircle = 56;
  static const double _iconSize = 28;

  final IconData? icon;
  final String title;
  final String? body;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final body = this.body;
    final action = this.action;

    final parts = <Widget>[
      if (icon != null)
        Container(
          width: _iconCircle,
          height: _iconCircle,
          decoration: const BoxDecoration(
            color: SsColors.brandTint,
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: _iconSize, color: SsColors.brand),
        ),
      Text(
        title,
        textAlign: TextAlign.center,
        style: SsType.heading.copyWith(color: SsColors.ink),
      ),
      if (body != null)
        Text(
          body,
          textAlign: TextAlign.center,
          style: SsType.body.copyWith(color: SsColors.inkMuted),
        ),
      ?action,
    ];

    return Padding(
      padding: const EdgeInsetsDirectional.symmetric(vertical: SsSpace.s6),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < parts.length; i++) ...[
            if (i > 0) const SizedBox(height: SsSpace.s4),
            parts[i],
          ],
        ],
      ),
    );
  }
}
