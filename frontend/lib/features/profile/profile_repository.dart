import '../../core/api/api_client.dart';
import '../../core/api/api_exception.dart';
import 'profile_models.dart';

/// The only class that calls the profile endpoints.
class ProfileRepository {
  ProfileRepository({required ApiClient api}) : _api = api;

  final ApiClient _api;

  /// The fixed lists; needs no token, so register can use it too.
  Future<ProfileOptions> options() async {
    final json = await _api.get('profile/options/', authenticated: false);
    return _parse(json, ProfileOptions.fromJson);
  }

  /// The stored profile, or null when the respondent has none yet (404).
  Future<Profile?> load() async {
    final Object? json;
    try {
      json = await _api.get('me/profile/');
    } on ApiException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
    return _parse<Profile>(json, Profile.fromJson);
  }

  /// Replaces the whole profile and returns it with the new completion percent.
  Future<Profile> save(Profile profile) async {
    final json = await _api.put('me/profile/', body: profile.toJson());
    return _parse(json, Profile.fromJson);
  }

  T _parse<T>(Object? json, T Function(Map<String, dynamic>) fromJson) {
    if (json is! Map<String, dynamic>) {
      throw const ApiException.unexpectedResponse(200);
    }
    try {
      return fromJson(json);
    } on TypeError {
      throw const ApiException.unexpectedResponse(200);
    }
  }
}
