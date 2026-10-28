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
