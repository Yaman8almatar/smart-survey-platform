import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_survey_app/core/api/token_store.dart';
import 'package:smart_survey_app/core/device_id_store.dart';

final RegExp _hex32 = RegExp(r'^[0-9a-f]{32}$');
final RegExp _serverFormat = RegExp(r'^[A-Za-z0-9_-]{16,64}$');

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  test('the ID is 32 lowercase hex characters the server accepts', () async {
    final id = await SecureDeviceIdStore().readOrCreate();

    expect(id, matches(_hex32));
    expect(id, matches(_serverFormat));
  });

  test('a second read gives the same value', () async {
    final first = await SecureDeviceIdStore().readOrCreate();

    expect(await SecureDeviceIdStore().readOrCreate(), first);
  });

  test('two fresh storages give different values', () async {
    final first = await SecureDeviceIdStore().readOrCreate();
    FlutterSecureStorage.setMockInitialValues({});

    expect(await SecureDeviceIdStore().readOrCreate(), isNot(first));
  });

  test('the ID survives logout', () async {
    final tokens = SecureTokenStore();
    await tokens.saveAccess('a');
    await tokens.saveRefresh('r');
    final id = await SecureDeviceIdStore().readOrCreate();

    await tokens.clear();

    expect(await tokens.readAccess(), isNull);
    expect(await SecureDeviceIdStore().readOrCreate(), id);
  });

  test('a stored value the server would refuse is replaced', () async {
    FlutterSecureStorage.setMockInitialValues({'device_id': 'short'});

    expect(await SecureDeviceIdStore().readOrCreate(), matches(_hex32));
  });

  test('the memory store creates once and keeps the value', () async {
    final store = MemoryDeviceIdStore();
    final id = await store.readOrCreate();

    expect(id, matches(_hex32));
    expect(await store.readOrCreate(), id);
  });
}
