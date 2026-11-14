import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_exception.dart';
import '../../theme/tokens.dart';
import '../../widgets/choice_select_field.dart';
import '../../widgets/interest_chips.dart';
import '../../widgets/state_message.dart';
import '../profile/profile_models.dart';
import '../answer/answer_repository.dart';
import '../profile/profile_repository.dart';
import '../surveys/eligible_surveys_screen.dart';
import '../surveys/surveys_repository.dart';
import 'auth_repository.dart';
import 'form_message.dart';

final RegExp _emailShape = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

const int _minAge = 1;
const int _maxAge = 120;

/// Creates a respondent account, then logs in with the same credentials.
class RegisterScreen extends StatefulWidget {
  const RegisterScreen({
    super.key,
    required this.authRepository,
    required this.surveysRepository,
    required this.profileRepository,
    required this.answerRepository,
  });

  final AuthRepository authRepository;
  final SurveysRepository surveysRepository;
  final ProfileRepository profileRepository;
  final AnswerRepository answerRepository;

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _age = TextEditingController();

  late Future<ProfileOptions> _options;
  String? _gender;
  String? _genderError;
  String? _region;
  String? _regionError;
  Set<String> _interests = {};
  String? _interestsError;
  bool _submitting = false;
  bool _passwordHidden = true;
  String? _error;
  Map<String, List<String>> _fieldErrors = const {};

  @override
  void initState() {
    super.initState();
    _options = widget.profileRepository.options();
  }

  void _retryOptions() {
    final next = widget.profileRepository.options();
    setState(() {
      _options = next;
    });
  }

  @override
  void dispose() {
    for (final controller in [_name, _email, _password, _age]) {
      controller.dispose();
    }
    super.dispose();
  }

  String? _serverError(String field) => _fieldErrors[field]?.join(' ');

  Future<void> _submit() async {
    if (_submitting) return;
    final formValid = _formKey.currentState!.validate();
    setState(() {
      _genderError = _gender == null ? 'Choose a gender.' : null;
      _regionError = _region == null ? 'Choose your governorate.' : null;
      _interestsError = _interests.isEmpty
          ? 'Choose at least one interest.'
          : null;
    });
    if (!formValid ||
        _genderError != null ||
        _regionError != null ||
        _interestsError != null) {
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
      _fieldErrors = const {};
    });

    final auth = widget.authRepository;
    final email = _email.text.trim();
    try {
      await auth.register(
        name: _name.text.trim(),
        email: email,
        password: _password.text,
        age: int.parse(_age.text),
        gender: _gender!,
        region: _region!,
        interests: _interests.toList(),
      );
      await auth.login(email, _password.text);
      final user = await auth.currentUser();
      if (!mounted) return;
      await Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute<void>(
          builder: (_) => EligibleSurveysScreen(
            authRepository: auth,
            surveysRepository: widget.surveysRepository,
            profileRepository: widget.profileRepository,
            answerRepository: widget.answerRepository,
            user: user,
          ),
        ),
        (route) => false,
      );
    } on ApiException catch (error) {
      _fail(error);
    } on Exception {
      _fail(const ApiException.unexpectedResponse(0));
    }
  }

  void _fail(ApiException error) {
    if (!mounted) return;
    setState(() {
      _submitting = false;
      _fieldErrors = error.fields;
      _error = error.code == ApiException.networkError
          ? 'Cannot reach the server. Is it running?'
          : (error.fields.isEmpty ? error.message : null);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create account')),
      body: Align(
        alignment: AlignmentDirectional.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: SsLayout.formMaxWidth),
          child: FutureBuilder<ProfileOptions>(
            future: _options,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              final options = snapshot.data;
              return options == null
                  ? _buildOptionsError(snapshot.error)
                  : _buildForm(options);
            },
          ),
        ),
      ),
    );
  }

  Widget _buildOptionsError(Object? error) {
    final body =
        (error is ApiException && error.code != ApiException.networkError)
        ? error.message
        : 'Cannot reach the server. Check your connection and try again.';
    return ListView(
      padding: const EdgeInsetsDirectional.all(SsSpace.s4),
      children: [
        StateMessage(
          icon: Icons.cloud_off_outlined,
          title: 'Could not load the form',
          body: body,
          action: FilledButton(
            onPressed: _retryOptions,
            child: const Text('Try again'),
          ),
        ),
      ],
    );
  }

  Widget _buildForm(ProfileOptions options) {
    final theme = Theme.of(context);
    final textTheme = theme.textTheme;
    final enabled = !_submitting;
    final interestsError = _interestsError ?? _serverError('interests');

    return SingleChildScrollView(
      padding: const EdgeInsetsDirectional.all(SsSpace.s4),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: SsSpace.s2),
            Text(
              'Your age, gender and governorate decide which surveys you see.',
              style: textTheme.bodyMedium?.copyWith(color: SsColors.inkMuted),
            ),
            const SizedBox(height: SsSpace.s6),
            TextFormField(
              controller: _name,
              enabled: enabled,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.name],
              decoration: InputDecoration(
                labelText: 'Name',
                errorText: _serverError('name'),
              ),
              validator: (value) =>
                  (value ?? '').trim().isEmpty ? 'Enter your name.' : null,
            ),
            const SizedBox(height: SsSpace.s4),
            TextFormField(
              controller: _email,
              enabled: enabled,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.email],
              decoration: InputDecoration(
                labelText: 'Email',
                errorText: _serverError('email'),
              ),
              validator: (value) {
                final email = (value ?? '').trim();
                if (email.isEmpty) return 'Enter your email.';
                if (!_emailShape.hasMatch(email)) {
                  return 'Enter a valid email address.';
                }
                return null;
              },
            ),
            const SizedBox(height: SsSpace.s4),
            TextFormField(
              controller: _password,
              enabled: enabled,
              obscureText: _passwordHidden,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.newPassword],
              decoration: InputDecoration(
                labelText: 'Password',
                errorText: _serverError('password'),
                suffixIcon: IconButton(
                  tooltip: _passwordHidden ? 'Show password' : 'Hide password',
                  icon: Icon(
                    _passwordHidden
                        ? Icons.visibility_outlined
                        : Icons.visibility_off_outlined,
                  ),
                  onPressed: () =>
                      setState(() => _passwordHidden = !_passwordHidden),
                ),
              ),
              validator: (value) =>
                  (value ?? '').isEmpty ? 'Enter a password.' : null,
            ),
            const SizedBox(height: SsSpace.s4),
            TextFormField(
              controller: _age,
              enabled: enabled,
              keyboardType: TextInputType.number,
              textInputAction: TextInputAction.next,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              decoration: InputDecoration(
                labelText: 'Age',
                errorText: _serverError('age'),
              ),
              validator: (value) {
                final age = int.tryParse(value ?? '');
                if (age == null || age < _minAge || age > _maxAge) {
                  return 'Enter an age from $_minAge to $_maxAge.';
                }
                return null;
              },
            ),
            const SizedBox(height: SsSpace.s4),
            Text('Gender', style: textTheme.labelLarge),
            const SizedBox(height: SsSpace.s2),
            SegmentedButton<String>(
              emptySelectionAllowed: true,
              showSelectedIcon: false,
              segments: const [
                ButtonSegment(value: 'MALE', label: Text('Male')),
                ButtonSegment(value: 'FEMALE', label: Text('Female')),
              ],
              selected: {?_gender},
              onSelectionChanged: enabled
                  ? (selection) => setState(() {
                      _gender = selection.isEmpty ? null : selection.first;
                      _genderError = null;
                    })
                  : null,
            ),
            if ((_genderError ?? _serverError('gender')) != null) ...[
              const SizedBox(height: SsSpace.s1),
              Text(
                (_genderError ?? _serverError('gender'))!,
                style: textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.error,
                ),
              ),
            ],
            const SizedBox(height: SsSpace.s4),
            ChoiceSelectField(
              label: 'Governorate',
              options: options.governorates,
              value: _region,
              errorText: _regionError ?? _serverError('region'),
              onChanged: enabled
                  ? (code) => setState(() {
                      _region = code;
                      _regionError = null;
                    })
                  : null,
            ),
            const SizedBox(height: SsSpace.s4),
            Text('Interests', style: textTheme.labelLarge),
            const SizedBox(height: SsSpace.s1),
            Text(
              'Choose at least one. You can change them later in your '
              'profile.',
              style: textTheme.bodySmall?.copyWith(color: SsColors.inkMuted),
            ),
            const SizedBox(height: SsSpace.s2),
            InterestChips(
              options: options.interests,
              selected: _interests,
              enabled: enabled,
              errorText: interestsError,
              onChanged: (next) => setState(() {
                _interests = next;
                _interestsError = null;
              }),
            ),
            if (_error != null) ...[
              const SizedBox(height: SsSpace.s4),
              FormMessage(text: _error!, color: theme.colorScheme.error),
            ],
            const SizedBox(height: SsSpace.s6),
            FilledButton(
              onPressed: enabled ? _submit : null,
              child: _submitting
                  ? const SizedBox(
                      width: SsLayout.indicatorSize,
                      height: SsLayout.indicatorSize,
                      child: CircularProgressIndicator(
                        strokeWidth: SsLayout.indicatorStroke,
                      ),
                    )
                  : const Text('Create account'),
            ),
          ],
        ),
      ),
    );
  }
}
