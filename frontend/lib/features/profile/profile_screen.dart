import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_exception.dart';
import '../../theme/app_theme.dart';
import '../../theme/tokens.dart';
import '../../widgets/choice_select_field.dart';
import '../../widgets/interest_chips.dart';
import '../../widgets/state_message.dart';
import '../auth/auth_repository.dart';
import '../auth/login_screen.dart';
import '../surveys/surveys_repository.dart';
import 'profile_hero.dart';
import 'profile_models.dart';
import 'profile_repository.dart';

const int _minAge = 1;
const int _maxAge = 120;

enum _Phase { loading, error, content }

/// The form sections, top to bottom, with the API fields each one holds.
enum _Section {
  about(['age', 'gender']),
  place(['region']),
  interests(['interests']),
  background(['education', 'occupation', 'marital_status']);

  const _Section(this.fields);

  final List<String> fields;

  static _Section? of(String field) {
    for (final section in values) {
      if (section.fields.contains(field)) return section;
    }
    return null;
  }
}

/// No answers at all: what an absent profile is compared with.
const Profile _blank = Profile(
  age: -1,
  gender: '',
  region: '',
  interests: [],
  education: '',
  occupation: '',
  maritalStatus: '',
);

/// FR-02: the respondent reads and edits the seven profile details.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({
    super.key,
    required this.authRepository,
    required this.surveysRepository,
    required this.profileRepository,
  });

  final AuthRepository authRepository;
  final SurveysRepository surveysRepository;
  final ProfileRepository profileRepository;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _scroll = ScrollController();
  final _sectionKeys = {for (final s in _Section.values) s: GlobalKey()};
  final _age = TextEditingController();

  _Phase _phase = _Phase.loading;
  Object? _loadError;
  ProfileOptions? _options;
  Profile? _saved;

  String? _gender;
  String? _region;
  Set<String> _interests = {};
  String? _education;
  String? _occupation;
  String? _maritalStatus;

  bool _saving = false;

  /// Set by a blocked save; client errors then follow the values live.
  bool _showErrors = false;
  Map<String, String> _serverErrors = const {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _scroll.dispose();
    _age.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait<Object?>([
        widget.profileRepository.options(),
        widget.profileRepository.load(),
      ]);
      if (!mounted) return;
      setState(() {
        _options = results[0]! as ProfileOptions;
        _apply(results[1] as Profile?);
        _phase = _Phase.content;
      });
    } on SessionExpiredException {
      _openLogin();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _loadError = error;
        _phase = _Phase.error;
      });
    }
  }

  void _retry() {
    setState(() => _phase = _Phase.loading);
    _load();
  }

  void _apply(Profile? profile) {
    _saved = profile;
    _age.text = profile == null ? '' : '${profile.age}';
    _gender = _orNull(profile?.gender);
    _region = _orNull(profile?.region);
    _interests = {...?profile?.interests};
    _education = _orNull(profile?.education);
    _occupation = _orNull(profile?.occupation);
    _maritalStatus = _orNull(profile?.maritalStatus);
  }

  static String? _orNull(String? code) =>
      (code == null || code.isEmpty) ? null : code;

  int? get _validAge {
    final age = int.tryParse(_age.text);
    return (age != null && age >= _minAge && age <= _maxAge) ? age : null;
  }

  Profile _draft() => Profile(
    age: int.tryParse(_age.text) ?? _blank.age,
    gender: _gender ?? '',
    region: _region ?? '',
    interests: [
      for (final option in _options!.interests)
        if (_interests.contains(option.code)) option.code,
    ],
    education: _education ?? '',
    occupation: _occupation ?? '',
    maritalStatus: _maritalStatus ?? '',
  );

  bool get _dirty => !_draft().sameAnswers(_saved ?? _blank);

  /// Field -> message: client checks (after a blocked save) and server field errors.
  Map<String, String> get _errors {
    final errors = <String, String>{};
    if (_showErrors) {
      if (_validAge == null) {
        errors['age'] = 'Enter an age from $_minAge to $_maxAge.';
      }
      if (_gender == null) errors['gender'] = 'Choose a gender.';
      if (_region == null) errors['region'] = 'Choose your governorate.';
      if (_interests.isEmpty) {
        errors['interests'] = 'Choose at least one interest.';
      }
    }
    for (final entry in _serverErrors.entries) {
      errors.putIfAbsent(entry.key, () => entry.value);
    }
    return errors;
  }

  void _edit(String field, VoidCallback change) {
    setState(() {
      change();
      if (_serverErrors.containsKey(field)) {
        _serverErrors = {..._serverErrors}..remove(field);
      }
    });
  }

  Future<void> _save() async {
    if (_saving) return;
    setState(() => _showErrors = true);
    final errors = _errors;
    if (errors.isNotEmpty) {
      _scrollToFirstError(errors);
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    setState(() => _saving = true);
    try {
      final saved = await widget.profileRepository.save(_draft());
      if (!mounted) return;
      setState(() {
        _saving = false;
        _showErrors = false;
        _serverErrors = const {};
        _apply(saved);
      });
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(
          const SnackBar(
            content: Row(
              children: [
                Icon(
                  Icons.check,
                  size: SsLayout.iconSmall,
                  color: SsColors.surfaceRaised,
                ),
                SizedBox(width: SsSpace.s2),
                Expanded(child: Text('Profile saved')),
              ],
            ),
          ),
        );
    } on SessionExpiredException {
      _openLogin();
    } on ApiException catch (error) {
      if (!mounted) return;
      final fields = {
        for (final entry in error.fields.entries)
          if (_Section.of(entry.key) != null) entry.key: entry.value.join(' '),
      };
      setState(() {
        _saving = false;
        _serverErrors = fields;
      });
      if (fields.isNotEmpty) {
        _scrollToFirstError(fields);
        return;
      }
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text('Not saved. ${error.message}'),
            action: SnackBarAction(label: 'Try again', onPressed: _save),
          ),
        );
    }
  }

  void _scrollToFirstError(Map<String, String> errors) {
    final section = _Section.values.firstWhere(
      (s) => s.fields.any(errors.containsKey),
    );
    final target = _sectionKeys[section]!.currentContext;
    if (target == null) return;
    Scrollable.ensureVisible(
      target,
      alignment: 0,
      duration: SsMotion.of(context, SsMotion.standard),
      curve: SsMotion.standardCurve,
    );
  }

  void _openLogin() {
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute<void>(
        builder: (_) => LoginScreen(
          authRepository: widget.authRepository,
          surveysRepository: widget.surveysRepository,
          profileRepository: widget.profileRepository,
          notice: 'Your session ended. Please log in again.',
        ),
      ),
      (route) => false,
    );
  }

  Future<void> _confirmLeave() async {
    final discard = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Discard your changes?'),
        content: const Text('Your edits to this profile will be lost.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Keep editing'),
          ),
          TextButton(
            style: TextButton.styleFrom(foregroundColor: SsColors.danger),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Discard'),
          ),
        ],
      ),
    );
    if (discard == true && mounted) {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final content = _phase == _Phase.content;
    final errors = content ? _errors : const <String, String>{};
    final Widget body = switch (_phase) {
      _Phase.loading => const ProfileSkeleton(key: ValueKey(_Phase.loading)),
      _Phase.error => _LoadError(
        key: const ValueKey(_Phase.error),
        error: _loadError,
        onRetry: _retry,
        onRefresh: _load,
      ),
      _Phase.content => _buildContent(errors),
    };

    return PopScope(
      canPop: !content || !_dirty,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _confirmLeave();
      },
      child: Scaffold(
        backgroundColor: _phase == _Phase.error ? null : SsColors.surfaceRaised,
        appBar: AppBar(title: const Text('Your profile')),
        body: AnimatedSwitcher(
          duration: SsMotion.of(context, SsMotion.standard),
          layoutBuilder: (current, previous) => Stack(
            alignment: AlignmentDirectional.topCenter,
            children: [...previous, ?current],
          ),
          child: body,
        ),
        bottomNavigationBar: content ? _buildSaveBar(errors) : null,
      ),
    );
  }

  Widget _buildContent(Map<String, String> errors) {
    final options = _options!;
    final enabled = !_saving;
    final textTheme = Theme.of(context).textTheme;

    Widget section(
      _Section s,
      String title,
      _Status status, {
      String? helper,
      required List<Widget> children,
    }) {
      final attention = s.fields.any(errors.containsKey);
      return Padding(
        key: _sectionKeys[s],
        padding: const EdgeInsetsDirectional.symmetric(
          horizontal: SsSpace.s4,
          vertical: SsSpace.s5,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: SsType.heading.copyWith(color: SsColors.ink),
                  ),
                ),
                _SectionStatus(
                  status: attention ? const _Status.attention() : status,
                ),
              ],
            ),
            if (helper != null) ...[
              const SizedBox(height: SsSpace.s1),
              Text(
                helper,
                style: SsType.body.copyWith(color: SsColors.inkMuted),
              ),
            ],
            const SizedBox(height: SsSpace.s4),
            ...children,
          ],
        ),
      );
    }

    const divider = Divider(
      height: SsLayout.hairline,
      thickness: SsLayout.hairline,
      color: SsColors.line,
      indent: SsSpace.s4,
      endIndent: SsSpace.s4,
    );

    final aboutMissing =
        (_validAge == null ? 1 : 0) + (_gender == null ? 1 : 0);
    final backgroundSet = [
      _education,
      _occupation,
      _maritalStatus,
    ].where((v) => v != null).length;
    final genderError = errors['gender'];

    return SingleChildScrollView(
      key: const ValueKey(_Phase.content),
      controller: _scroll,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ProfileHero(saved: _saved),
          _RisingSheet(
            child: ProfileContentWidth(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  section(
                    _Section.about,
                    'About you',
                    _Status.toGo(aboutMissing),
                    children: [
                      TextField(
                        controller: _age,
                        enabled: enabled,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                        ],
                        decoration: InputDecoration(
                          labelText: 'Age',
                          suffixText: 'years',
                          errorText: errors['age'],
                        ),
                        onChanged: (_) => _edit('age', () {}),
                      ),
                      const SizedBox(height: SsSpace.s4),
                      Text('Gender', style: textTheme.labelLarge),
                      const SizedBox(height: SsSpace.s2),
                      SegmentedButton<String>(
                        emptySelectionAllowed: true,
                        segments: const [
                          ButtonSegment(value: 'MALE', label: Text('Male')),
                          ButtonSegment(value: 'FEMALE', label: Text('Female')),
                        ],
                        selected: {?_gender},
                        onSelectionChanged: enabled
                            ? (selection) => _edit(
                                'gender',
                                () => _gender = selection.isEmpty
                                    ? null
                                    : selection.first,
                              )
                            : null,
                      ),
                      if (genderError != null) ...[
                        const SizedBox(height: SsSpace.s1),
                        Text(
                          genderError,
                          style: SsType.caption.copyWith(
                            color: SsColors.danger,
                          ),
                        ),
                      ],
                    ],
                  ),
                  divider,
                  section(
                    _Section.place,
                    'Where you live',
                    _Status.toGo(_region == null ? 1 : 0),
                    children: [
                      ChoiceSelectField(
                        label: 'Governorate',
                        options: options.governorates,
                        value: _region,
                        errorText: errors['region'],
                        onChanged: enabled
                            ? (code) => _edit('region', () => _region = code)
                            : null,
                      ),
                    ],
                  ),
                  divider,
                  section(
                    _Section.interests,
                    'Interests',
                    _Status.toGo(_interests.isEmpty ? 1 : 0),
                    helper:
                        'Choose at least one topic you like answering '
                        'surveys about.',
                    children: [
                      InterestChips(
                        options: options.interests,
                        selected: _interests,
                        enabled: enabled,
                        errorText: errors['interests'],
                        onChanged: (next) =>
                            _edit('interests', () => _interests = next),
                      ),
                    ],
                  ),
                  divider,
                  section(
                    _Section.background,
                    'Background',
                    backgroundSet == 3
                        ? const _Status.done()
                        : _Status.optional(backgroundSet),
                    helper:
                        'Some surveys are for certain groups. These details '
                        'help them find you.',
                    children: [
                      ChoiceSelectField(
                        label: 'Education',
                        options: options.education,
                        value: _education,
                        errorText: errors['education'],
                        onChanged: enabled
                            ? (code) =>
                                  _edit('education', () => _education = code)
                            : null,
                      ),
                      const SizedBox(height: SsSpace.s4),
                      ChoiceSelectField(
                        label: 'Occupation',
                        options: options.occupation,
                        value: _occupation,
                        errorText: errors['occupation'],
                        onChanged: enabled
                            ? (code) =>
                                  _edit('occupation', () => _occupation = code)
                            : null,
                      ),
                      const SizedBox(height: SsSpace.s4),
                      ChoiceSelectField(
                        label: 'Marital status',
                        options: options.maritalStatus,
                        value: _maritalStatus,
                        errorText: errors['marital_status'],
                        onChanged: enabled
                            ? (code) => _edit(
                                'marital_status',
                                () => _maritalStatus = code,
                              )
                            : null,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSaveBar(Map<String, String> errors) {
    final count = errors.length;
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: SsColors.surfaceRaised,
        border: Border(
          top: BorderSide(color: SsColors.line, width: SsLayout.hairline),
        ),
      ),
      child: SafeArea(
        top: false,
        // Centred and as wide as the form, so the button lines up on wide windows.
        child: Align(
          alignment: AlignmentDirectional.topCenter,
          heightFactor: 1,
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: SsLayout.contentMaxWidth,
            ),
            child: Padding(
              padding: const EdgeInsetsDirectional.fromSTEB(
                SsSpace.s4,
                SsSpace.s3,
                SsSpace.s4,
                SsSpace.s4,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (count > 0) ...[
                    Semantics(
                      liveRegion: true,
                      child: Row(
                        children: [
                          const Icon(
                            Icons.error_outline,
                            size: SsLayout.iconSmall,
                            color: SsColors.danger,
                          ),
                          const SizedBox(width: SsSpace.s2),
                          Expanded(
                            child: Text(
                              count == 1
                                  ? 'Fix the 1 highlighted field, then save.'
                                  : 'Fix the $count highlighted fields, then save.',
                              style: SsType.label.copyWith(
                                color: SsColors.danger,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: SsSpace.s3),
                  ],
                  FilledButton(
                    onPressed: _dirty && !_saving ? _save : null,
                    child: _saving
                        ? const SizedBox(
                            width: SsLayout.indicatorSize,
                            height: SsLayout.indicatorSize,
                            child: CircularProgressIndicator(
                              strokeWidth: SsLayout.indicatorStroke,
                            ),
                          )
                        : Text(
                            _saved == null ? 'Save profile' : 'Save changes',
                          ),
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

/// The sheet over the hero: pulled up, and on first paint it rises and fades in.
class _RisingSheet extends StatelessWidget {
  const _RisingSheet({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 1, end: 0),
      duration: SsMotion.of(context, SsMotion.standard),
      curve: SsMotion.standardCurve,
      builder: (context, t, child) => Transform.translate(
        offset: Offset(0, -SsSpace.s6 + SsSpace.s4 * t),
        child: Opacity(opacity: 1 - t, child: child),
      ),
      child: DecoratedBox(decoration: profileSheetDecoration, child: child),
    );
  }
}

/// A section header status.
class _Status {
  const _Status.done() : text = 'Done', kind = _StatusKind.done;

  const _Status.attention()
    : text = 'Needs attention',
      kind = _StatusKind.attention;

  _Status.optional(int set)
    : text = 'Optional, $set of 3',
      kind = _StatusKind.muted;

  factory _Status.toGo(int missing) => missing == 0
      ? const _Status.done()
      : _Status._('$missing to go', _StatusKind.muted);

  const _Status._(this.text, this.kind);

  final String text;
  final _StatusKind kind;
}

enum _StatusKind { done, muted, attention }

class _SectionStatus extends StatelessWidget {
  const _SectionStatus({required this.status});

  final _Status status;

  @override
  Widget build(BuildContext context) {
    final (color, icon) = switch (status.kind) {
      _StatusKind.done => (SsColors.brand, Icons.check),
      _StatusKind.attention => (SsColors.danger, Icons.error_outline),
      _StatusKind.muted => (SsColors.inkMuted, null),
    };
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (icon != null) ...[
          Icon(icon, size: SsLayout.iconSmall, color: color),
          const SizedBox(width: SsSpace.s1),
        ],
        Text(status.text, style: SsType.label.copyWith(color: color)),
      ],
    );
  }
}

class _LoadError extends StatelessWidget {
  const _LoadError({
    super.key,
    required this.error,
    required this.onRetry,
    required this.onRefresh,
  });

  final Object? error;
  final VoidCallback onRetry;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final error = this.error;
    final body =
        (error is ApiException && error.code != ApiException.networkError)
        ? error.message
        : 'Cannot reach the server. Check your connection and try again.';
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsetsDirectional.all(SsSpace.s4),
        children: [
          ProfileContentWidth(
            child: StateMessage(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load your profile',
              body: body,
              action: FilledButton(
                onPressed: onRetry,
                child: const Text('Try again'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
