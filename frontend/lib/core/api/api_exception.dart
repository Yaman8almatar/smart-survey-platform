/// An error answered by the API, or a failure to get a usable answer.
///
/// Built from `{"error": {"code", "message", "fields"?}}`. The UI only ever sees
/// [code], [message] and [fields], never raw exception text.
class ApiException implements Exception {
  const ApiException({
    required this.statusCode,
    required this.code,
    required this.message,
    this.fields = const {},
  });

  /// The server could not be reached (not running, offline, timed out).
  const ApiException.network()
    : statusCode = 0,
      code = networkError,
      message = 'Cannot reach the server.',
      fields = const {};

  /// The body was not the JSON the API contract promises (e.g. Django's HTML 404).
  const ApiException.unexpectedResponse(this.statusCode)
    : code = unexpectedResponseCode,
      message = 'The server sent an unexpected response.',
      fields = const {};

  static const String networkError = 'network_error';
  static const String unexpectedResponseCode = 'unexpected_response';
  static const String invalidCredentials = 'invalid_credentials';
  static const String permissionDenied = 'permission_denied';

  final int statusCode;
  final String code;
  final String message;

  /// Field name -> messages, present only for input validation errors.
  final Map<String, List<String>> fields;

  /// Parses a decoded error body; anything else is an unexpected response.
  factory ApiException.fromJson(int statusCode, Object? json) {
    if (json is Map<String, dynamic> && json['error'] is Map<String, dynamic>) {
      final error = json['error'] as Map<String, dynamic>;
      final code = error['code'];
      final message = error['message'];
      if (code is String && message is String) {
        return ApiException(
          statusCode: statusCode,
          code: code,
          message: message,
          fields: _parseFields(error['fields']),
        );
      }
    }
    return ApiException.unexpectedResponse(statusCode);
  }

  static Map<String, List<String>> _parseFields(Object? raw) {
    if (raw is! Map<String, dynamic>) {
      return const {};
    }
    return {
      for (final entry in raw.entries)
        entry.key: entry.value is List
            ? [for (final item in entry.value as List) item.toString()]
            : [entry.value.toString()],
    };
  }

  @override
  String toString() => 'ApiException($statusCode, $code)';
}

/// The refresh token no longer works; the respondent must log in again.
class SessionExpiredException implements Exception {
  const SessionExpiredException();

  @override
  String toString() => 'SessionExpiredException';
}
