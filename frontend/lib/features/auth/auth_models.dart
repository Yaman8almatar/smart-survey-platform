/// The signed-in respondent, as returned by `GET /me/`.
class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.name,
    required this.role,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      id: json['id'] as int,
      email: json['email'] as String,
      name: json['name'] as String,
      role: json['role'] as String,
    );
  }

  final int id;
  final String email;
  final String name;
  final String role;

  /// Name for the app bar; falls back to the email when the name is blank.
  String get displayName => name.trim().isEmpty ? email : name;
}
