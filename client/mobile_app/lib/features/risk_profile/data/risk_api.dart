// UNVERIFIED: written without the Flutter SDK; run `flutter analyze` before use.

import '../../../core/api_client.dart';
import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import 'risk_repository.dart';

/// Live repository: talks only to the gateway through [ApiClient].
class RiskApi implements RiskRepository {
  RiskApi({ApiClient? client}) : _client = client ?? ApiClient();

  final ApiClient _client;

  /// Gateway route; the gateway forwards it to C3. No service port is used here.
  Uri get assessUri => _client.uri('/api/v1/risk/assess');

  @override
  bool get isDemoData => false;

  @override
  Future<RiskAssessment> assess(RiskProfile profile) {
    // TODO(c3): POST profile.toJson() to assessUri and return RiskAssessment.fromJson(body).
    // Needs an HTTP package in pubspec.yaml (shared file, not added yet). On a network
    // error, show an error with Retry; never fall back to the mock silently.
    throw UnimplementedError('Live C3 API call not wired yet (needs an approved HTTP package).');
  }
}
