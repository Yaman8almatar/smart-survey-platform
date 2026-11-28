/// One row of `GET /surveys/eligible/`.
class EligibleSurvey {
  const EligibleSurvey({
    required this.id,
    required this.title,
    required this.description,
    required this.questionCount,
    required this.expectedMinutes,
    this.publishedOn,
    this.closesOn,
  });

  factory EligibleSurvey.fromJson(Map<String, dynamic> json) {
    final publishedOn = json['published_on'] as String?;
    final closesOn = json['closes_on'] as String?;
    return EligibleSurvey(
      id: json['id'] as int,
      title: json['title'] as String,
      description: (json['description'] as String?) ?? '',
      questionCount: json['question_count'] as int,
      expectedMinutes: json['expected_minutes'] as int,
      publishedOn: publishedOn == null ? null : DateTime.parse(publishedOn),
      closesOn: closesOn == null ? null : DateTime.parse(closesOn),
    );
  }

  final int id;
  final String title;
  final String description;
  final int questionCount;

  /// About how many minutes the survey takes (FR-08).
  final int expectedMinutes;

  /// The publish date, without a time; null when the server has none.
  final DateTime? publishedOn;

  /// The last day the survey takes responses (FR-11); null when it has none.
  final DateTime? closesOn;
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
