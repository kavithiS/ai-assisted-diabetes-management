/// Estimated risk band from C4. The app shows the band, never a model score.
enum FootRiskBand {
  low('Low'),
  medium('Medium'),
  high('High');

  const FootRiskBand(this.apiValue);

  final String apiValue;

  static FootRiskBand parse(Object? value) {
    for (final band in values) {
      if (band.apiValue == value) return band;
    }
    throw FormatException('Unknown risk band: $value');
  }
}

/// Response of `POST /api/v1/foot/analyze`.
class FootAnalysis {
  const FootAnalysis({
    required this.analysisId,
    required this.classification,
    required this.riskBand,
    required this.recommendations,
    required this.disclaimer,
    required this.isMock,
  });

  /// Throws [FormatException] when the JSON does not have the expected shape.
  factory FootAnalysis.fromJson(Map<String, dynamic> json) {
    final meta = json['meta'];
    final recommendations = json['recommendations'];
    final classification = json['classification'];
    if (meta is! Map ||
        recommendations is! List ||
        classification is! String ||
        json['analysis_id'] is! String ||
        json['disclaimer'] is! String ||
        meta['is_mock'] is! bool) {
      throw const FormatException('Unexpected foot analysis response');
    }
    return FootAnalysis(
      analysisId: json['analysis_id'] as String,
      classification: classification,
      riskBand: FootRiskBand.parse(json['risk_band']),
      recommendations: [for (final r in recommendations) r.toString()],
      disclaimer: json['disclaimer'] as String,
      isMock: meta['is_mock'] as bool,
    );
  }

  final String analysisId;

  /// `normal` or `ulcer` (estimated).
  final String classification;
  final FootRiskBand riskBand;
  final List<String> recommendations;
  final String disclaimer;

  /// True when the server has no trained model and the result is synthetic.
  final bool isMock;
}
