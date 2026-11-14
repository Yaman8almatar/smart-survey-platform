import 'package:flutter/material.dart';

import '../../core/api/api_exception.dart';
import '../../theme/tokens.dart';
import '../../widgets/refreshable_list.dart';
import '../../widgets/state_message.dart';
import '../answer/survey_sent_screen.dart';
import 'surveys_models.dart';
import 'surveys_repository.dart';

/// Surveys the signed-in respondent has sent (UC-06), newest first.
class AnsweredSurveysScreen extends StatefulWidget {
  const AnsweredSurveysScreen({
    super.key,
    required this.surveysRepository,
    required this.onSessionExpired,
    this.clock = DateTime.now,
  });

  final SurveysRepository surveysRepository;
  final VoidCallback onSessionExpired;

  /// The current time; tests pass a fixed one.
  final DateTime Function() clock;

  @override
  State<AnsweredSurveysScreen> createState() => _AnsweredSurveysScreenState();
}

class _AnsweredSurveysScreenState extends State<AnsweredSurveysScreen> {
  late Future<List<AnsweredSurvey>> _surveys;

  @override
  void initState() {
    super.initState();
    _surveys = _fetch();
  }

  Future<List<AnsweredSurvey>> _fetch() async {
    try {
      return await widget.surveysRepository.answeredSurveys();
    } on SessionExpiredException {
      if (mounted) widget.onSessionExpired();
      return const [];
    }
  }

  void _retry() {
    final next = _fetch();
    setState(() {
      _surveys = next;
    });
  }

  Future<void> _refresh() async {
    final next = _fetch();
    setState(() {
      _surveys = next;
    });
    try {
      await next;
    } on ApiException {
      // The error state shows the failure; the indicator just stops.
    }
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Answered surveys')),
      body: Align(
        alignment: AlignmentDirectional.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: SsLayout.contentMaxWidth),
          child: FutureBuilder<List<AnsweredSurvey>>(
            future: _surveys,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return RefreshableList(
                  onRefresh: _refresh,
                  children: [
                    StateMessage(
                      icon: Icons.cloud_off_outlined,
                      title: 'Could not load answered surveys',
                      body: _errorText(snapshot.error),
                      action: FilledButton(
                        onPressed: _retry,
                        child: const Text('Try again'),
                      ),
                    ),
                  ],
                );
              }
              final surveys = snapshot.data ?? const <AnsweredSurvey>[];
              if (surveys.isEmpty) {
                return RefreshableList(
                  onRefresh: _refresh,
                  children: [
                    StateMessage(
                      title: 'No answered surveys yet.',
                      body:
                          'Surveys you send appear here with the day you '
                          'sent them.',
                      action: Align(
                        alignment: AlignmentDirectional.centerStart,
                        child: OutlinedButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: const Text('See surveys that match you'),
                        ),
                      ),
                    ),
                  ],
                );
              }
              return RefreshableList(
                onRefresh: _refresh,
                children: [
                  Text('Surveys you answered', style: textTheme.displaySmall),
                  const SizedBox(height: SsSpace.s2),
                  Text(
                    'You answer each survey once. Sent answers cannot be '
                    'changed.',
                    style: textTheme.bodyMedium?.copyWith(
                      color: SsColors.inkMuted,
                    ),
                  ),
                  const SizedBox(height: SsSpace.s6),
                  for (final survey in surveys) ...[
                    _AnsweredCard(survey: survey, now: widget.clock()),
                    const SizedBox(height: SsSpace.s4),
                  ],
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  /// Only a network failure gets its own words; this screen hides server text.
  String _errorText(Object? error) {
    if (error is ApiException && error.code == ApiException.networkError) {
      return 'Cannot reach the server. Check your connection and try again.';
    }
    return 'Something went wrong. Please try again.';
  }
}

/// A sent survey; it opens nothing, because sent answers cannot change.
class _AnsweredCard extends StatelessWidget {
  const _AnsweredCard({required this.survey, required this.now});

  final AnsweredSurvey survey;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Card(
      child: Padding(
        padding: const EdgeInsetsDirectional.all(SsSpace.s4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(survey.title, style: textTheme.titleMedium),
            if (survey.description.isNotEmpty) ...[
              const SizedBox(height: SsSpace.s1),
              Text(
                survey.description,
                style: textTheme.bodyMedium?.copyWith(color: SsColors.inkMuted),
              ),
            ],
            const SizedBox(height: SsSpace.s2),
            Row(
              children: [
                const Icon(
                  Icons.check_circle_outline,
                  size: SsLayout.iconSmall,
                  color: SsColors.brand,
                ),
                const SizedBox(width: SsSpace.s2),
                Expanded(
                  child: Text(
                    sentAtText(survey.submittedAt, now),
                    style: textTheme.bodySmall?.copyWith(
                      color: SsColors.inkMuted,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
