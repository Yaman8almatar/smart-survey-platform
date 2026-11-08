import 'package:flutter/material.dart';

import '../../core/api/api_exception.dart';
import '../../theme/tokens.dart';
import '../../widgets/match_badge.dart';
import '../../widgets/state_message.dart';
import '../answer/answer_repository.dart';
import '../answer/survey_start_screen.dart';
import '../auth/auth_models.dart';
import '../auth/auth_repository.dart';
import '../auth/login_screen.dart';
import '../profile/profile_repository.dart';
import '../profile/profile_screen.dart';
import 'surveys_models.dart';
import 'surveys_repository.dart';

/// Surveys the signed-in respondent is eligible for.
class EligibleSurveysScreen extends StatefulWidget {
  const EligibleSurveysScreen({
    super.key,
    required this.authRepository,
    required this.surveysRepository,
    required this.profileRepository,
    required this.answerRepository,
    required this.user,
  });

  final AuthRepository authRepository;
  final SurveysRepository surveysRepository;
  final ProfileRepository profileRepository;
  final AnswerRepository answerRepository;
  final AppUser user;

  @override
  State<EligibleSurveysScreen> createState() => _EligibleSurveysScreenState();
}

class _EligibleSurveysScreenState extends State<EligibleSurveysScreen> {
  late Future<List<EligibleSurvey>> _surveys;
  bool _loggingOut = false;

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
    setState(() => _loggingOut = true);
    await widget.authRepository.logout();
    if (mounted) {
      _openLogin();
    }
  }

  /// Profile edits change which surveys match, so the list reloads on return.
  Future<void> _openProfile() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ProfileScreen(
          authRepository: widget.authRepository,
          surveysRepository: widget.surveysRepository,
          profileRepository: widget.profileRepository,
          answerRepository: widget.answerRepository,
        ),
      ),
    );
    if (mounted) _retry();
  }

  /// An answered survey leaves the list, so it reloads on return.
  Future<void> _openSurvey(EligibleSurvey survey) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SurveyStartScreen(
          answerRepository: widget.answerRepository,
          surveyId: survey.id,
          onSessionExpired: () =>
              _openLogin(notice: 'Your session ended. Please log in again.'),
        ),
      ),
    );
    if (mounted && (ModalRoute.of(context)?.isCurrent ?? false)) _retry();
  }

  /// Removes every route, because the answer flow may be open above this list.
  void _openLogin({String? notice}) {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute<void>(
        builder: (_) => LoginScreen(
          authRepository: widget.authRepository,
          surveysRepository: widget.surveysRepository,
          profileRepository: widget.profileRepository,
          answerRepository: widget.answerRepository,
          notice: notice,
        ),
      ),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.user.displayName),
        actions: [
          IconButton(
            tooltip: 'Your profile',
            icon: const Icon(Icons.account_circle_outlined),
            onPressed: _loggingOut ? null : _openProfile,
          ),
          IconButton(
            tooltip: 'Log out',
            icon: _loggingOut
                ? const SizedBox(
                    width: SsLayout.indicatorSize,
                    height: SsLayout.indicatorSize,
                    child: CircularProgressIndicator(
                      strokeWidth: SsLayout.indicatorStroke,
                      color: SsColors.surfaceRaised,
                    ),
                  )
                : const Icon(Icons.logout),
            onPressed: _loggingOut ? null : _logout,
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
                    StateMessage(
                      icon: Icons.cloud_off_outlined,
                      title: 'Could not load surveys',
                      body: _errorText(snapshot.error),
                      action: FilledButton(
                        onPressed: _retry,
                        child: const Text('Try again'),
                      ),
                    ),
                  ],
                );
              }
              final surveys = snapshot.data ?? const <EligibleSurvey>[];
              if (surveys.isEmpty) {
                return _Scrollable(
                  onRefresh: _refresh,
                  children: [
                    StateMessage(
                      title: 'No surveys match your profile yet.',
                      body:
                          'New surveys appear here when a provider targets '
                          'your age, gender and governorate. A complete '
                          'profile matches more surveys.',
                      action: Align(
                        alignment: AlignmentDirectional.centerStart,
                        child: OutlinedButton.icon(
                          onPressed: _openProfile,
                          icon: const Icon(Icons.account_circle_outlined),
                          label: const Text('Complete your profile'),
                        ),
                      ),
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
                    _SurveyCard(
                      survey: survey,
                      onTap: () => _openSurvey(survey),
                    ),
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
          ? 'Cannot reach the server. Check your connection and try again.'
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

class _SurveyCard extends StatelessWidget {
  const _SurveyCard({required this.survey, required this.onTap});

  final EligibleSurvey survey;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final count = survey.questionCount;

    return Card(
      clipBehavior: Clip.antiAlias,
      child: Semantics(
        button: true,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsetsDirectional.all(SsSpace.s4),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const MatchBadge(),
                      const SizedBox(height: SsSpace.s2),
                      Text(survey.title, style: textTheme.titleMedium),
                      if (survey.description.isNotEmpty) ...[
                        const SizedBox(height: SsSpace.s1),
                        Text(
                          survey.description,
                          style: textTheme.bodyMedium?.copyWith(
                            color: SsColors.inkMuted,
                          ),
                        ),
                      ],
                      const SizedBox(height: SsSpace.s2),
                      Text(
                        count == 1 ? '1 question' : '$count questions',
                        style: textTheme.bodySmall?.copyWith(
                          color: SsColors.inkMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: SsSpace.s2),
                const Icon(Icons.chevron_right, color: SsColors.inkMuted),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
