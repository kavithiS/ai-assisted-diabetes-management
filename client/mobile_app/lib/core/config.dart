/// App configuration.
class AppConfig {
  const AppConfig._();

  /// Base URL of the API gateway (port 8000). The client talks only to the gateway.
  ///
  /// The default reaches the host machine from the Android emulator. Override with
  /// `flutter run --dart-define=API_BASE_URL=http://<host>:8000`.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
}
