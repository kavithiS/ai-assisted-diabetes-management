// UNVERIFIED: written without the Flutter SDK; run `flutter analyze` before use.

/// What C3 returns: `risk_assessment` 0.1
/// (server/services/c3_risk_xai/docs/contract_proposal.md, a proposal until agreed).
///
/// The band, the explanation and every sentence come from the server. The app never
/// computes a band, a threshold or a SHAP/LIME value. The researcher-only `debug`
/// block is deliberately not modelled: patient screens never show a probability.
library;

enum AssessmentStatus { ok, insufficientData, invalidInput }

enum RiskBand { low, moderate, high }

AssessmentStatus _parseStatus(String value) => switch (value) {
      'ok' => AssessmentStatus.ok,
      'insufficient_data' => AssessmentStatus.insufficientData,
      'invalid_input' => AssessmentStatus.invalidInput,
      _ => throw FormatException('Unknown risk_assessment status: $value'),
    };

RiskBand? _parseBand(Object? value) => switch (value) {
      null => null,
      'Low' => RiskBand.low,
      'Moderate' => RiskBand.moderate,
      'High' => RiskBand.high,
      _ => throw FormatException('Unknown risk_category: $value'),
    };

List<String> _strings(Object? value) =>
    (value as List<dynamic>? ?? const <dynamic>[]).cast<String>();

/// One SHAP factor: how much this answer moved the model's estimate.
class ShapFactor {
  const ShapFactor({
    required this.feature,
    required this.readable,
    required this.factorType,
    required this.value,
    required this.shap,
    required this.direction,
  });

  factory ShapFactor.fromJson(Map<String, dynamic> json) => ShapFactor(
        feature: json['feature'] as String,
        readable: json['readable'] as String,
        factorType: json['factor_type'] as String,
        value: (json['value'] as num).toDouble(),
        shap: (json['shap'] as num).toDouble(),
        direction: json['direction'] as String,
      );

  final String feature;
  final String readable;

  /// `modifiable`, `not modifiable` or `medical history`.
  final String factorType;
  final double value;
  final double shap;

  /// `increases risk` or `decreases risk`.
  final String direction;
}

/// One LIME rule from the local cross-check.
class LimeFactor {
  const LimeFactor({
    required this.rule,
    required this.feature,
    required this.readable,
    required this.factorType,
    required this.value,
    required this.weight,
    required this.direction,
  });

  factory LimeFactor.fromJson(Map<String, dynamic> json) => LimeFactor(
        rule: json['rule'] as String,
        feature: json['feature'] as String,
        readable: json['readable'] as String,
        factorType: json['factor_type'] as String,
        value: (json['value'] as num).toDouble(),
        weight: (json['weight'] as num).toDouble(),
        direction: json['direction'] as String,
      );

  final String rule;
  final String feature;
  final String readable;
  final String factorType;
  final double value;
  final double weight;
  final String direction;
}

class XaiAgreement {
  const XaiAgreement({
    required this.shapTop,
    required this.limeTop,
    required this.shared,
    required this.overlapRatio,
    required this.meetsTarget,
  });

  factory XaiAgreement.fromJson(Map<String, dynamic> json) => XaiAgreement(
        shapTop: _strings(json['shap_top']),
        limeTop: _strings(json['lime_top']),
        shared: _strings(json['shared']),
        overlapRatio: (json['overlap_ratio'] as num).toDouble(),
        meetsTarget: json['meets_target'] as bool,
      );

  final List<String> shapTop;
  final List<String> limeTop;
  final List<String> shared;
  final double overlapRatio;
  final bool meetsTarget;
}

class RiskExplanation {
  const RiskExplanation({
    required this.shap,
    required this.lime,
    required this.limeFidelity,
    required this.agreement,
    required this.explanationQuality,
    required this.explanationText,
  });

  factory RiskExplanation.fromJson(Map<String, dynamic> json) => RiskExplanation(
        shap: (json['shap'] as List<dynamic>)
            .map((e) => ShapFactor.fromJson(e as Map<String, dynamic>))
            .toList(),
        lime: (json['lime'] as List<dynamic>)
            .map((e) => LimeFactor.fromJson(e as Map<String, dynamic>))
            .toList(),
        limeFidelity: (json['lime_fidelity'] as num).toDouble(),
        agreement: XaiAgreement.fromJson(json['agreement'] as Map<String, dynamic>),
        explanationQuality: json['explanation_quality'] as String,
        explanationText: json['explanation_text'] as String,
      );

  final List<ShapFactor> shap;
  final List<LimeFactor> lime;
  final double limeFidelity;
  final XaiAgreement agreement;
  final String explanationQuality;

  /// Plain-language summary to show the patient as it is.
  final String explanationText;
}

class RiskAssessment {
  const RiskAssessment({
    required this.status,
    required this.disclaimer,
    this.band,
    this.referral,
    this.featureSet,
    this.modelUsed,
    this.modelVersion,
    this.dataComplete,
    this.imputedFields = const [],
    this.missingCriticalFields = const [],
    this.problems = const [],
    this.explanation,
  });

  factory RiskAssessment.fromJson(Map<String, dynamic> json) => RiskAssessment(
        status: _parseStatus(json['status'] as String),
        disclaimer: json['disclaimer'] as String,
        band: _parseBand(json['risk_category']),
        referral: json['referral'] as String?,
        featureSet: json['feature_set'] as String?,
        modelUsed: json['model_used'] as String?,
        modelVersion: json['model_version'] as String?,
        dataComplete: json['data_complete'] as bool?,
        imputedFields: _strings(json['imputed_fields']),
        missingCriticalFields: _strings(json['missing_critical_fields']),
        problems: _strings(json['problems']),
        explanation: json['explanation'] == null
            ? null
            : RiskExplanation.fromJson(json['explanation'] as Map<String, dynamic>),
      );

  final AssessmentStatus status;

  /// Must be shown on every result screen.
  final String disclaimer;

  /// Estimated risk band (only when status is ok). Show label + icon, not colour alone.
  final RiskBand? band;

  /// Present for High only; show it as a banner.
  final String? referral;
  final String? featureSet;
  final String? modelUsed;
  final String? modelVersion;
  final bool? dataComplete;
  final List<String> imputedFields;
  final List<String> missingCriticalFields;
  final List<String> problems;
  final RiskExplanation? explanation;
}
