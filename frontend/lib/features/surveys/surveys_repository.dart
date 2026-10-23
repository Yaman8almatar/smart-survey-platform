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
}
