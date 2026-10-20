import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../../../core/api_client.dart';
import '../../auth/data/auth_http_client.dart';
import 'meal_analysis.dart';

/// Calls C1 through the gateway: `POST /api/v1/meals/analyze`.
class MealApi {
  MealApi({ApiClient? apiClient, http.Client? httpClient, Duration? analyzeTimeout})
      : _apiClient = apiClient ?? ApiClient(),
        _http = httpClient ?? AuthHttpClient(),
        analyzeTimeout = analyzeTimeout ?? _defaultAnalyzeTimeout;

  final ApiClient _apiClient;
  final http.Client _http;

  /// Timeout for the meal-analysis request (upload + inference).
  /// Longer than general requests because the model may need to warm up.
  static const Duration _defaultAnalyzeTimeout = Duration(seconds: 60);
  final Duration analyzeTimeout;

  Future<MealAnalysis> analyze({
    required Uint8List imageBytes,
    required MealType mealType,
    DateTime? capturedAt,
  }) async {
    final mediaType = detectImageType(imageBytes);
    if (mediaType == null) {
      throw const MealApiException(
        'UNSUPPORTED_MEDIA_TYPE',
        'Please use a JPEG or PNG photo.',
      );
    }

    final request = http.MultipartRequest('POST', _apiClient.uri('/api/v1/meals/analyze'))
      ..fields['meal_type'] = mealType.apiValue
      ..fields['captured_at'] = toRfc3339(capturedAt ?? DateTime.now())
      ..files.add(http.MultipartFile.fromBytes(
        'image',
        imageBytes,
        filename: mediaType.subtype == 'png' ? 'meal.png' : 'meal.jpg',
        contentType: mediaType,
      ));

    final http.Response response;
    try {
      response = await http.Response.fromStream(
          await _http.send(request).timeout(analyzeTimeout));
    } on TimeoutException {
      throw const MealApiException(
        'TIMEOUT',
        'The server is taking too long. Make sure the server is running and try again.',
      );
    } on http.ClientException {
      throw const MealApiException(
        'NETWORK',
        'Cannot reach the server. Make sure the server is running on your PC and try again.',
      );
    }

    if (response.statusCode != 200) throw MealApiException.fromResponse(response);
    try {
      return MealAnalysis.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    } catch (_) {
      // Malformed JSON or an unexpected shape: never crash the screen.
      throw const MealApiException('BAD_RESPONSE', _genericMessage);
    }
  }

  /// Detects JPEG or PNG from the file bytes (the API checks the bytes, not the name).
  static MediaType? detectImageType(Uint8List bytes) {
    if (bytes.length >= 3 && bytes[0] == 0xFF && bytes[1] == 0xD8 && bytes[2] == 0xFF) {
      return MediaType('image', 'jpeg');
    }
    const png = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
    if (bytes.length >= png.length) {
      for (var i = 0; i < png.length; i++) {
        if (bytes[i] != png[i]) return null;
      }
      return MediaType('image', 'png');
    }
    return null;
  }

  /// Formats [time] as RFC 3339 with its UTC offset, e.g. `2026-10-03T12:30:00+05:30`.
  static String toRfc3339(DateTime time) {
    String two(int n) => n.toString().padLeft(2, '0');
    final offset = time.timeZoneOffset;
    final sign = offset.isNegative ? '-' : '+';
    final abs = offset.abs();
    return '${time.year.toString().padLeft(4, '0')}-${two(time.month)}-${two(time.day)}'
        'T${two(time.hour)}:${two(time.minute)}:${two(time.second)}'
        '$sign${two(abs.inHours)}:${two(abs.inMinutes % 60)}';
  }
}

const String _genericMessage =
    'Something went wrong while analysing your meal. Please try again.';

const String _sessionEndedMessage = 'Your session has ended. Please log in again.';

class MealApiException implements Exception {
  const MealApiException(this.code, this.message);

  /// Reads the shared error envelope: `{"error": {"code", "message", ...}, "request_id"}`.
  factory MealApiException.fromResponse(http.Response response) {
    var code = 'HTTP_${response.statusCode}';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['error'] is Map && body['error']['code'] is String) {
        code = body['error']['code'] as String;
      }
    } on FormatException {
      // Not JSON (e.g. a proxy error page): keep the HTTP status code.
    }
    return MealApiException(code, _patientMessage(code));
  }

  final String code;

  /// Message safe to show to the patient.
  final String message;

  static String _patientMessage(String code) {
    switch (code) {
      case 'IMAGE_TOO_LARGE':
        return 'This photo is too large. Please take a new photo.';
      case 'UNSUPPORTED_MEDIA_TYPE':
        return 'Please use a JPEG or PNG photo.';
      case 'IMAGE_REQUIRED':
      case 'IMAGE_UNREADABLE':
        return 'The photo could not be read. Please take a new photo.';
      case 'INVALID_METADATA':
        return 'Some meal details were not accepted. Check the meal type and try again.';
      case 'UNAUTHORIZED':
        return _sessionEndedMessage;
      default:
        return _genericMessage;
    }
  }

  @override
  String toString() => 'MealApiException($code): $message';
}
