import 'risk_assessment.dart';

/// One saved assessment from `GET /api/v1/risk/history` (FR13). The server returns no
/// answers, only what a history list needs.
class ServerHistoryItem {
  const ServerHistoryItem({
    required this.id,
    required this.assessedAt,
    required this.status,
    required this.schemaVersion,
    this.band,
    this.modelVersion,
  });

  factory ServerHistoryItem.fromJson(Map<String, dynamic> json) => ServerHistoryItem(
        id: json['id'] as String,
        assessedAt: DateTime.parse(json['assessed_at'] as String).toLocal(),
        status: json['status'] as String,
        schemaVersion: json['schema_version'] as String,
        band: switch (json['risk_category']) {
          'Low' => RiskBand.low,
          'Moderate' => RiskBand.moderate,
          'High' => RiskBand.high,
          _ => null,
        },
        modelVersion: json['model_version'] as String?,
      );

  final String id;
  final DateTime assessedAt;

  /// `ok`, `insufficient_data` or `invalid_input`.
  final String status;
  final String schemaVersion;
  final RiskBand? band;
  final String? modelVersion;
}
