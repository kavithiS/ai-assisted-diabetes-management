/// What the app sends to C3: `patient_risk_profile` 0.1
/// (server/services/c3_risk_xai/docs/contract_proposal.md, a proposal until agreed).
///
/// Every field is optional: C3 itself answers `insufficient_data` when age, BMI or
/// blood pressure is missing, so the app never guesses values.
class RiskProfile {
  const RiskProfile({
    this.age,
    this.sexMale,
    this.bmi,
    this.systolicBp,
    this.diastolicBp,
    this.pulseRate,
    this.glucoseMmol,
    this.familyHistoryDiabetes,
    this.familyHistoryHypertension,
    this.hypertensive,
    this.cardiovascularDisease,
    this.stroke,
  });

  static const String schemaVersion = '0.1';

  /// Years.
  final double? age;

  /// 1 = male, 0 = female.
  final int? sexMale;

  /// kg/m2. Compute it from height and weight in the questionnaire.
  final double? bmi;

  /// mmHg.
  final double? systolicBp;

  /// mmHg.
  final double? diastolicBp;

  /// Beats per minute.
  final double? pulseRate;

  /// mmol/L. When given, C3 uses its glucose model.
  final double? glucoseMmol;

  /// 1 = yes, 0 = no for the five history questions.
  final int? familyHistoryDiabetes;
  final int? familyHistoryHypertension;
  final int? hypertensive;
  final int? cardiovascularDisease;
  final int? stroke;

  /// JSON body for POST /api/v1/risk/assess. Unanswered fields are left out.
  Map<String, Object?> toJson() {
    final json = <String, Object?>{
      'schema_version': schemaVersion,
      'age': age,
      'sex_male': sexMale,
      'bmi': bmi,
      'systolic_bp': systolicBp,
      'diastolic_bp': diastolicBp,
      'pulse_rate': pulseRate,
      'glucose_mmol': glucoseMmol,
      'family_history_diabetes': familyHistoryDiabetes,
      'family_history_hypertension': familyHistoryHypertension,
      'hypertensive': hypertensive,
      'cardiovascular_disease': cardiovascularDisease,
      'stroke': stroke,
    };
    json.removeWhere((_, value) => value == null);
    return json;
  }
}
