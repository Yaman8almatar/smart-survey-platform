import 'package:flutter/material.dart';

import '../../core/api/api_exception.dart';
import '../../theme/app_theme.dart';
import '../../theme/tokens.dart';
import '../../widgets/state_message.dart';
import '../profile/profile_hero.dart';

const List<String> _months = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/// "today", "on 7 November", or "on 7 November 2025" for another year,
/// for a [local] time.
String dayPhrase(DateTime local, DateTime now) {
  final today =
      local.year == now.year &&
      local.month == now.month &&
      local.day == now.day;
  if (today) return 'today';
  final year = local.year == now.year ? '' : ' ${local.year}';
  return 'on ${local.day} ${_months[local.month - 1]}$year';
}

/// Why a survey cannot be answered: the words that replace the screen.
class SurveyBlock {
  const SurveyBlock({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;
}

/// The block for an API result, or null when the screen should stay.
SurveyBlock? surveyBlockFor(ApiException error, {required bool sending}) {
  return switch (error.code) {
    'duplicate_response' => const SurveyBlock(
      icon: Icons.check,
      title: 'You already answered this survey',
      body: 'Each survey takes one response from you.',
    ),
    'not_editable' => SurveyBlock(
      icon: Icons.lock_outline,
      title: 'This survey is closed',
      body: sending
          ? 'It stopped taking answers before yours arrived, so they were '
                'not saved.'
          : 'It no longer takes answers.',
    ),
    'unauthorized_action' => const SurveyBlock(
      icon: Icons.info_outline,
      title: 'This survey no longer matches your profile',
      body: 'The survey or your profile changed after the list was loaded.',
    ),
    'survey_not_found' => const SurveyBlock(
      icon: Icons.info_outline,
      title: 'This survey is not available',
      body: 'It may have been removed.',
    ),
    _ => null,
  };
}

/// Returns to the survey list at the bottom of the navigator.
void backToSurveys(BuildContext context) {
  Navigator.of(context).popUntil((route) => route.isFirst);
}

/// A full-screen message within the content width.
class SurveyStateBody extends StatelessWidget {
  const SurveyStateBody({
    super.key,
    required this.icon,
    required this.title,
    required this.body,
    required this.action,
  });

  final IconData icon;
  final String title;
  final String body;
  final Widget action;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsetsDirectional.all(SsSpace.s4),
      child: ProfileContentWidth(
        child: Align(
          alignment: AlignmentDirectional.centerStart,
          child: StateMessage(
            icon: icon,
            title: title,
            body: body,
            action: action,
          ),
        ),
      ),
    );
  }
}

/// The message for a [SurveyBlock], with its way back to the list.
class SurveyBlockedBody extends StatelessWidget {
  const SurveyBlockedBody({super.key, required this.block});

  final SurveyBlock block;

  @override
  Widget build(BuildContext context) {
    return SurveyStateBody(
      icon: block.icon,
      title: block.title,
      body: block.body,
      action: FilledButton(
        onPressed: () => backToSurveys(context),
        child: const Text('Back to surveys'),
      ),
    );
  }
}

/// The bar under the answer flow's screens, as wide as their content.
class AnswerBottomBar extends StatelessWidget {
  const AnswerBottomBar({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: SsColors.surfaceRaised,
        border: Border(
          top: BorderSide(color: SsColors.line, width: SsLayout.hairline),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Align(
          alignment: AlignmentDirectional.topCenter,
          heightFactor: 1,
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: SsLayout.contentMaxWidth,
            ),
            child: Padding(
              padding: const EdgeInsetsDirectional.fromSTEB(
                SsSpace.s4,
                SsSpace.s3,
                SsSpace.s4,
                SsSpace.s4,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: children,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// A danger line with an alert icon, announced when it appears.
class AnswerAlertLine extends StatelessWidget {
  const AnswerAlertLine({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Row(
        children: [
          const Icon(
            Icons.error_outline,
            size: SsLayout.iconSmall,
            color: SsColors.danger,
          ),
          const SizedBox(width: SsSpace.s2),
          Expanded(
            child: Text(
              text,
              style: SsType.label.copyWith(color: SsColors.danger),
            ),
          ),
        ],
      ),
    );
  }
}
