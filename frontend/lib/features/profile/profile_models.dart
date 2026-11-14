/// One entry of a fixed list from `GET /profile/options/`: the app shows [label] and sends [code].
class ChoiceOption {
  const ChoiceOption({required this.code, required this.label});

  factory ChoiceOption.fromJson(Map<String, dynamic> json) => ChoiceOption(
    code: json['code'] as String,
    label: json['label'] as String,
  );

  final String code;
  final String label;
}

/// The fixed lists the profile and register forms choose from, in display order.
class ProfileOptions {
  const ProfileOptions({
    required this.governorates,
    required this.education,
    required this.occupation,
    required this.maritalStatus,
    required this.interests,
  });

  factory ProfileOptions.fromJson(Map<String, dynamic> json) => ProfileOptions(
    governorates: _list(json['governorates']),
    education: _list(json['education']),
    occupation: _list(json['occupation']),
    maritalStatus: _list(json['marital_status']),
    interests: _list(json['interests']),
  );

  static List<ChoiceOption> _list(Object? raw) => [
    for (final item in raw as List)
      ChoiceOption.fromJson(item as Map<String, dynamic>),
  ];

  final List<ChoiceOption> governorates;
  final List<ChoiceOption> education;
  final List<ChoiceOption> occupation;
  final List<ChoiceOption> maritalStatus;
  final List<ChoiceOption> interests;
}

/// The respondent profile: seven details and the server's completion percent.
///
/// Optional details are `""` when not answered.
class Profile {
  const Profile({
    required this.age,
    required this.gender,
    required this.region,
    required this.interests,
    required this.education,
    required this.occupation,
    required this.maritalStatus,
    this.completionPercent = 0,
  });

  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
    age: json['age'] as int,
    gender: json['gender'] as String,
    region: json['region'] as String,
    interests: [for (final code in json['interests'] as List) code as String],
    education: json['education'] as String,
    occupation: json['occupation'] as String,
    maritalStatus: json['marital_status'] as String,
    completionPercent: json['completion_percent'] as int,
  );

  final int age;
  final String gender;
  final String region;
  final List<String> interests;
  final String education;
  final String occupation;
  final String maritalStatus;

  /// Read-only, computed by the server.
  final int completionPercent;

  /// The body of `PUT /me/profile/`: all seven fields (a full replace).
  Map<String, Object> toJson() => {
    'age': age,
    'gender': gender,
    'region': region,
    'interests': interests,
    'education': education,
    'occupation': occupation,
    'marital_status': maritalStatus,
  };

  /// True when both hold the same seven answers; interest order does not matter.
  bool sameAnswers(Profile other) =>
      age == other.age &&
      gender == other.gender &&
      region == other.region &&
      interests.toSet().length == other.interests.toSet().length &&
      interests.toSet().containsAll(other.interests) &&
      education == other.education &&
      occupation == other.occupation &&
      maritalStatus == other.maritalStatus;
}
