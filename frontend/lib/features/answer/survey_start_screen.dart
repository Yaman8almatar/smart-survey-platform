import 'package:flutter/material.dart';

import '../../core/api/api_exception.dart';
import '../../theme/app_theme.dart';
import '../../theme/tokens.dart';
import '../../widgets/match_badge.dart';
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
  SurveyBlock? _block;
  ApiException? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final detail = await widget.answerRepository.survey(widget.surveyId);
      if (!mounted) return;
      setState(() {
        _detail = detail;
        _phase = _Phase.content;
      });
    } on SessionExpiredException {
      if (mounted) widget.onSessionExpired();
    } on ApiException catch (error) {
      if (!mounted) return;
      final block = surveyBlockFor(error, sending: false);
      setState(() {
        _block = block;
        _error = error;
        _phase = block == null ? _Phase.error : _Phase.blocked;
      });
    }
  }

  void _retry() {
    setState(() => _phase = _Phase.loading);
    _load();
  }

  void _start() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SurveyAnswerScreen(
          answerRepository: widget.answerRepository,
          survey: _detail!,
          onSessionExpired: widget.onSessionExpired,
        ),
      ),
    );
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
          ? AnswerBottomBar(
              children: [
                FilledButton(
                  onPressed: _start,
                  child: const Text('Start survey'),
                ),
              ],
            )
          : null,
    );
  }
}

class _Content extends StatelessWidget {
  const _Content({super.key, required this.survey});

  final SurveyDetail survey;

  @override
  Widget build(BuildContext context) {
    final count = survey.questions.length;
    final optional = survey.optionalCount;
    const muted = SsColors.onBrandMuted;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HeroBand(
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
                  Text(
                    survey.description,
                    style: SsType.body.copyWith(color: muted),
                  ),
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
          ),
          const RisingSheet(
            child: ProfileContentWidth(
              child: Padding(
                padding: EdgeInsetsDirectional.symmetric(
                  horizontal: SsSpace.s4,
                  vertical: SsSpace.s5,
                ),
                child: _Rules(),
              ),
            ),
          ),
        ],
      ),
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

class _Rules extends StatelessWidget {
  const _Rules();

  @override
  Widget build(BuildContext context) {
    const divider = Divider(
      height: SsSpace.s6,
      thickness: SsLayout.hairline,
      color: SsColors.line,
    );
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
        divider,
        const _Rule(
          icon: Icons.lock_outline,
          title: 'One response per survey',
          body: "You can't change your answers after you send them.",
        ),
        divider,
        const _Rule(
          icon: Icons.exit_to_app,
          title: 'Finish in one go',
          body: 'If you leave before sending, your answers are not kept.',
        ),
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
