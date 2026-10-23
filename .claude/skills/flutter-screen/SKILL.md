---
name: flutter-screen
description: Use when adding or changing a screen in the Flutter respondent app under frontend/lib/, or when a task says "add screen", "new page", "show survey list/form", or edits frontend/lib/features/.
---

# Add a Flutter screen

Run every command from `frontend/`. API contract: `planning/API.md`. CLAUDE.md still applies (Plan Mode first,
`/handoff` last).

## Layout
```
frontend/lib/features/<name>/
  <name>_screen.dart        # widgets only
  <name>_repository.dart    # the ONLY class that calls the API for this feature
  <name>_models.dart        # plain Dart models parsed from the API JSON
frontend/test/features/<name>/<name>_screen_test.dart
```
One folder per feature, then register the route or home entry in `lib/app.dart`.
`lib/features/home/home_screen.dart` shows token usage only; it predates repositories, so do not copy its data handling.

## Rules
1. **Design tokens only.** Colors and text from `Theme.of(context)` and `SsColors`; spacing from `SsSpace`
   (`s1`, `s2`, `s4`, `s6`); corners from `SsRadius` (`lib/theme/tokens.dart`); text styles from `SsType`
   (`lib/theme/app_theme.dart`). No `Color(0x...)`, `Colors.*`, or numeric padding/size/radius literals in
   feature code. Missing token: add it to `tokens.dart` and say so, do not inline a value.
2. **Repository boundary.** The screen never touches HTTP or JSON. It asks the repository, which returns models
   or throws a typed error built from the API error shape `{"error": {"code", "message", "fields"?}}`.
3. **Four states, always:** loading, error (message + retry), empty (explain what to do next), data.
   Create the future once (`initState` or a controller), never inside `build`.
4. **API access.** Base URL, Bearer header and refresh-on-401 belong to one shared API client
   (`127.0.0.1` on Chrome, `10.0.2.2` on the emulator). No HTTP package in `pubspec.yaml` and no shared client yet?
   Ask before adding a dependency or creating one.
5. Accessibility: text scales, labels on icon-only buttons, tap targets from Material widgets
   (`FilledButton`, `ListTile`), which meet 48 px without a size literal.
6. Right-to-left safe: use `EdgeInsetsDirectional` and `AlignmentDirectional`; the product is Arabic and English.

## Test
One widget test per screen in `frontend/test/features/<name>/`: pump the screen with a fake repository and assert
the loading, error, empty and data states.

## Before finishing
```
flutter pub get
flutter analyze
flutter test
```
Both must report no issues. `dart format` runs automatically after each Dart edit (project hook).

## Common mistakes
- Hard-coded `EdgeInsets.all(16)`: use `SsSpace.s4`.
- Calling the API inside `build`: do it from the repository in `initState` or a `FutureBuilder` source.
- Testing only the happy path.
