import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../../../core/api_client.dart';
import 'foot_analysis.dart';

/// Calls C4 through the gateway: `POST /api/v1/foot/analyze`.
///
/// Uses a plain `http.Client` for now. Switch the default to C1's `AuthHttpClient` (adds the
/// login token) once the login work is merged into `main`.
class FootApi {
  FootApi({ApiClient? apiClient, http.Client? httpClient, Duration? timeout})
      : _apiClient = apiClient ?? ApiClient(),
        _http = httpClient ?? http.Client(),
        timeout = timeout ?? _defaultTimeout;

  final ApiClient _apiClient;
  final http.Client _http;

  /// Upload plus inference. The model may need a moment on a slow laptop.
  static const Duration _defaultTimeout = Duration(seconds: 30);
  final Duration timeout;

  Future<FootAnalysis> analyze({required Uint8List imageBytes}) async {
    final mediaType = detectImageType(imageBytes);
    if (mediaType == null) {
      throw const FootApiException('UNSUPPORTED_MEDIA_TYPE', 'Please use a JPEG or PNG photo.');
    }

    final request = http.MultipartRequest('POST', _apiClient.uri('/api/v1/foot/analyze'))
      ..files.add(http.MultipartFile.fromBytes(
        'image',
        imageBytes,
        filename: mediaType.subtype == 'png' ? 'foot.png' : 'foot.jpg',
        contentType: mediaType,
      ));

    final http.Response response;
    try {
      response = await http.Response.fromStream(await _http.send(request).timeout(timeout));
    } on TimeoutException {
      throw const FootApiException(
        'TIMEOUT',
        'The server is taking too long. Make sure the server is running and try again.',
      );
    } on http.ClientException {
      throw const FootApiException(
        'NETWORK',
        'Cannot reach the server. Make sure the server is running on your PC and try again.',
      );
    }

    if (response.statusCode != 200) throw FootApiException.fromResponse(response);
    try {
      return FootAnalysis.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    } catch (_) {
      // Malformed JSON or an unexpected shape: never crash the screen.
      throw const FootApiException('BAD_RESPONSE', _genericMessage);
    }
  }

  /// Detects JPEG or PNG from the file bytes (the API checks the bytes, not the name).
  static MediaType? detectImageType(Uint8List bytes) {
    if (bytes.length >= 3 && bytes[0] == 0xFF && bytes[1] == 0xD8 && bytes[2] == 0xFF) {
      return MediaType('image', 'jpeg');
    }
    const png = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
    if (bytes.length < png.length) return null;
    for (var i = 0; i < png.length; i++) {
      if (bytes[i] != png[i]) return null;
    }
    return MediaType('image', 'png');
  }
}

const String _genericMessage =
    'Something went wrong while checking your photo. Please try again.';

class FootApiException implements Exception {
  const FootApiException(this.code, this.message);

  /// Reads the shared error envelope: `{"error": {"code", "message", ...}, "request_id"}`.
  factory FootApiException.fromResponse(http.Response response) {
    var code = 'HTTP_${response.statusCode}';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['error'] is Map && body['error']['code'] is String) {
        code = body['error']['code'] as String;
      }
    } on FormatException {
      // Not JSON (e.g. a proxy error page): keep the HTTP status code.
    }
    return FootApiException(code, _patientMessage(code));
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
      case 'UNAUTHORIZED':
        return 'Your session has ended. Please log in again.';
      default:
        return _genericMessage;
    }
  }

  @override
  String toString() => 'FootApiException($code): $message';
}
