import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// FR-04: the app's anonymous install ID, sent with each response.
///
/// It is random, not a hardware identifier, and logout does not delete it:
/// the signal is "two accounts, one installation" (DESIGN-INC2 2.4).
abstract class DeviceIdStore {
  /// The stored ID; the first call creates and stores one.
  Future<String> readOrCreate();
}

/// 128 random bits from [Random.secure], as 32 lowercase hex characters.
String newDeviceId([Random? random]) {
  final source = random ?? Random.secure();
  return [
    for (var i = 0; i < 16; i++)
      source.nextInt(256).toRadixString(16).padLeft(2, '0'),
  ].join();
}

/// The format the server accepts for `device_id`.
final RegExp _serverFormat = RegExp(r'^[A-Za-z0-9_-]{16,64}$');

/// Keeps the ID in the platform keystore (encrypted browser storage on web).
class SecureDeviceIdStore implements DeviceIdStore {
  SecureDeviceIdStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  static const String _key = 'device_id';

  final FlutterSecureStorage _storage;

  @override
  Future<String> readOrCreate() async {
    final stored = await _storage.read(key: _key);
    if (stored != null && _serverFormat.hasMatch(stored)) return stored;
    final created = newDeviceId();
    await _storage.write(key: _key, value: created);
    return created;
  }
}

/// In-memory store for tests.
class MemoryDeviceIdStore implements DeviceIdStore {
  MemoryDeviceIdStore({this.id});

  String? id;

  @override
  Future<String> readOrCreate() async => id ??= newDeviceId();
}
