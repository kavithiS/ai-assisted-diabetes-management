import 'risk_profile.dart';

/// Three made-up people for the PP1 demo. They are INPUTS only and match the Python
/// examples in `server/services/c3_risk_xai/src/c3_risk_xai/ml/predict.py`
/// (EXAMPLE_PATIENT and LOW_RISK_PATIENT), so the app and Python can be compared.
class RiskPreset {
  const RiskPreset({required this.label, required this.description, required this.profile});

  final String label;
  final String description;
  final RiskProfile profile;
}

const higherRiskPreset = RiskPreset(
  label: 'Higher-risk example',
  description: '58-year-old man, high blood pressure, family history, glucose 9.8',
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
  ),
);

const lowerRiskPreset = RiskPreset(
  label: 'Lower-risk example',
  description: '29-year-old woman, normal blood pressure, glucose 5.4',
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
  ),
);

/// The higher-risk person without height and weight: BMI is critical, so the server
/// must answer `insufficient_data` and show no band.
const missingBmiPreset = RiskPreset(
  label: 'Missing BMI example',
  description: 'Same person as the higher-risk example, but no height or weight',
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
  ),
);

const riskPresets = [higherRiskPreset, lowerRiskPreset, missingBmiPreset];
