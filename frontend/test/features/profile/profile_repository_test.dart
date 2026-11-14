import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:smart_survey_app/core/api/token_store.dart';
import 'package:smart_survey_app/features/profile/profile_models.dart';

import '../../support/test_api.dart';

void main() {
  test('options parses every list and sends no token', () async {
    http.Request? sent;
    final test = TestApi((request) async {
      sent = request;
      return jsonResponse(profileOptionsJson);
    }, tokens: MemoryTokenStore(access: 'a', refresh: 'r'));

    final options = await test.profile.options();

    expect(sent!.url.path, endsWith('profile/options/'));
    expect(sent!.headers.containsKey('Authorization'), isFalse);
    expect(options.governorates.map((o) => o.code), [
      'ALEPPO',
      'DAMASCUS',
      'HOMS',
      'OUTSIDE_SYRIA',
    ]);
    expect(options.governorates[1].label, 'Damascus');
    expect(options.education.last.code, 'PREFER_NOT_TO_SAY');
    expect(options.occupation, hasLength(3));
    expect(options.maritalStatus, hasLength(3));
    expect(options.interests.first.label, 'Technology');
  });

  test('load parses the profile', () async {
    final test = TestApi((request) async => jsonResponse(profileJson));

    final profile = await test.profile.load();

    expect(profile!.age, 24);
    expect(profile.gender, 'FEMALE');
    expect(profile.region, 'DAMASCUS');
    expect(profile.interests, ['TECHNOLOGY', 'EDUCATION', 'HEALTH']);
    expect(profile.education, '');
    expect(profile.occupation, '');
    expect(profile.maritalStatus, '');
    expect(profile.completionPercent, 57);
  });

  test('load returns null when there is no profile (404)', () async {
    final test = TestApi(
      (request) async => errorResponse(404, 'not_found', 'Not found.'),
    );

    expect(await test.profile.load(), isNull);
  });

  test('save sends a PUT with all seven fields', () async {
    http.Request? sent;
    final test = TestApi((request) async {
      sent = request;
      return jsonResponse({
        ...profileJson,
        'marital_status': 'SINGLE',
        'completion_percent': 71,
      });
    });

    final saved = await test.profile.save(
      const Profile(
        age: 24,
        gender: 'FEMALE',
        region: 'DAMASCUS',
        interests: ['TECHNOLOGY'],
        education: '',
        occupation: '',
        maritalStatus: 'SINGLE',
      ),
    );

    expect(sent!.method, 'PUT');
    expect(sent!.url.path, endsWith('me/profile/'));
    expect(jsonDecode(sent!.body), {
      'age': 24,
      'gender': 'FEMALE',
      'region': 'DAMASCUS',
      'interests': ['TECHNOLOGY'],
      'education': '',
      'occupation': '',
      'marital_status': 'SINGLE',
    });
    expect(saved.completionPercent, 71);
  });
}
