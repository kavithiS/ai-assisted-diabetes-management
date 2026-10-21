# Shared app name proposal

The shared Flutter app title is set in `client/mobile_app/lib/main.dart` as
`MaterialApp(title: 'DiaCare AI', ...)`. Please change it to `DiaCare` so the
window title matches the C3 patient-facing name and Android launcher label.

The shared file was not edited by C3. The Android launcher label in
`client/mobile_app/android/app/src/main/AndroidManifest.xml` is already `DiaCare`.

## Related: dark mode in the shared shell

The C3 screens follow the phone's light or dark setting. The shared shell in
`lib/main.dart` has only a light `theme`, so in dark mode its top bar and bottom bar
stay light around a dark C3 screen. Suggested change for the client owner: add a
`darkTheme` (and a dark version of `buildAppTheme` in `lib/core/theme.dart`).

## Note for whoever builds the web app

`flutter build web` (Flutter 3.47.7) adds an `analyzer: exclude:` block to
`client/mobile_app/analysis_options.yaml`. C3 restores that shared file after each
build; please do not commit that change by accident.
