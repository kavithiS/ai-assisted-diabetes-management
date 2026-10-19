import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/api_client.dart';
import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import '../domain/service_status.dart';
import 'risk_repository.dart';

enum RiskApiErrorKind { timeout, network, notReady, gateway, server, badResponse }

/// A failed call, with a message the screen can show next to a Retry button.
class RiskApiException implements Exception {
  const RiskApiException(this.kind, this.message);

  final RiskApiErrorKind kind;
  final String message;

  @override
  String toString() => message;
}

/// Live repository: talks only to the gateway through [ApiClient].
///
/// On any failure it throws [RiskApiException]. It never falls back to demo data.
class RiskApi implements RiskRepository {
  RiskApi({
    ApiClient? client,
    http.Client? httpClient,
    this.researcherMode = false,
    this.timeout = const Duration(seconds: 10),
  })  : _client = client ?? ApiClient(),
        _http = httpClient ?? http.Client();

  final ApiClient _client;
  final http.Client _http;

  /// Adds `?debug=true`; the server only honours it in research mode.
  final bool researcherMode;
  final Duration timeout;

  /// Gateway route; the gateway forwards it to C3. No service port is used here.
  Uri get assessUri => _client.uri('/api/v1/risk/assess');
  Uri get statusUri => _client.uri('/api/v1/risk/status');

  @override
  bool get isDemoData => false;

  @override
  Future<RiskAssessment> assess(RiskProfile profile) async {
    final uri =
        researcherMode ? assessUri.replace(queryParameters: {'debug': 'true'}) : assessUri;
    final body = await _send(
      () => _http.post(
        uri,
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode(profile.toJson()),
      ),
    );
    try {
      return RiskAssessment.fromJson(body);
    } on FormatException catch (error) {
      throw RiskApiException(RiskApiErrorKind.badResponse, 'Unexpected answer: ${error.message}');
    }
  }

  @override
  Future<ServiceStatus> status() async => ServiceStatus.fromJson(await _send(() => _http.get(statusUri)));

  Future<Map<String, dynamic>> _send(Future<http.Response> Function() request) async {
    final http.Response response;
    try {
      response = await request().timeout(timeout);
    } on TimeoutException {
      throw RiskApiException(
        RiskApiErrorKind.timeout,
        'No answer within ${timeout.inSeconds} seconds. The model may be warming up.',
      );
    } on http.ClientException catch (error) {
      throw RiskApiException(
        RiskApiErrorKind.network,
        'Cannot reach the gateway at ${_client.baseUrl} (${error.message}).',
      );
    }
    switch (response.statusCode) {
      case 200:
        break;
      case 503:
        throw const RiskApiException(
          RiskApiErrorKind.notReady,
          'The risk model is not loaded on the server yet.',
        );
      case 502:
        throw const RiskApiException(
          RiskApiErrorKind.gateway,
          'The gateway cannot reach the risk service (C3). Is it running on port 8003?',
        );
      default:
        throw RiskApiException(
          RiskApiErrorKind.server,
          'The server answered with error ${response.statusCode}.',
        );
    }
    final Object? decoded;
    try {
      decoded = jsonDecode(utf8.decode(response.bodyBytes));
    } on FormatException {
      throw const RiskApiException(RiskApiErrorKind.badResponse, 'The answer was not valid JSON.');
    }
    if (decoded is! Map<String, dynamic>) {
      throw const RiskApiException(RiskApiErrorKind.badResponse, 'The answer had an unexpected shape.');
    }
    return decoded;
  }
}
