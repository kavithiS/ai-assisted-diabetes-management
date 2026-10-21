import '../c3_strings.dart';
import 'risk_profile.dart';

/// Three example profiles. They are inputs only; every estimate comes from C3.
class RiskPreset {
  const RiskPreset({required this.label, required this.description, required this.profile});

  final String label;
  final String description;
  final RiskProfile profile;
}

const higherRiskPreset = RiskPreset(
  label: C3Strings.presetHigher,
  description: C3Strings.presetHigherNote,
  profile: RiskProfile(
    age: 58,
    sexMale: 1,
    bmi: 27.8,
    systolicBp: 150,
    diastolicBp: 95,
    pulseRate: 84,
    glucoseMmol: 9.8,
    familyHistoryDiabetes: 1,
    familyHistoryHypertension: 1,
    hypertensive: 1,
    cardiovascularDisease: 0,
    stroke: 0,
    physicalActivity: 'low',
    smoker: 0,
    medicationAdherence: 'good',
    cholesterolLevel: 'borderline_high',
    kidneyDisease: 0,
    liverDisease: 0,
    weightChangeKg: 2.5,
  ),
);

const lowerRiskPreset = RiskPreset(
  label: C3Strings.presetLower,
  description: C3Strings.presetLowerNote,
  profile: RiskProfile(
    age: 29,
    sexMale: 0,
    bmi: 21.5,
    systolicBp: 112,
    diastolicBp: 72,
    pulseRate: 72,
    glucoseMmol: 5.4,
    familyHistoryDiabetes: 0,
    familyHistoryHypertension: 0,
    hypertensive: 0,
    cardiovascularDisease: 0,
    stroke: 0,
    physicalActivity: 'high',
    smoker: 0,
    medicationAdherence: 'good',
    cholesterolLevel: 'normal',
    kidneyDisease: 0,
    liverDisease: 0,
    weightChangeKg: 0,
  ),
);

/// The higher-risk person without height and weight: BMI is critical, so the server
/// must answer `insufficient_data` and show no band.
const missingBmiPreset = RiskPreset(
  label: C3Strings.presetMissing,
  description: C3Strings.presetMissingNote,
  profile: RiskProfile(
    age: 58,
    sexMale: 1,
    systolicBp: 150,
    diastolicBp: 95,
    pulseRate: 84,
    glucoseMmol: 9.8,
    familyHistoryDiabetes: 1,
    familyHistoryHypertension: 1,
    hypertensive: 1,
    cardiovascularDisease: 0,
    stroke: 0,
    physicalActivity: 'low',
    smoker: 0,
    medicationAdherence: 'good',
    cholesterolLevel: 'borderline_high',
    kidneyDisease: 0,
    liverDisease: 0,
    weightChangeKg: 2.5,
  ),
);

const riskPresets = [higherRiskPreset, lowerRiskPreset, missingBmiPreset];
