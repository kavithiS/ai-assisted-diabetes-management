import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';
import '../domain/server_history.dart';
import '../domain/service_status.dart';

/// Where risk assessments come from. Screens depend on this, never on HTTP directly.
abstract interface class RiskRepository {
  /// Sends the profile to C3 (through the gateway) and returns its assessment.
  /// With `save: false` (what-if previews) the device ID is not sent, so nothing is stored.
  Future<RiskAssessment> assess(RiskProfile profile, {bool save = true});

  /// Whether C3 is reachable through the gateway and its models are loaded.
  Future<ServiceStatus> status();

  /// This device's saved assessments from the server, newest first (FR13).
  Future<List<ServerHistoryItem>> history();

  /// Deletes this device's saved records on the server (FR16). Returns how many.
  Future<int> deleteMyRecords();

  /// True when the answers are canned demo data, so screens show a "Demo data" banner.
  bool get isDemoData;
}
