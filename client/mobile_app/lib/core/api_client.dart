import 'config.dart';

/// Client for the API gateway. Feature owners add their calls here.
class ApiClient {
  ApiClient({String? baseUrl}) : baseUrl = baseUrl ?? AppConfig.apiBaseUrl;

  final String baseUrl;

  /// Builds a gateway URL, e.g. `uri('/api/v1/meals/analyze')`.
  Uri uri(String path) => Uri.parse(baseUrl).resolve(path);
}
