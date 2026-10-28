import '../../core/api/api_client.dart';
import '../../core/api/api_exception.dart';
import '../../core/api/token_store.dart';
import 'auth_models.dart';

/// The account is a provider or admin; this app is for respondents only.
class NotRespondentException implements Exception {
  const NotRespondentException();

  @override
  String toString() => 'NotRespondentException';
}

/// The only class that calls the auth endpoints.
class AuthRepository {
  AuthRepository({required ApiClient api, required TokenStore tokens})
    : _api = api,
      _tokens = tokens;

  final ApiClient _api;
  final TokenStore _tokens;

  Future<void> login(String email, String password) async {
    final json = await _api.post(
      'auth/token/',
      body: {'email': email, 'password': password},
      authenticated: false,
    );
    if (json is! Map<String, dynamic> ||
        json['access'] is! String ||
        json['refresh'] is! String) {
      throw const ApiException.unexpectedResponse(200);
    }
    await _tokens.saveAccess(json['access'] as String);
    await _tokens.saveRefresh(json['refresh'] as String);
  }

  /// Creates the respondent and profile. The API returns no tokens; call [login] next.
  Future<void> register({
    required String name,
    required String email,
    required String password,
    required int age,
    required String gender,
    required String region,
    required String interests,
  }) async {
    await _api.post(
      'auth/register/',
      body: {
        'name': name,
        'email': email,
        'password': password,
        'age': age,
        'gender': gender,
        'region': region,
        'interests': interests,
      },
      authenticated: false,
    );
  }

  /// Throws [NotRespondentException] (and clears the tokens) on a 403.
  Future<AppUser> currentUser() async {
    try {
      final json = await _api.get('me/');
      if (json is! Map<String, dynamic>) {
        throw const ApiException.unexpectedResponse(200);
      }
      return AppUser.fromJson(json);
    } on ApiException catch (error) {
      if (error.statusCode == 403) {
        await _tokens.clear();
        throw const NotRespondentException();
      }
      rethrow;
    } on TypeError {
      throw const ApiException.unexpectedResponse(200);
    }
  }

  Future<void> logout() => _tokens.clear();

  Future<bool> hasSession() async => await _tokens.readRefresh() != null;
}
