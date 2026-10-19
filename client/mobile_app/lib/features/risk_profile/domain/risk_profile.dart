/// What the app sends to C3: `patient_risk_profile` 0.2
/// (server/services/c3_risk_xai/docs/contract_proposal.md, a proposal until agreed).
///
/// Every field is optional: C3 itself answers `insufficient_data` when age, BMI or
/// blood pressure is missing, so the app never guesses values.
///
/// The lifestyle answers (TAF task 1) feed the Diabetic Health Score and the
/// recommendations only; the risk model does not use them.
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
    this.physicalActivity,
    this.smoker,
    this.medicationAdherence,
    this.cholesterolLevel,
    this.kidneyDisease,
    this.liverDisease,
    this.weightChangeKg,
  });

  static const String schemaVersion = '0.2';

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

  /// `low`, `moderate` or `high`.
  final String? physicalActivity;

  /// 1 = smokes, 0 = does not.
  final int? smoker;

  /// `poor`, `fair` or `good`.
  final String? medicationAdherence;

  /// `normal`, `borderline_high` or `high` (as told by the patient's doctor).
  final String? cholesterolLevel;

  /// Diagnosed kidney / liver condition: 1 = yes, 0 = no. DHS only, never a model input.
  final int? kidneyDisease;
  final int? liverDisease;

  /// Weight now minus 3 months ago, kg.
  final double? weightChangeKg;

  /// A copy with some lifestyle answers changed (used by the what-if screen).
  RiskProfile withLifestyle({String? physicalActivity, String? cholesterolLevel}) => RiskProfile(
        age: age,
        sexMale: sexMale,
        bmi: bmi,
        systolicBp: systolicBp,
        diastolicBp: diastolicBp,
        pulseRate: pulseRate,
        glucoseMmol: glucoseMmol,
        familyHistoryDiabetes: familyHistoryDiabetes,
        familyHistoryHypertension: familyHistoryHypertension,
        hypertensive: hypertensive,
        cardiovascularDisease: cardiovascularDisease,
        stroke: stroke,
        physicalActivity: physicalActivity ?? this.physicalActivity,
        smoker: smoker,
        medicationAdherence: medicationAdherence,
        cholesterolLevel: cholesterolLevel ?? this.cholesterolLevel,
        kidneyDisease: kidneyDisease,
        liverDisease: liverDisease,
        weightChangeKg: weightChangeKg,
      );

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
      'physical_activity': physicalActivity,
      'smoker': smoker,
      'medication_adherence': medicationAdherence,
      'cholesterol_level': cholesterolLevel,
      'kidney_disease': kidneyDisease,
      'liver_disease': liverDisease,
      'weight_change_kg': weightChangeKg,
    };
    json.removeWhere((_, value) => value == null);
    return json;
  }
}
