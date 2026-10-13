// UNVERIFIED: written without the Flutter SDK; run `flutter analyze` before use.

import '../domain/risk_assessment.dart';
import '../domain/risk_profile.dart';

/// Where risk assessments come from. Screens depend on this, never on HTTP directly.
abstract interface class RiskRepository {
  /// Sends the profile to C3 (through the gateway) and returns its assessment.
  Future<RiskAssessment> assess(RiskProfile profile);

  /// True when the answers are canned demo data, so screens show a "Demo data" banner.
  bool get isDemoData;
}
