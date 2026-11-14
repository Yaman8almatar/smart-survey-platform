import 'package:flutter/foundation.dart' show mapEquals;
import 'package:flutter/material.dart';

import '../../core/api/api_exception.dart';
import '../../core/text_direction.dart';
import '../../theme/app_theme.dart';
import '../../theme/tokens.dart';
import '../../widgets/answer_option.dart';
import '../../widgets/open_text_field.dart';
import '../../widgets/rating_scale.dart';
import '../../widgets/signal_ring.dart';
import '../profile/profile_hero.dart';
import 'answer_models.dart';
import 'answer_repository.dart';
import 'survey_parts.dart';
import 'survey_sent_screen.dart';

const double _sendingOpacity = 0.55;

const Divider _rowDivider = Divider(
  height: SsLayout.hairline,
  thickness: SsLayout.hairline,
  color: SsColors.line,
);

/// FR-01 and FR-06: one question per screen, then a review before sending.
class SurveyAnswerScreen extends StatefulWidget {
  const SurveyAnswerScreen({
    super.key,
    required this.answerRepository,
    required this.survey,
    required this.onSessionExpired,
    this.initialAnswers = const {},
    this.initialIndex = 0,
  });

  final AnswerRepository answerRepository;
  final SurveyDetail survey;
  final VoidCallback onSessionExpired;

  /// Answers restored from a saved draft.
  final Map<int, Answer> initialAnswers;

  /// The first question shown; `survey.questions.length` means the review.
  final int initialIndex;

  @override
  State<SurveyAnswerScreen> createState() => _SurveyAnswerScreenState();
}

enum _SaveResult { saved, failed, stopped }

class _SurveyAnswerScreenState extends State<SurveyAnswerScreen> {
  /// Holds real answers only: a blank text removes its entry.
  late final Map<int, Answer> _answers = Map.of(widget.initialAnswers);

  /// What the server holds as the draft.
  late Map<int, Answer> _saved = widget.initialAnswers;

  /// The answers of the latest save point, until a save takes them.
  Map<int, Answer>? _queued;
  Future<_SaveResult>? _saveRun;
  bool _leaving = false;

  /// The question shown; `questions.length` means the review.
  late int _index = widget.initialIndex;
  bool _movingForward = true;
  bool _returnToReview = false;
  bool _showRequired = false;

  bool _sending = false;

  /// An earlier send got no answer from the server.
  bool _networkFailed = false;
  Set<int> _needsAnswer = const {};
  String? _sendMessage;
  SurveyBlock? _block;

  List<SurveyQuestion> get _questions => widget.survey.questions;
  bool get _onReview => _index == _questions.length;

  void _goTo(int index) {
    if (_sending || _leaving) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _movingForward = index > _index;
      _index = index;
      _showRequired = false;
    });
    _save();
  }

  /// A save point: at most one request runs, and the newest answers follow it.
  Future<_SaveResult> _save() {
    _queued = Map.of(_answers);
    return _saveRun ??= _runSaves().whenComplete(() => _saveRun = null);
  }

  Future<_SaveResult> _runSaves() async {
    var result = _SaveResult.saved;
    while (mounted && !_sending) {
      final answers = _queued;
      if (answers == null) break;
      _queued = null;
      if (mapEquals(answers, _saved)) {
        result = _SaveResult.saved;
        continue;
      }
      try {
        await widget.answerRepository.saveDraft(widget.survey.id, answers);
        _saved = answers;
        result = _SaveResult.saved;
      } on SessionExpiredException {
        if (mounted && !_sending) widget.onSessionExpired();
        return _SaveResult.stopped;
      } on ApiException catch (error) {
        // During a send the server may already answer 409 for the response itself.
        if (!mounted || _sending) return _SaveResult.stopped;
        final block = surveyBlockFor(error, sending: false);
        if (block != null) {
          setState(() => _block = block);
          return _SaveResult.stopped;
        }
        result = _SaveResult.failed;
      }
    }
    return result;
  }

  void _setAnswer(SurveyQuestion question, Answer? answer) {
    setState(() {
      if (answer == null) {
        _answers.remove(question.id);
      } else {
        _answers[question.id] = answer;
        _showRequired = false;
      }
      _needsAnswer = {..._needsAnswer}..remove(question.id);
      _sendMessage = null;
    });
  }

  void _advance() {
    final question = _questions[_index];
    if (question.isRequired && !_answers.containsKey(question.id)) {
      setState(() => _showRequired = true);
      return;
    }
    if (_returnToReview) {
      _returnToReview = false;
      _goTo(_questions.length);
    } else {
      _goTo(_index + 1);
    }
  }

  void _goBack() {
    _returnToReview = false;
    _goTo(_index - 1);
  }

  void _openFromReview(int index) {
    if (_sending) return;
    _returnToReview = true;
    _goTo(index);
  }

  void _hideSnackBar() {
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
  }

  Future<void> _send() async {
    if (_sending || _leaving) return;
    _hideSnackBar();
    final sent = {
      for (final question in _questions) question.id: ?_answers[question.id],
    };
    setState(() {
      _sending = true;
      _needsAnswer = const {};
      _sendMessage = null;
    });
    try {
      final result = await widget.answerRepository.submit(
        widget.survey.id,
        sent,
      );
      if (mounted) _showSent(sent.length, result.submittedAt);
    } on SessionExpiredException {
      if (mounted) widget.onSessionExpired();
    } on ApiException catch (error) {
      if (mounted) _sendFailed(error, sent.keys.toList());
    }
  }

  void _showSent(int answered, DateTime submittedAt) {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => SurveySentScreen(
          title: widget.survey.title,
          answered: answered,
          total: _questions.length,
          submittedAt: submittedAt,
        ),
      ),
    );
  }

  void _sendFailed(ApiException error, List<int> sentIds) {
    // A send that timed out may still have been saved (K-02).
    if (error.code == 'duplicate_response' && _networkFailed) {
      _showSent(sentIds.length, DateTime.now());
      return;
    }
    if (error.code == ApiException.networkError) _networkFailed = true;
    if (error.code == 'validation_error') {
      final marked = _questionsInError(error, sentIds);
      setState(() {
        _sending = false;
        _needsAnswer = marked;
        _sendMessage = marked.isEmpty ? error.message : null;
      });
      return;
    }
    final block = surveyBlockFor(error, sending: true);
    setState(() {
      _sending = false;
      _block = block;
    });
    if (block != null) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text('Not sent. ${error.message}'),
          action: SnackBarAction(label: 'Try again', onPressed: _send),
        ),
      );
  }

  /// `fields['answers']` lines up with the answers sent; `{}` means that one passed.
  static Set<int> _questionsInError(ApiException error, List<int> sentIds) {
    final rows = error.fields['answers'] ?? const <String>[];
    return {
      for (var i = 0; i < rows.length && i < sentIds.length; i++)
        if (rows[i].startsWith('{') && rows[i] != '{}') sentIds[i],
    };
  }

  Future<void> _leave() async {
    if (_leaving) return;
    setState(() => _leaving = true);
    final result = await _save();
    if (!mounted) return;
    setState(() => _leaving = false);
    switch (result) {
      case _SaveResult.saved:
        _close();
      case _SaveResult.failed:
        await _confirmLeaveUnsaved();
      case _SaveResult.stopped:
        break;
    }
  }

  void _close() {
    _hideSnackBar();
    Navigator.of(context).pop();
  }

  Future<void> _confirmLeaveUnsaved() async {
    final leave = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Leave without saving?'),
        content: const Text(
          'Your latest answers could not be saved. Cannot reach the server.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Keep answering'),
          ),
          TextButton(
            style: TextButton.styleFrom(foregroundColor: SsColors.danger),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Leave'),
          ),
        ],
      ),
    );
    if (leave == true && mounted) _close();
  }

  void _onPop(bool didPop) {
    if (didPop) {
      _hideSnackBar();
    } else if (_block != null) {
      backToSurveys(context);
    } else if (!_sending) {
      _leave();
    }
  }

  @override
  Widget build(BuildContext context) {
    final block = _block;
    return PopScope(
      canPop:
          block == null &&
          !_sending &&
          _answers.isEmpty &&
          _saved.isEmpty &&
          _saveRun == null,
      onPopInvokedWithResult: (didPop, _) => _onPop(didPop),
      child: block != null
          ? Scaffold(
              appBar: AppBar(title: const Text('Survey')),
              body: SurveyBlockedBody(block: block),
            )
          : Scaffold(
              appBar: _buildAppBar(),
              body: _buildPages(),
              bottomNavigationBar: _onReview
                  ? _buildReviewBar()
                  : _buildQuestionBar(_questions[_index]),
            ),
    );
  }

  AppBar _buildAppBar() {
    final total = _questions.length;
    final position = _onReview ? total : _index + 1;
    return AppBar(
      leading: _onReview
          ? IconButton(
              tooltip: 'Back',
              icon: const Icon(Icons.arrow_back),
              onPressed: () => _goTo(total - 1),
            )
          : IconButton(
              tooltip: 'Leave survey',
              icon: _leaving
                  ? const SizedBox(
                      width: SsLayout.indicatorSize,
                      height: SsLayout.indicatorSize,
                      child: CircularProgressIndicator(
                        strokeWidth: SsLayout.indicatorStroke,
                        color: SsColors.surfaceRaised,
                      ),
                    )
                  : const Icon(Icons.close),
              onPressed: _leaving
                  ? null
                  : () => Navigator.of(context).maybePop(),
            ),
      title: _onReview
          ? const Text('Check your answers')
          : Text(
              widget.survey.title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: SsType.heading.copyWith(color: SsColors.surfaceRaised),
            ),
      actions: [
        Padding(
          padding: const EdgeInsetsDirectional.only(end: SsSpace.s4),
          child: ExcludeSemantics(
            child: SignalRing(
              value: (position * 100 / total).round(),
              size: SsLayout.ringCompact,
              centerLabel: '$position/$total',
              semanticLabel: 'Question $position of $total',
              ping: false,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPages() {
    final pageKey = ValueKey<int>(_index);
    final side =
        (_movingForward ? 1 : -1) *
        (Directionality.of(context) == TextDirection.rtl ? -1 : 1);
    return AnimatedSwitcher(
      duration: SsMotion.of(context, SsMotion.standard),
      switchInCurve: SsMotion.standardCurve,
      switchOutCurve: SsMotion.standardCurve,
      layoutBuilder: (current, previous) => Stack(
        alignment: AlignmentDirectional.topCenter,
        children: [...previous, ?current],
      ),
      transitionBuilder: (child, animation) => FadeTransition(
        opacity: animation,
        child: child.key == pageKey
            ? AnimatedBuilder(
                animation: animation,
                builder: (_, slid) => Transform.translate(
                  offset: Offset(side * SsSpace.s6 * (1 - animation.value), 0),
                  child: slid,
                ),
                child: child,
              )
            : child,
      ),
      child: KeyedSubtree(
        key: pageKey,
        child: _onReview
            ? _buildReview()
            : _buildQuestion(_questions[_index], _index),
      ),
    );
  }

  Widget _buildQuestion(SurveyQuestion question, int index) {
    final hint = switch (question.type) {
      QuestionType.choice => 'Choose one.',
      QuestionType.rating => '1 is the lowest, 5 the highest.',
      QuestionType.text => 'Write in Arabic or English.',
    };
    final missing = question.type == QuestionType.text
        ? 'Write an answer to continue.'
        : 'Choose an answer to continue.';

    return SingleChildScrollView(
      padding: const EdgeInsetsDirectional.all(SsSpace.s4),
      child: ProfileContentWidth(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Semantics(
                  liveRegion: true,
                  child: Text(
                    'Question ${index + 1} of ${_questions.length}',
                    style: SsType.label.copyWith(color: SsColors.inkMuted),
                  ),
                ),
                if (!question.isRequired) ...[
                  const SizedBox(width: SsSpace.s2),
                  const _OptionalTag(),
                ],
              ],
            ),
            const SizedBox(height: SsSpace.s2),
            Text(
              question.text,
              style: SsType.heading.copyWith(color: SsColors.ink),
            ),
            const SizedBox(height: SsSpace.s1),
            Text(
              hint,
              style: SsType.caption.copyWith(color: SsColors.inkMuted),
            ),
            const SizedBox(height: SsSpace.s4),
            _buildInput(question),
            if (_showRequired) ...[
              const SizedBox(height: SsSpace.s3),
              AnswerAlertLine(text: missing),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildInput(SurveyQuestion question) {
    final answer = _answers[question.id];
    switch (question.type) {
      case QuestionType.choice:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (final (i, option) in question.options.indexed) ...[
              if (i > 0) const SizedBox(height: SsSpace.s2),
              AnswerOption(
                label: option.text,
                selected: answer?.optionId == option.id,
                error: _showRequired,
                onTap: () => _setAnswer(question, Answer.option(option.id)),
              ),
            ],
          ],
        );
      case QuestionType.rating:
        return RatingScale(
          values: question.ratingValues,
          selected: answer?.rating,
          error: _showRequired,
          onChanged: (value) => _setAnswer(question, Answer.rating(value)),
        );
      case QuestionType.text:
        return OpenTextField(
          key: ValueKey<int>(question.id),
          initialText: answer?.text ?? '',
          error: _showRequired,
          onChanged: (text) => _setAnswer(
            question,
            text.trim().isEmpty ? null : Answer.text(text),
          ),
        );
    }
  }

  Widget _buildQuestionBar(SurveyQuestion question) {
    final isLast = _index == _questions.length - 1;
    final skip =
        !question.isRequired &&
        !_answers.containsKey(question.id) &&
        !isLast &&
        !_returnToReview;
    final label = _returnToReview
        ? 'Back to review'
        : (isLast ? 'Review answers' : 'Next');

    return AnswerBottomBar(
      children: [
        Row(
          children: [
            if (_index > 0) ...[
              Expanded(
                child: OutlinedButton(
                  onPressed: _goBack,
                  child: const Text('Back'),
                ),
              ),
              const SizedBox(width: SsSpace.s3),
            ],
            Expanded(
              flex: 2,
              child: skip
                  ? OutlinedButton.icon(
                      onPressed: _advance,
                      icon: const Icon(Icons.last_page),
                      label: const Text('Skip'),
                    )
                  : FilledButton(onPressed: _advance, child: Text(label)),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildReview() {
    final style = SsType.body.copyWith(color: SsColors.inkMuted);
    return SingleChildScrollView(
      child: ProfileContentWidth(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsetsDirectional.all(SsSpace.s4),
              child: Text(
                '${widget.survey.title}. Tap an answer to change it.',
                style: style,
              ),
            ),
            _rowDivider,
            AnimatedOpacity(
              duration: SsMotion.of(context, SsMotion.fast),
              opacity: _sending ? _sendingOpacity : 1,
              child: Material(
                color: SsColors.surfaceRaised,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (final (i, question) in _questions.indexed) ...[
                      _ReviewRow(
                        number: i + 1,
                        question: question,
                        answer: _reviewAnswer(question),
                        onTap: _sending ? null : () => _openFromReview(i),
                      ),
                      _rowDivider,
                    ],
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsetsDirectional.all(SsSpace.s4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.info_outline,
                    size: SsLayout.iconSmall,
                    color: SsColors.inkMuted,
                  ),
                  const SizedBox(width: SsSpace.s2),
                  Expanded(
                    child: Text(
                      _sending
                          ? 'Sending your answers. This can take a few seconds.'
                          : "You can't change your answers after you send them.",
                      style: SsType.caption.copyWith(color: SsColors.inkMuted),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _reviewAnswer(SurveyQuestion question) {
    final strong = SsType.body.copyWith(
      color: SsColors.ink,
      fontWeight: FontWeight.w600,
    );
    if (_needsAnswer.contains(question.id)) {
      return Row(
        children: [
          const Icon(
            Icons.error_outline,
            size: SsLayout.iconSmall,
            color: SsColors.danger,
          ),
          const SizedBox(width: SsSpace.s1),
          Expanded(
            child: Text(
              'Needs an answer',
              style: strong.copyWith(color: SsColors.danger),
            ),
          ),
        ],
      );
    }
    final answer = _answers[question.id];
    if (answer == null) {
      return Text(
        'Skipped',
        style: SsType.body.copyWith(color: SsColors.inkMuted),
      );
    }
    final text = answer.text?.trim();
    if (text != null) {
      return Text(
        text,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        textDirection: directionOf(text),
        style: strong,
      );
    }
    final rating = answer.rating;
    return Text(
      rating != null
          ? '$rating out of ${question.ratingValues.last}'
          : question.options.firstWhere((o) => o.id == answer.optionId).text,
      style: strong,
    );
  }

  Widget _buildReviewBar() {
    final line = _needsAnswer.isNotEmpty
        ? 'Fix the marked answer, then send.'
        : _sendMessage;
    return AnswerBottomBar(
      children: [
        if (line != null) ...[
          AnswerAlertLine(text: line),
          const SizedBox(height: SsSpace.s3),
        ],
        FilledButton.icon(
          onPressed: _send,
          icon: _sending
              ? const SizedBox(
                  width: SsLayout.indicatorSize,
                  height: SsLayout.indicatorSize,
                  child: CircularProgressIndicator(
                    strokeWidth: SsLayout.indicatorStroke,
                    color: SsColors.surfaceRaised,
                  ),
                )
              : const Icon(Icons.send_outlined),
          label: Text(_sending ? 'Sending…' : 'Send answers'),
        ),
      ],
    );
  }
}

class _OptionalTag extends StatelessWidget {
  const _OptionalTag();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: SsColors.surfaceRaised,
        borderRadius: BorderRadius.circular(SsRadius.pill),
        border: Border.all(color: SsColors.line),
      ),
      child: Padding(
        padding: const EdgeInsetsDirectional.symmetric(
          horizontal: SsSpace.s2,
          vertical: SsSpace.s1,
        ),
        child: Text(
          'Optional',
          style: SsType.caption.copyWith(color: SsColors.inkMuted),
        ),
      ),
    );
  }
}

class _ReviewRow extends StatelessWidget {
  const _ReviewRow({
    required this.number,
    required this.question,
    required this.answer,
    required this.onTap,
  });

  final int number;
  final SurveyQuestion question;
  final Widget answer;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final caption = question.isRequired
        ? question.text
        : '${question.text} Optional';
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsetsDirectional.symmetric(
          horizontal: SsSpace.s4,
          vertical: SsSpace.s3,
        ),
        child: Row(
          children: [
            Container(
              width: SsLayout.reviewNumber,
              height: SsLayout.reviewNumber,
              alignment: Alignment.center,
              decoration: const BoxDecoration(
                color: SsColors.brandTint,
                shape: BoxShape.circle,
              ),
              child: Text(
                '$number',
                style: SsType.label.copyWith(color: SsColors.brand),
              ),
            ),
            const SizedBox(width: SsSpace.s3),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    caption,
                    style: SsType.caption.copyWith(color: SsColors.inkMuted),
                  ),
                  const SizedBox(height: SsSpace.s1),
                  answer,
                ],
              ),
            ),
            const SizedBox(width: SsSpace.s2),
            const Icon(Icons.chevron_right, color: SsColors.inkMuted),
          ],
        ),
      ),
    );
  }
}
