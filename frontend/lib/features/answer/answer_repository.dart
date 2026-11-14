import '../../core/api/api_client.dart';
import '../../core/api/api_exception.dart';
import 'answer_models.dart';

/// The only class that calls the survey detail and response endpoints.
class AnswerRepository {
  AnswerRepository({required ApiClient api}) : _api = api;

  /// The server may analyse open text inside the submit request (K-02).
  static const Duration submitTimeout = Duration(seconds: 60);

  final ApiClient _api;

  Future<SurveyDetail> survey(int id) async {
    final json = await _api.get('surveys/$id/');
    return _parse(200, json, SurveyDetail.fromJson);
  }

  /// Sends [answers], keyed by question id. A blank text counts as no answer.
  Future<SubmitResult> submit(int id, Map<int, Answer> answers) async {
    final json = await _api.post(
      'surveys/$id/responses/',
      body: _answersBody(answers),
      timeout: submitTimeout,
    );
    return _parse(201, json, SubmitResult.fromJson);
  }

  /// The saved draft of survey [id], or null when the respondent has none.
  Future<SurveyDraft?> draft(int id) async {
    final Object? json;
    try {
      json = await _api.get('surveys/$id/draft/');
    } on ApiException catch (error) {
      if (error.code == 'draft_not_found') return null;
      rethrow;
    }
    return _parse(200, json, SurveyDraft.fromJson);
  }

  /// Replaces the saved draft with [answers]. A blank text counts as no answer.
  Future<void> saveDraft(int id, Map<int, Answer> answers) async {
    await _api.put('surveys/$id/draft/', body: _answersBody(answers));
  }

  Future<void> deleteDraft(int id) async {
    await _api.delete('surveys/$id/draft/');
  }

  static Map<String, Object> _answersBody(Map<int, Answer> answers) => {
    'answers': [
      for (final entry in answers.entries) ?_answerBody(entry.key, entry.value),
    ],
  };

  static Map<String, Object>? _answerBody(int questionId, Answer answer) {
    final text = answer.text?.trim();
    if (text != null && text.isEmpty) return null;
    return {
      'question_id': questionId,
      'selected_option_id': ?answer.optionId,
      'rating_value': ?answer.rating,
      'answer_value': ?text,
    };
  }

  static T _parse<T>(
    int status,
    Object? json,
    T Function(Map<String, dynamic>) fromJson,
  ) {
    if (json is! Map<String, dynamic>) {
      throw ApiException.unexpectedResponse(status);
    }
    try {
      return fromJson(json);
    } on TypeError {
      throw ApiException.unexpectedResponse(status);
    } on FormatException {
      throw ApiException.unexpectedResponse(status);
    }
  }
}
