import 'package:flutter/material.dart';

import '../theme/tokens.dart';

/// Always scrollable so pull-to-refresh also works on short content.
class RefreshableList extends StatelessWidget {
  const RefreshableList({
    super.key,
    required this.onRefresh,
    required this.children,
  });

  final Future<void> Function() onRefresh;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsetsDirectional.all(SsSpace.s4),
        children: children,
      ),
    );
  }
}
