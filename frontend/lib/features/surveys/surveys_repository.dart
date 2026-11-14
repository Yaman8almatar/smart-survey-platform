import '../../core/api/api_client.dart';
import '../../core/api/api_exception.dart';
import 'surveys_models.dart';

/// The only class that calls the survey endpoints.
class SurveysRepository {
  SurveysRepository({required ApiClient api}) : _api = api;

  final ApiClient _api;

  Future<List<EligibleSurvey>> eligibleSurveys() async {
    final json = await _api.get('surveys/eligible/');
    if (json is! List) {
      throw const ApiException.unexpectedResponse(200);
    }
    try {
      return [
        for (final item in json)
          EligibleSurvey.fromJson(item as Map<String, dynamic>),
      ];
    } on TypeError {
      throw const ApiException.unexpectedResponse(200);
    }
  }

  /// Surveys the respondent has sent, in the server's order (newest first).
  Future<List<AnsweredSurvey>> answeredSurveys() async {
    final json = await _api.get('me/responses/');
    if (json is! List) {
      throw const ApiException.unexpectedResponse(200);
    }
    try {
      return [
        for (final item in json)
          AnsweredSurvey.fromJson(item as Map<String, dynamic>),
      ];
    } on TypeError {
      throw const ApiException.unexpectedResponse(200);
    } on FormatException {
      throw const ApiException.unexpectedResponse(200);
    }
  }
}
