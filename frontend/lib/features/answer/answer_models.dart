enum QuestionType { choice, rating, text }

/// One choice of a multiple-choice question.
class QuestionOption {
  const QuestionOption({required this.id, required this.text});

  factory QuestionOption.fromJson(Map<String, dynamic> json) {
    return QuestionOption(id: json['id'] as int, text: json['text'] as String);
  }

  final int id;
  final String text;
}

/// One question of `GET /surveys/{id}/`.
class SurveyQuestion {
  const SurveyQuestion({
    required this.id,
    required this.text,
    required this.type,
    required this.isRequired,
    this.options = const [],
    this.ratingValues = const [],
  });

  factory SurveyQuestion.fromJson(Map<String, dynamic> json) {
    return SurveyQuestion(
      id: json['id'] as int,
      text: json['text'] as String,
      type: switch (json['type']) {
        'MULTIPLE_CHOICE' => QuestionType.choice,
        'RATING_SCALE' => QuestionType.rating,
        'OPEN_TEXT' => QuestionType.text,
        final other => throw FormatException('Unknown question type $other'),
      },
      isRequired: json['is_required'] as bool,
      options: [
        for (final item in (json['options'] as List?) ?? const [])
          QuestionOption.fromJson(item as Map<String, dynamic>),
      ],
      ratingValues: [
        for (final value in (json['rating_values'] as List?) ?? const [])
          value as int,
      ],
    );
  }

  final int id;
  final String text;
  final QuestionType type;
  final bool isRequired;
  final List<QuestionOption> options;
  final List<int> ratingValues;
}

/// A survey ready to answer, its questions in `order_index` order.
class SurveyDetail {
  const SurveyDetail({
    required this.id,
    required this.title,
    required this.description,
    required this.questions,
  });

  factory SurveyDetail.fromJson(Map<String, dynamic> json) {
    final rows = [
      for (final item in json['questions'] as List)
        item as Map<String, dynamic>,
    ]..sort((a, b) => (a['order_index'] as int) - (b['order_index'] as int));
    return SurveyDetail(
      id: json['id'] as int,
      title: json['title'] as String,
      description: (json['description'] as String?) ?? '',
      questions: [for (final row in rows) SurveyQuestion.fromJson(row)],
    );
  }

  final int id;
  final String title;
  final String description;
  final List<SurveyQuestion> questions;

  int get optionalCount => questions.where((q) => !q.isRequired).length;
}

/// The respondent's answer to one question: exactly one field is set.
class Answer {
  const Answer.option(int this.optionId) : rating = null, text = null;

  const Answer.rating(int this.rating) : optionId = null, text = null;

  const Answer.text(String this.text) : optionId = null, rating = null;

  final int? optionId;
  final int? rating;
  final String? text;

  @override
  bool operator ==(Object other) =>
      other is Answer &&
      other.optionId == optionId &&
      other.rating == rating &&
      other.text == text;

  @override
  int get hashCode => Object.hash(optionId, rating, text);
}

/// The 200 body of `GET /surveys/{id}/draft/`: answers saved but not sent.
class SurveyDraft {
  const SurveyDraft({
    required this.answers,
    required this.startedAt,
    required this.updatedAt,
  });

  factory SurveyDraft.fromJson(Map<String, dynamic> json) {
    return SurveyDraft(
      answers: {
        for (final item in json['answers'] as List)
          item['question_id'] as int: ?_answerFrom(
            item as Map<String, dynamic>,
          ),
      },
      startedAt: DateTime.parse(json['started_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  static Answer? _answerFrom(Map<String, dynamic> row) {
    final optionId = row['selected_option_id'] as int?;
    if (optionId != null) return Answer.option(optionId);
    final rating = row['rating_value'] as int?;
    if (rating != null) return Answer.rating(rating);
    final text = row['answer_value'] as String?;
    return text == null ? null : Answer.text(text);
  }

  /// Keyed by question id.
  final Map<int, Answer> answers;
  final DateTime startedAt;
  final DateTime updatedAt;

  /// This draft without answers [survey] no longer accepts; null when none is left.
  SurveyDraft? keptFor(SurveyDetail survey) {
    final kept = <int, Answer>{};
    for (final question in survey.questions) {
      final answer = answers[question.id];
      if (answer == null) continue;
      final optionId = answer.optionId;
      if (optionId != null && !question.options.any((o) => o.id == optionId)) {
        continue;
      }
      kept[question.id] = answer;
    }
    if (kept.isEmpty) return null;
    return SurveyDraft(
      answers: kept,
      startedAt: startedAt,
      updatedAt: updatedAt,
    );
  }
}

/// The 201 body of `POST /surveys/{id}/responses/`.
class SubmitResult {
  const SubmitResult({required this.responseId, required this.submittedAt});

  factory SubmitResult.fromJson(Map<String, dynamic> json) {
    return SubmitResult(
      responseId: json['id'] as int,
      submittedAt: DateTime.parse(json['submitted_at'] as String),
    );
  }

  final int responseId;
  final DateTime submittedAt;
}
