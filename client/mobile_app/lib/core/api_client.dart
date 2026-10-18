import 'dart:async';
import 'dart:convert';
import 'dart:io' show SocketException;

import 'package:http/http.dart' as http;

import '../features/glucose/glucose_models.dart';
import 'config.dart';

/// Client for the API gateway. Feature owners add their calls here.
class ApiClient {
  ApiClient({
    String? baseUrl,
    http.Client? httpClient,
    this.timeout = const Duration(seconds: 20),
  })  : baseUrl = baseUrl ?? AppConfig.apiBaseUrl,
        _http = httpClient ?? http.Client();

  final String baseUrl;

  /// Upper bound for a whole request, so a stalled server cannot leave the UI spinning.
  final Duration timeout;

  final http.Client _http;

  /// Builds a gateway URL, e.g. `uri('/api/v1/meals/analyze')`.
  Uri uri(String path) => Uri.parse(baseUrl).resolve(path);

  /// Requests a four-hour glucose forecast through the gateway (C2).
  Future<GlucoseForecast> forecastGlucose(
      GlucoseForecastRequest request) async {
    final json = await postJson('/api/v1/glucose/forecast', request.toJson());
    try {
      return GlucoseForecast.fromJson(json);
    } on FormatException {
      throw const ApiException(
          'The server sent a response this app could not read.');
    }
  }

  /// POSTs a JSON body and returns the decoded JSON object. Throws [ApiException]
  /// with a user-facing message on any failure.
  Future<Map<String, dynamic>> postJson(
      String path, Map<String, Object> body) async {
    final http.Response response;
    try {
      response = await _http
          .post(
            uri(path),
            headers: const {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: jsonEncode(body),
          )
          .timeout(timeout);
    } on TimeoutException {
      throw const ApiException(
        'The forecast took too long. Check your connection and try again.',
      );
    } on http.ClientException {
      throw const ApiException(
        'Cannot reach the DiaCare server. Make sure the backend is running and the address is correct.',
      );
    } on SocketException {
      throw const ApiException(
        'Cannot reach the DiaCare server. Make sure the backend is running and the address is correct.',
      );
    }

    // The API always sends UTF-8 JSON; decode the bytes rather than relying on headers.
    final text = utf8.decode(response.bodyBytes, allowMalformed: true);
    if (response.statusCode != 200) {
      throw ApiException(_messageForStatus(response.statusCode, text),
          statusCode: response.statusCode);
    }

    try {
      final decoded = jsonDecode(text);
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('Expected a JSON object.');
      }
      return decoded;
    } on FormatException {
      throw const ApiException(
          'The server sent a response this app could not read.');
    }
  }

  /// Releases the underlying HTTP connections.
  void close() => _http.close();
}

/// A failed API call. [message] is safe to show to the user.
class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => 'ApiException($statusCode): $message';
}

String _messageForStatus(int status, String body) {
  switch (status) {
    case 422:
      return 'The server rejected these values. Check the form and try again.';
    case 502:
      return 'The forecasting service is unavailable right now. Try again shortly.';
    case 503:
      return 'The glucose model is unavailable right now. Try again later.';
    default:
      return 'The server returned an unexpected error (HTTP $status).${_detailFrom(body)}';
  }
}

String _detailFrom(String body) {
  try {
    final decoded = jsonDecode(body);
    if (decoded is Map && decoded['detail'] is String) {
      return ' ${decoded['detail']}';
    }
  } on FormatException {
    // Non-JSON error bodies are ignored; the status code is enough.
  }
  return '';
}
