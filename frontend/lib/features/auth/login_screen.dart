import 'package:flutter/material.dart';

import '../../core/api/api_exception.dart';
import '../../theme/tokens.dart';
import '../surveys/eligible_surveys_screen.dart';
import '../surveys/surveys_repository.dart';
import 'auth_repository.dart';

final RegExp _emailShape = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

/// Email and password login for respondents.
class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.authRepository,
    required this.surveysRepository,
    this.notice,
  });

  final AuthRepository authRepository;
  final SurveysRepository surveysRepository;

  /// Shown above the form, e.g. after the session ended.
  final String? notice;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _submitting = false;
  bool _passwordHidden = true;
  String? _error;
  Map<String, List<String>> _fieldErrors = const {};

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting || !_formKey.currentState!.validate()) {
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
      _fieldErrors = const {};
    });

    try {
      await widget.authRepository.login(
        _emailController.text.trim(),
        _passwordController.text,
      );
      final user = await widget.authRepository.currentUser();
      if (!mounted) return;
      await Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(
          builder: (_) => EligibleSurveysScreen(
            authRepository: widget.authRepository,
            surveysRepository: widget.surveysRepository,
            user: user,
          ),
        ),
      );
    } on NotRespondentException {
      _fail(
        'This app is for respondents. Providers and admins use the website.',
      );
    } on SessionExpiredException {
      _fail('Your session ended. Please log in again.');
    } on ApiException catch (error) {
      _failWith(error);
    }
  }

  void _failWith(ApiException error) {
    if (!mounted) return;
    setState(() {
      _submitting = false;
      _fieldErrors = error.fields;
      _error = switch (error.code) {
        ApiException.invalidCredentials => 'Email or password is incorrect.',
        ApiException.networkError => 'Cannot reach the server. Is it running?',
        _ => error.fields.isEmpty ? error.message : null,
      };
    });
  }

  void _fail(String message) {
    if (!mounted) return;
    setState(() {
      _submitting = false;
      _error = message;
    });
  }

  String? _fieldError(String name) => _fieldErrors[name]?.join(' ');

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textTheme = theme.textTheme;
    final notice = widget.notice;

    return Scaffold(
      appBar: AppBar(title: const Text('Smart Survey')),
      body: Align(
        alignment: AlignmentDirectional.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: SsLayout.formMaxWidth),
          child: SingleChildScrollView(
            padding: const EdgeInsetsDirectional.all(SsSpace.s4),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: SsSpace.s6),
                  Text('Log in', style: textTheme.displaySmall),
                  const SizedBox(height: SsSpace.s2),
                  Text(
                    'See the surveys that match your profile.',
                    style: textTheme.bodyMedium?.copyWith(
                      color: SsColors.inkMuted,
                    ),
                  ),
                  const SizedBox(height: SsSpace.s6),
                  if (notice != null) ...[
                    _Message(text: notice, color: SsColors.inkMuted),
                    const SizedBox(height: SsSpace.s4),
                  ],
                  TextFormField(
                    controller: _emailController,
                    enabled: !_submitting,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.email],
                    textInputAction: TextInputAction.next,
                    decoration: InputDecoration(
                      labelText: 'Email',
                      errorText: _fieldError('email'),
                    ),
                    validator: (value) {
                      final email = value?.trim() ?? '';
                      if (email.isEmpty) return 'Enter your email.';
                      if (!_emailShape.hasMatch(email)) {
                        return 'Enter a valid email address.';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: SsSpace.s4),
                  TextFormField(
                    controller: _passwordController,
                    enabled: !_submitting,
                    obscureText: _passwordHidden,
                    autofillHints: const [AutofillHints.password],
                    textInputAction: TextInputAction.done,
                    onFieldSubmitted: (_) => _submit(),
                    decoration: InputDecoration(
                      labelText: 'Password',
                      errorText: _fieldError('password'),
                      suffixIcon: IconButton(
                        tooltip: _passwordHidden
                            ? 'Show password'
                            : 'Hide password',
                        icon: Icon(
                          _passwordHidden
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                        ),
                        onPressed: () =>
                            setState(() => _passwordHidden = !_passwordHidden),
                      ),
                    ),
                    validator: (value) => (value == null || value.isEmpty)
                        ? 'Enter your password.'
                        : null,
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: SsSpace.s4),
                    _Message(text: _error!, color: theme.colorScheme.error),
                  ],
                  const SizedBox(height: SsSpace.s6),
                  FilledButton(
                    onPressed: _submitting ? null : _submit,
                    child: _submitting
                        ? const SizedBox(
                            width: SsLayout.indicatorSize,
                            height: SsLayout.indicatorSize,
                            child: CircularProgressIndicator(
                              strokeWidth: SsLayout.indicatorStroke,
                            ),
                          )
                        : const Text('Log in'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Message extends StatelessWidget {
  const _Message({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Text(
        text,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: color),
      ),
    );
  }
}
