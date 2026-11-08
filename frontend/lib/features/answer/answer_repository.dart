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
      body: {
        'answers': [
          for (final entry in answers.entries)
            ?_answerBody(entry.key, entry.value),
        ],
      },
      timeout: submitTimeout,
    );
    return _parse(201, json, SubmitResult.fromJson);
  }

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
