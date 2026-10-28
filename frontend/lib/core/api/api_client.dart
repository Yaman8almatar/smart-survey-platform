import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_exception.dart';
import 'token_store.dart';

/// The single entry point to the REST API: Bearer header, refresh-on-401, error mapping.
class ApiClient {
  ApiClient({
    required http.Client httpClient,
    required TokenStore tokenStore,
    required Uri baseUrl,
  }) : _http = httpClient,
       _tokens = tokenStore,
       _baseUrl = baseUrl;

  static const Duration _timeout = Duration(seconds: 15);

  final http.Client _http;
  final TokenStore _tokens;
  final Uri _baseUrl;

  /// Concurrent 401s wait for this one refresh instead of starting their own.
  Future<void>? _refreshing;

  Future<Object?> get(String path, {bool authenticated = true}) =>
      _send('GET', path, authenticated: authenticated);

  Future<Object?> post(
    String path, {
    Object? body,
    bool authenticated = true,
  }) => _send('POST', path, body: body, authenticated: authenticated);

  Future<Object?> put(String path, {Object? body, bool authenticated = true}) =>
      _send('PUT', path, body: body, authenticated: authenticated);

  Future<Object?> _send(
    String method,
    String path, {
    Object? body,
    required bool authenticated,
  }) async {
    final usedToken = authenticated ? await _tokens.readAccess() : null;
    var response = await _request(method, path, body, usedToken);

    if (response.statusCode == 401 && authenticated) {
      await _refreshAfterRejection(usedToken);
      final fresh = await _tokens.readAccess();
      response = await _request(method, path, body, fresh);
    }
    return _decode(response);
  }

  /// Refreshes unless another call already replaced the token that was rejected.
  Future<void> _refreshAfterRejection(String? rejectedToken) async {
    if (_refreshing == null && await _tokens.readAccess() != rejectedToken) {
      return;
    }
    await (_refreshing ??= _refresh().whenComplete(() => _refreshing = null));
  }

  Future<void> _refresh() async {
    final refreshToken = await _tokens.readRefresh();
    if (refreshToken == null) {
      await _tokens.clear();
      throw const SessionExpiredException();
    }

    final response = await _request('POST', 'auth/token/refresh/', {
      'refresh': refreshToken,
    }, null);

    if (response.statusCode == 401 || response.statusCode == 400) {
      await _tokens.clear();
      throw const SessionExpiredException();
    }
    final json = _decode(response);
    if (json is! Map<String, dynamic> || json['access'] is! String) {
      throw ApiException.unexpectedResponse(response.statusCode);
    }
    await _tokens.saveAccess(json['access'] as String);
    if (json['refresh'] is String) {
      await _tokens.saveRefresh(json['refresh'] as String);
    }
  }

  Future<http.Response> _request(
    String method,
    String path,
    Object? body,
    String? accessToken,
  ) async {
    final request = http.Request(method, _baseUrl.resolve(path))
      ..headers['Accept'] = 'application/json';
    if (accessToken != null) {
      request.headers['Authorization'] = 'Bearer $accessToken';
    }
    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }
    try {
      final streamed = await _http.send(request).timeout(_timeout);
      return await http.Response.fromStream(streamed);
    } on Exception {
      throw const ApiException.network();
    }
  }

  Object? _decode(http.Response response) {
    final ok = response.statusCode >= 200 && response.statusCode < 300;
    if (ok && response.bodyBytes.isEmpty) {
      return null;
    }
    final Object? json;
    try {
      json = jsonDecode(utf8.decode(response.bodyBytes));
    } on FormatException {
      throw ApiException.unexpectedResponse(response.statusCode);
    }
    if (!ok) {
      throw ApiException.fromJson(response.statusCode, json);
    }
    return json;
  }
}
