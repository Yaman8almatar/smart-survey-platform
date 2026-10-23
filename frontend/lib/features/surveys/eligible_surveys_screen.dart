import 'package:flutter/material.dart';

import '../../core/api/api_exception.dart';
import '../../theme/tokens.dart';
import '../auth/auth_models.dart';
import '../auth/auth_repository.dart';
import '../auth/login_screen.dart';
import 'surveys_models.dart';
import 'surveys_repository.dart';

/// Surveys the signed-in respondent is eligible for.
class EligibleSurveysScreen extends StatefulWidget {
  const EligibleSurveysScreen({
    super.key,
    required this.authRepository,
    required this.surveysRepository,
    required this.user,
  });

  final AuthRepository authRepository;
  final SurveysRepository surveysRepository;
  final AppUser user;

  @override
  State<EligibleSurveysScreen> createState() => _EligibleSurveysScreenState();
}

class _EligibleSurveysScreenState extends State<EligibleSurveysScreen> {
  late Future<List<EligibleSurvey>> _surveys;

  @override
  void initState() {
    super.initState();
    _surveys = _fetch();
  }

  Future<List<EligibleSurvey>> _fetch() async {
    try {
      return await widget.surveysRepository.eligibleSurveys();
    } on SessionExpiredException {
      if (mounted) {
        _openLogin(notice: 'Your session ended. Please log in again.');
      }
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

  Future<void> _logout() async {
    await widget.authRepository.logout();
    if (mounted) {
      _openLogin();
    }
  }

  void _openLogin({String? notice}) {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => LoginScreen(
          authRepository: widget.authRepository,
          surveysRepository: widget.surveysRepository,
          notice: notice,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.user.displayName),
        actions: [
          IconButton(
            tooltip: 'Log out',
            icon: const Icon(Icons.logout),
            onPressed: _logout,
          ),
        ],
      ),
      body: Align(
        alignment: AlignmentDirectional.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: SsLayout.contentMaxWidth),
          child: FutureBuilder<List<EligibleSurvey>>(
            future: _surveys,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return _Scrollable(
                  onRefresh: _refresh,
                  children: [
                    _StateMessage(
                      title: 'Could not load surveys',
                      body: _errorText(snapshot.error),
                      action: FilledButton(
                        onPressed: _retry,
                        child: const Text('Retry'),
                      ),
                    ),
                  ],
                );
              }
              final surveys = snapshot.data ?? const <EligibleSurvey>[];
              if (surveys.isEmpty) {
                return _Scrollable(
                  onRefresh: _refresh,
                  children: const [
                    _StateMessage(
                      title: 'No surveys match your profile yet.',
                      body:
                          'New surveys appear here when a provider targets '
                          'your age, gender and region.',
                    ),
                  ],
                );
              }
              return _Scrollable(
                onRefresh: _refresh,
                children: [
                  Text(
                    'Surveys that match you',
                    style: Theme.of(context).textTheme.displaySmall,
                  ),
                  const SizedBox(height: SsSpace.s6),
                  for (final survey in surveys) ...[
                    _SurveyCard(survey: survey),
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

  String _errorText(Object? error) {
    if (error is ApiException) {
      return error.code == ApiException.networkError
          ? 'Cannot reach the server. Is it running?'
          : error.message;
    }
    return 'Something went wrong. Please try again.';
  }
}

/// Always scrollable so pull-to-refresh also works on short content.
class _Scrollable extends StatelessWidget {
  const _Scrollable({required this.onRefresh, required this.children});

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

class _StateMessage extends StatelessWidget {
  const _StateMessage({required this.title, required this.body, this.action});

  final String title;
  final String body;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: SsSpace.s6),
        Text(title, style: textTheme.titleMedium),
        const SizedBox(height: SsSpace.s2),
        Text(
          body,
          style: textTheme.bodyMedium?.copyWith(color: SsColors.inkMuted),
        ),
        if (action != null) ...[const SizedBox(height: SsSpace.s4), action!],
      ],
    );
  }
}

class _SurveyCard extends StatelessWidget {
  const _SurveyCard({required this.survey});

  final EligibleSurvey survey;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final count = survey.questionCount;

    return Card(
      child: Padding(
        padding: const EdgeInsetsDirectional.all(SsSpace.s4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _MatchBadge(),
            const SizedBox(height: SsSpace.s2),
            Text(survey.title, style: textTheme.titleMedium),
            if (survey.description.isNotEmpty) ...[
              const SizedBox(height: SsSpace.s1),
              Text(
                survey.description,
                style: textTheme.bodyMedium?.copyWith(color: SsColors.inkMuted),
              ),
            ],
            const SizedBox(height: SsSpace.s2),
            Text(
              count == 1 ? '1 question' : '$count questions',
              style: textTheme.bodySmall?.copyWith(color: SsColors.inkMuted),
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
        padding: const EdgeInsetsDirectional.symmetric(
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
