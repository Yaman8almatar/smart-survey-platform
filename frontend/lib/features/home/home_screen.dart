import 'package:flutter/material.dart';

import '../../theme/tokens.dart';

/// SAMPLE DATA ONLY: placeholder surveys until the REST API arrives in Sprint 1.
const List<_SampleSurvey> _sampleSurveys = [
  _SampleSurvey(
    title: 'Customer Experience Feedback',
    meta: '5 questions · about 2 min',
  ),
  _SampleSurvey(
    title: 'Campus Services Survey',
    meta: '5 questions · about 2 min',
  ),
];

/// Placeholder home screen listing surveys that match the respondent.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Smart Survey')),
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: ListView(
            padding: const EdgeInsets.all(SsSpace.s4),
            children: [
              const SizedBox(height: SsSpace.s2),
              Text('Surveys that match you', style: textTheme.displaySmall),
              const SizedBox(height: SsSpace.s6),
              for (final survey in _sampleSurveys) ...[
                _SurveyCard(survey: survey),
                const SizedBox(height: SsSpace.s4),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _SampleSurvey {
  const _SampleSurvey({required this.title, required this.meta});

  final String title;
  final String meta;
}

class _SurveyCard extends StatelessWidget {
  const _SurveyCard({required this.survey});

  final _SampleSurvey survey;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(SsSpace.s4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _MatchBadge(),
            const SizedBox(height: SsSpace.s2),
            Text(survey.title, style: textTheme.titleMedium),
            const SizedBox(height: SsSpace.s1),
            Text(
              survey.meta,
              style: textTheme.bodySmall?.copyWith(color: SsColors.inkMuted),
            ),
            const SizedBox(height: SsSpace.s4),
            Align(
              alignment: AlignmentDirectional.centerEnd,
              child: FilledButton(
                // Navigation to the survey form arrives with the real screens.
                onPressed: () {},
                child: const Text('Start'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MatchBadge extends StatelessWidget {
  const _MatchBadge();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: SsColors.accent,
        borderRadius: BorderRadius.circular(SsRadius.pill),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
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
