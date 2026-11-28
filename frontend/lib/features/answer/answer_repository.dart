import '../../core/api/api_client.dart';
import '../../core/api/api_exception.dart';
import '../../core/device_id_store.dart';
import 'answer_models.dart';

/// The only class that calls the survey detail and response endpoints.
class AnswerRepository {
  AnswerRepository({required ApiClient api, required DeviceIdStore deviceIds})
    : _api = api,
      _deviceIds = deviceIds;

  final ApiClient _api;
  final DeviceIdStore _deviceIds;

  Future<SurveyDetail> survey(int id) async {
    final json = await _api.get('surveys/$id/');
    return _parse(200, json, SurveyDetail.fromJson);
  }

  /// Sends [answers], keyed by question id. A blank text counts as no answer.
  ///
  /// FR-04: adds [timings] (active ms by question id) when given, and the
  /// install ID when the store gives one; evidence never stops the send.
  Future<SubmitResult> submit(
    int id,
    Map<int, Answer> answers, {
    Map<int, int>? timings,
  }) async {
    final json = await _api.post(
      'surveys/$id/responses/',
      body: {
        ..._answersBody(answers),
        'timings': ?_timingsBody(timings),
        'device_id': ?await _deviceId(),
      },
    );
    return _parse(201, json, SubmitResult.fromJson);
  }

  Future<String?> _deviceId() async {
    try {
      return await _deviceIds.readOrCreate();
    } catch (_) {
      return null;
    }
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
  ///
  /// Sent [timings] replace the stored ones; without them the server keeps them.
  Future<void> saveDraft(
    int id,
    Map<int, Answer> answers, {
    Map<int, int>? timings,
  }) async {
    await _api.put(
      'surveys/$id/draft/',
      body: {..._answersBody(answers), 'timings': ?_timingsBody(timings)},
    );
  }

  Future<void> deleteDraft(int id) async {
    await _api.delete('surveys/$id/draft/');
  }

  static Map<String, Object> _answersBody(Map<int, Answer> answers) => {
    'answers': [
      for (final entry in answers.entries) ?_answerBody(entry.key, entry.value),
    ],
  };

  static List<Map<String, int>>? _timingsBody(Map<int, int>? timings) =>
      timings == null
      ? null
      : [
          for (final entry in timings.entries)
            {'question_id': entry.key, 'active_ms': entry.value},
        ];

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
