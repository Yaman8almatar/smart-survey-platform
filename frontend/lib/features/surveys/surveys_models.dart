/// One row of `GET /surveys/eligible/`.
class EligibleSurvey {
  const EligibleSurvey({
    required this.id,
    required this.title,
    required this.description,
    required this.questionCount,
  });

  factory EligibleSurvey.fromJson(Map<String, dynamic> json) {
    return EligibleSurvey(
      id: json['id'] as int,
      title: json['title'] as String,
      description: (json['description'] as String?) ?? '',
      questionCount: json['question_count'] as int,
    );
  }

  final int id;
  final String title;
  final String description;
  final int questionCount;
}

/// One row of `SurveysRepository.answeredSurveys`: a survey the respondent
/// has sent.
class AnsweredSurvey {
  const AnsweredSurvey({
    required this.surveyId,
    required this.title,
    required this.description,
    required this.submittedAt,
  });

  factory AnsweredSurvey.fromJson(Map<String, dynamic> json) {
    return AnsweredSurvey(
      surveyId: json['survey_id'] as int,
      title: json['title'] as String,
      description: (json['description'] as String?) ?? '',
      submittedAt: DateTime.parse(json['submitted_at'] as String),
    );
  }

  final int surveyId;
  final String title;
  final String description;
  final DateTime submittedAt;
}
