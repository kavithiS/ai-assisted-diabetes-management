// UNVERIFIED: written without the Flutter SDK; run `flutter analyze` before use.

import '../domain/risk_assessment.dart';

class RiskHistoryEntry {
  const RiskHistoryEntry({required this.assessedAt, required this.assessment});

  final DateTime assessedAt;
  final RiskAssessment assessment;
}

/// Local history of past assessments, newest first. In memory for now.
class RiskHistoryStore {
  final List<RiskHistoryEntry> _entries = [];

  List<RiskHistoryEntry> get entries => List.unmodifiable(_entries);

  void add(RiskAssessment assessment, {DateTime? at}) {
    // Only real results are kept; insufficient or invalid answers are not history.
    if (assessment.status != AssessmentStatus.ok) return;
    _entries.insert(
      0,
      RiskHistoryEntry(assessedAt: at ?? DateTime.now(), assessment: assessment),
    );
  }

  // TODO(c3): persist on the device once a storage package is approved for pubspec.yaml.
}
