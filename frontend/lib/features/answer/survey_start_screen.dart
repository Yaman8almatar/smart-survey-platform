import 'package:flutter/material.dart';

import '../../core/api/api_exception.dart';
import '../../theme/app_theme.dart';
import '../../theme/tokens.dart';
import '../../widgets/match_badge.dart';
import '../../widgets/signal_ring.dart';
import '../profile/profile_hero.dart';
import 'answer_models.dart';
import 'answer_repository.dart';
import 'survey_answer_screen.dart';
import 'survey_parts.dart';

enum _Phase { loading, error, blocked, content }

/// FR-01: what a survey asks and the rules, before the first question.
class SurveyStartScreen extends StatefulWidget {
  const SurveyStartScreen({
    super.key,
    required this.answerRepository,
    required this.surveyId,
    required this.onSessionExpired,
  });

  final AnswerRepository answerRepository;
  final int surveyId;
  final VoidCallback onSessionExpired;

  @override
  State<SurveyStartScreen> createState() => _SurveyStartScreenState();
}

class _SurveyStartScreenState extends State<SurveyStartScreen> {
  _Phase _phase = _Phase.loading;
  SurveyDetail? _detail;
  SurveyDraft? _draft;
  SurveyBlock? _block;
  ApiException? _error;
  bool _deleting = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait<Object?>([
        widget.answerRepository.survey(widget.surveyId),
        widget.answerRepository.draft(widget.surveyId),
      ]);
      if (!mounted) return;
      final detail = results[0] as SurveyDetail;
      final draft = results[1] as SurveyDraft?;
      setState(() {
        _detail = detail;
        _draft = draft?.keptFor(detail);
        _phase = _Phase.content;
      });
    } on SessionExpiredException {
      if (mounted) widget.onSessionExpired();
    } on ApiException catch (error) {
      if (mounted) _showLoadError(error);
    }
  }

  void _showLoadError(ApiException error) {
    final block = surveyBlockFor(error, sending: false);
    setState(() {
      _block = block;
      _error = error;
      _phase = block == null ? _Phase.error : _Phase.blocked;
    });
  }

  void _retry() {
    setState(() => _phase = _Phase.loading);
    _load();
  }

  /// Opens the questions; coming back loads what was saved meanwhile.
  Future<void> _open({
    Map<int, Answer> answers = const {},
    int index = 0,
  }) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SurveyAnswerScreen(
          answerRepository: widget.answerRepository,
          survey: _detail!,
          initialAnswers: answers,
          initialIndex: index,
          onSessionExpired: widget.onSessionExpired,
        ),
      ),
    );
    if (mounted) _retry();
  }

  void _continue() {
    final answers = _draft!.answers;
    final questions = _detail!.questions;
    final next = questions.indexWhere((q) => !answers.containsKey(q.id));
    _open(answers: answers, index: next == -1 ? questions.length : next);
  }

  Future<void> _startOver() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Start over?'),
        content: const Text('Your saved answers will be deleted.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            style: TextButton.styleFrom(foregroundColor: SsColors.danger),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Start over'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _deleting = true);
    try {
      await widget.answerRepository.deleteDraft(widget.surveyId);
      if (!mounted) return;
      setState(() => _deleting = false);
      _open();
    } on SessionExpiredException {
      if (mounted) widget.onSessionExpired();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _deleting = false);
      if (error.code != ApiException.networkError) {
        _showLoadError(error);
        return;
      }
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          const SnackBar(
            content: Text(
              'Cannot reach the server. Check your connection and try again.',
            ),
          ),
        );
    }
  }

  String get _errorBody {
    final error = _error;
    return error == null || error.code == ApiException.networkError
        ? 'Cannot reach the server. Check your connection and try again.'
        : error.message;
  }

  @override
  Widget build(BuildContext context) {
    final content = _phase == _Phase.content;
    final Widget body = switch (_phase) {
      _Phase.loading => const Center(
        key: ValueKey(_Phase.loading),
        child: CircularProgressIndicator(),
      ),
      _Phase.error => SurveyStateBody(
        key: const ValueKey(_Phase.error),
        icon: Icons.cloud_off_outlined,
        title: 'Could not load this survey',
        body: _errorBody,
        action: FilledButton(onPressed: _retry, child: const Text('Try again')),
      ),
      _Phase.blocked => SurveyBlockedBody(
        key: const ValueKey(_Phase.blocked),
        block: _block!,
      ),
      _Phase.content => _Content(
        key: const ValueKey(_Phase.content),
        survey: _detail!,
        draft: _draft,
      ),
    };

    return Scaffold(
      backgroundColor: content ? SsColors.surfaceRaised : null,
      appBar: AppBar(title: const Text('Survey')),
      body: AnimatedSwitcher(
        duration: SsMotion.of(context, SsMotion.standard),
        layoutBuilder: (current, previous) => Stack(
          alignment: AlignmentDirectional.topCenter,
          children: [...previous, ?current],
        ),
        child: body,
      ),
      bottomNavigationBar: content
          ? AnswerBottomBar(children: [_buildActions()])
          : null,
    );
  }

  Widget _buildActions() {
    if (_draft == null) {
      return FilledButton(onPressed: _open, child: const Text('Start survey'));
    }
    return Row(
      children: [
        OutlinedButton.icon(
          onPressed: _deleting ? null : _startOver,
          icon: const Icon(Icons.restart_alt),
          label: const Text('Start over'),
        ),
        const SizedBox(width: SsSpace.s3),
        Expanded(
          child: FilledButton(
            onPressed: _deleting ? null : _continue,
            child: const Text('Continue'),
          ),
        ),
      ],
    );
  }
}

class _Content extends StatelessWidget {
  const _Content({super.key, required this.survey, required this.draft});

  final SurveyDetail survey;
  final SurveyDraft? draft;

  @override
  Widget build(BuildContext context) {
    final draft = this.draft;
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HeroBand(
            child: draft == null
                ? _SurveyHero(survey: survey)
                : _DraftHero(survey: survey, draft: draft),
          ),
          RisingSheet(
            child: ProfileContentWidth(
              child: Padding(
                padding: const EdgeInsetsDirectional.symmetric(
                  horizontal: SsSpace.s4,
                  vertical: SsSpace.s5,
                ),
                child: draft == null ? const _Rules() : const _DraftRules(),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SurveyHero extends StatelessWidget {
  const _SurveyHero({required this.survey});

  final SurveyDetail survey;

  @override
  Widget build(BuildContext context) {
    final count = survey.questions.length;
    final optional = survey.optionalCount;
    const muted = SsColors.onBrandMuted;

    return SizedBox(
      width: double.infinity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const MatchBadge(),
          const SizedBox(height: SsSpace.s2),
          Text(
            survey.title,
            style: SsType.title.copyWith(color: SsColors.surfaceRaised),
          ),
          if (survey.description.isNotEmpty) ...[
            const SizedBox(height: SsSpace.s2),
            Text(survey.description, style: SsType.body.copyWith(color: muted)),
          ],
          const SizedBox(height: SsSpace.s3),
          Wrap(
            spacing: SsSpace.s4,
            runSpacing: SsSpace.s1,
            children: [
              _Fact(
                icon: Icons.format_list_bulleted,
                text: count == 1 ? '1 question' : '$count questions',
              ),
              if (optional > 0)
                _Fact(icon: Icons.last_page, text: '$optional optional'),
            ],
          ),
        ],
      ),
    );
  }
}

class _DraftHero extends StatelessWidget {
  const _DraftHero({required this.survey, required this.draft});

  final SurveyDetail survey;
  final SurveyDraft draft;

  @override
  Widget build(BuildContext context) {
    final answered = draft.answers.length;
    final total = survey.questions.length;
    final questions =
        '$answered of $total '
        '${total == 1 ? 'question' : 'questions'}';
    final day = dayPhrase(draft.updatedAt.toLocal(), DateTime.now());

    return Row(
      children: [
        ExcludeSemantics(
          child: SignalRing(
            value: answered * 100 ~/ total,
            size: SsLayout.ringSize,
            centerLabel: '$answered/$total',
            semanticLabel: '$questions answered',
            ping: false,
          ),
        ),
        const SizedBox(width: SsSpace.s3),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                survey.title,
                style: SsType.title.copyWith(color: SsColors.surfaceRaised),
              ),
              const SizedBox(height: SsSpace.s1),
              Text(
                'You answered $questions $day.',
                style: SsType.body.copyWith(color: SsColors.onBrandMuted),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Fact extends StatelessWidget {
  const _Fact({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    const muted = SsColors.onBrandMuted;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: SsLayout.iconSmall, color: muted),
        const SizedBox(width: SsSpace.s1),
        Text(text, style: SsType.label.copyWith(color: muted)),
      ],
    );
  }
}

const Divider _ruleDivider = Divider(
  height: SsSpace.s6,
  thickness: SsLayout.hairline,
  color: SsColors.line,
);

const _Rule _oneResponseRule = _Rule(
  icon: Icons.lock_outline,
  title: 'One response per survey',
  body: "You can't change your answers after you send them.",
);

const _Rule _savedRule = _Rule(
  icon: Icons.save_outlined,
  title: 'Saved as you go',
  body: 'Your answers are kept until you send them or the survey closes.',
);

class _DraftRules extends StatelessWidget {
  const _DraftRules();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Your draft', style: SsType.heading.copyWith(color: SsColors.ink)),
        const SizedBox(height: SsSpace.s4),
        _savedRule,
        _ruleDivider,
        _oneResponseRule,
      ],
    );
  }
}

class _Rules extends StatelessWidget {
  const _Rules();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Before you start',
          style: SsType.heading.copyWith(color: SsColors.ink),
        ),
        const SizedBox(height: SsSpace.s4),
        const _Rule(
          icon: Icons.article_outlined,
          title: 'One question at a time',
          body:
              'Optional questions can be skipped. You can go back until you '
              'send.',
        ),
        _ruleDivider,
        _oneResponseRule,
        _ruleDivider,
        _savedRule,
      ],
    );
  }
}

class _Rule extends StatelessWidget {
  const _Rule({required this.icon, required this.title, required this.body});

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: SsSpace.s10,
          height: SsSpace.s10,
          decoration: const BoxDecoration(
            color: SsColors.brandTint,
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: SsLayout.iconMedium, color: SsColors.brand),
        ),
        const SizedBox(width: SsSpace.s3),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: SsType.body.copyWith(
                  color: SsColors.ink,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(body, style: SsType.body.copyWith(color: SsColors.inkMuted)),
            ],
          ),
        ),
      ],
    );
  }
}
