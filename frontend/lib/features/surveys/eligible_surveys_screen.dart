import 'package:flutter/material.dart';

import '../../core/api/api_exception.dart';
import '../../theme/tokens.dart';
import '../../widgets/match_badge.dart';
import '../../widgets/refreshable_list.dart';
import '../../widgets/state_message.dart';
import '../answer/answer_repository.dart';
import '../answer/survey_start_screen.dart';
import '../auth/auth_models.dart';
import '../auth/auth_repository.dart';
import '../auth/login_screen.dart';
import '../profile/profile_repository.dart';
import '../profile/profile_screen.dart';
import 'answered_surveys_screen.dart';
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
    this.today,
  });

  final AuthRepository authRepository;
  final SurveysRepository surveysRepository;
  final ProfileRepository profileRepository;
  final AnswerRepository answerRepository;
  final AppUser user;

  /// The current date for "New this week"; tests fix it, the app uses the device's.
  final DateTime Function()? today;

  @override
  State<EligibleSurveysScreen> createState() => _EligibleSurveysScreenState();
}

/// The FR-08 chips; exactly one is selected.
enum _ListFilter {
  all('All'),
  underFive('Under 5 min'),
  newThisWeek('New this week');

  const _ListFilter(this.label);

  final String label;
}

class _EligibleSurveysScreenState extends State<EligibleSurveysScreen> {
  static const int _shortMinutes = 5;
  static const int _weekDays = 7;

  late Future<List<EligibleSurvey>> _surveys;
  bool _loggingOut = false;
  final TextEditingController _search = TextEditingController();
  _ListFilter _filter = _ListFilter.all;

  @override
  void initState() {
    super.initState();
    _surveys = _fetch();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  /// The surveys passing the search text and the chip, in the server's order.
  List<EligibleSurvey> _visible(List<EligibleSurvey> surveys) {
    final query = _search.text.trim().toLowerCase();
    final now = (widget.today ?? DateTime.now)();
    final today = DateTime(now.year, now.month, now.day);
    final weekStart = DateTime(now.year, now.month, now.day - (_weekDays - 1));

    bool passesChip(EligibleSurvey survey) {
      switch (_filter) {
        case _ListFilter.all:
          return true;
        case _ListFilter.underFive:
          return survey.expectedMinutes < _shortMinutes;
        case _ListFilter.newThisWeek:
          final published = survey.publishedOn;
          return published != null &&
              !published.isBefore(weekStart) &&
              !published.isAfter(today);
      }
    }

    return [
      for (final survey in surveys)
        if ((query.isEmpty ||
                survey.title.toLowerCase().contains(query) ||
                survey.description.toLowerCase().contains(query)) &&
            passesChip(survey))
          survey,
    ];
  }

  void _clearSearch() {
    setState(() {
      _search.clear();
      _filter = _ListFilter.all;
    });
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

  /// Read-only history, so the list does not reload on return.
  void _openAnswered() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => AnsweredSurveysScreen(
          surveysRepository: widget.surveysRepository,
          onSessionExpired: () =>
              _openLogin(notice: 'Your session ended. Please log in again.'),
        ),
      ),
    );
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
            tooltip: 'Answered surveys',
            icon: const Icon(Icons.history),
            onPressed: _loggingOut ? null : _openAnswered,
          ),
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
                return RefreshableList(
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
                return RefreshableList(
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
              final visible = _visible(surveys);
              return RefreshableList(
                onRefresh: _refresh,
                children: [
                  Text(
                    'Surveys that match you',
                    style: Theme.of(context).textTheme.displaySmall,
                  ),
                  const SizedBox(height: SsSpace.s6),
                  TextField(
                    controller: _search,
                    onChanged: (_) => setState(() {}),
                    textInputAction: TextInputAction.search,
                    decoration: const InputDecoration(
                      hintText: 'Search surveys',
                      prefixIcon: Icon(Icons.search),
                    ),
                  ),
                  const SizedBox(height: SsSpace.s3),
                  Wrap(
                    spacing: SsSpace.s2,
                    runSpacing: SsSpace.s2,
                    children: [
                      for (final filter in _ListFilter.values)
                        ChoiceChip(
                          label: Text(filter.label),
                          selected: _filter == filter,
                          onSelected: (_) => setState(() => _filter = filter),
                        ),
                    ],
                  ),
                  const SizedBox(height: SsSpace.s6),
                  if (visible.isEmpty)
                    StateMessage(
                      title: 'No surveys match your search.',
                      action: Align(
                        alignment: AlignmentDirectional.centerStart,
                        child: OutlinedButton(
                          onPressed: _clearSearch,
                          child: const Text('Clear search'),
                        ),
                      ),
                    ),
                  for (final survey in visible) ...[
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

class _SurveyCard extends StatelessWidget {
  const _SurveyCard({required this.survey, required this.onTap});

  static const _months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', //
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];

  final EligibleSurvey survey;
  final VoidCallback onTap;

  /// " · Closes 30 Nov" when the survey has a closing date (FR-11), else ''.
  static String _closesSuffix(DateTime? closesOn) => closesOn == null
      ? ''
      : ' · Closes ${closesOn.day} ${_months[closesOn.month - 1]}';

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
                        '${count == 1 ? '1 question' : '$count questions'}'
                        ' · About ${survey.expectedMinutes} min'
                        '${_closesSuffix(survey.closesOn)}',
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
