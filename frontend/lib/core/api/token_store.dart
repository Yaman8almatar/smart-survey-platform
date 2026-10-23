import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Where the JWT access and refresh tokens live between app launches.
abstract class TokenStore {
  Future<String?> readAccess();
  Future<String?> readRefresh();
  Future<void> saveAccess(String token);
  Future<void> saveRefresh(String token);
  Future<void> clear();
}

/// Keeps tokens in the platform keystore (encrypted browser storage on web).
class SecureTokenStore implements TokenStore {
  SecureTokenStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  static const String _accessKey = 'access_token';
  static const String _refreshKey = 'refresh_token';

  final FlutterSecureStorage _storage;

  @override
  Future<String?> readAccess() => _storage.read(key: _accessKey);

  @override
  Future<String?> readRefresh() => _storage.read(key: _refreshKey);

  @override
  Future<void> saveAccess(String token) =>
      _storage.write(key: _accessKey, value: token);

  @override
  Future<void> saveRefresh(String token) =>
      _storage.write(key: _refreshKey, value: token);

  @override
  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }
}

/// In-memory store for tests.
class MemoryTokenStore implements TokenStore {
  MemoryTokenStore({this.access, this.refresh});

  String? access;
  String? refresh;

  @override
  Future<String?> readAccess() async => access;

  @override
  Future<String?> readRefresh() async => refresh;

  @override
  Future<void> saveAccess(String token) async => access = token;

  @override
  Future<void> saveRefresh(String token) async => refresh = token;

  @override
  Future<void> clear() async {
    access = null;
    refresh = null;
  }
}
