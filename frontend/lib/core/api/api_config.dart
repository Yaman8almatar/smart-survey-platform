import 'package:flutter/foundation.dart';

/// Where the app finds the REST API. Override with `--dart-define=API_BASE_URL=...`.
abstract final class ApiConfig {
  static const String _definedBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const String _webDefault = 'http://127.0.0.1:8000/api/v1/';
  static const String _emulatorDefault = 'http://10.0.2.2:8000/api/v1/';

  /// Always ends with `/` so relative paths such as `me/` resolve under it.
  static Uri get baseUrl {
    var raw = _definedBaseUrl.isNotEmpty
        ? _definedBaseUrl
        : (kIsWeb ? _webDefault : _emulatorDefault);
    if (!raw.endsWith('/')) {
      raw = '$raw/';
    }
    return Uri.parse(raw);
  }
}
