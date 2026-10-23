import 'package:flutter/material.dart';

import 'features/home/home_screen.dart';
import 'theme/app_theme.dart';

/// Root widget of the Smart Survey respondent app.
class SmartSurveyApp extends StatelessWidget {
  const SmartSurveyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Survey',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: const HomeScreen(),
    );
  }
}
