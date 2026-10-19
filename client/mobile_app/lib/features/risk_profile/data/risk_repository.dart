import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import '../domain/service_status.dart';

/// Where risk assessments come from. Screens depend on this, never on HTTP directly.
abstract interface class RiskRepository {
  /// Sends the profile to C3 (through the gateway) and returns its assessment.
  Future<RiskAssessment> assess(RiskProfile profile);

  /// Whether C3 is reachable through the gateway and its models are loaded.
  Future<ServiceStatus> status();

  /// True when the answers are canned demo data, so screens show a "Demo data" banner.
  bool get isDemoData;
}
