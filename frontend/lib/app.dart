import 'package:flutter/material.dart';

import 'features/auth/auth_repository.dart';
import 'features/auth/login_screen.dart';
import 'features/surveys/eligible_surveys_screen.dart';
import 'features/surveys/surveys_repository.dart';
import 'theme/app_theme.dart';

/// Root widget of the Smart Survey respondent app.
class SmartSurveyApp extends StatelessWidget {
  const SmartSurveyApp({
    super.key,
    required this.authRepository,
    required this.surveysRepository,
  });

  final AuthRepository authRepository;
  final SurveysRepository surveysRepository;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Survey',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: AuthGate(
        authRepository: authRepository,
        surveysRepository: surveysRepository,
      ),
    );
  }
}

/// Decides the first screen: the list for a valid stored session, else login.
class AuthGate extends StatefulWidget {
  const AuthGate({
    super.key,
    required this.authRepository,
    required this.surveysRepository,
  });

  final AuthRepository authRepository;
  final SurveysRepository surveysRepository;

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  late final Future<Widget> _firstScreen = _resolve();

  Future<Widget> _resolve() async {
    final auth = widget.authRepository;
    if (await auth.hasSession()) {
      try {
        final user = await auth.currentUser();
        return EligibleSurveysScreen(
          authRepository: auth,
          surveysRepository: widget.surveysRepository,
          user: user,
        );
      } on Exception {
        // Expired, not a respondent, or server down: fall back to login.
      }
    }
    return LoginScreen(
      authRepository: auth,
      surveysRepository: widget.surveysRepository,
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Widget>(
      future: _firstScreen,
      builder: (context, snapshot) {
        return snapshot.data ??
            const Scaffold(body: Center(child: CircularProgressIndicator()));
      },
    );
  }
}
