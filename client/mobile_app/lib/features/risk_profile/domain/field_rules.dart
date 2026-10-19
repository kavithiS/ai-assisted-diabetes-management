/// Accepted input ranges, copied from the C3 server (`ml/predict.py` VALID_RANGES).
///
/// These only stop typing mistakes before sending. The server checks again and is the
/// authority. They are not model thresholds or risk cut-offs: no model logic lives here.
class FieldRule {
  const FieldRule(this.min, this.max, this.unit);

  final double min;
  final double max;
  final String unit;

  bool accepts(double value) => value >= min && value <= max;
}

const ageRule = FieldRule(18, 100, 'years');
const bmiRule = FieldRule(12, 70, 'kg/m²');
const systolicRule = FieldRule(70, 260, 'mmHg');
const diastolicRule = FieldRule(40, 150, 'mmHg');
const pulseRule = FieldRule(35, 200, 'beats per minute');
const glucoseRule = FieldRule(1.5, 40, 'mmol/L');

/// Only used to work out BMI from what people know (height and weight).
const heightRule = FieldRule(100, 250, 'cm');
const weightRule = FieldRule(20, 300, 'kg');

/// BMI = weight (kg) / height (m)², rounded to one decimal. Plain arithmetic.
double bmiFrom({required double heightCm, required double weightKg}) {
  final metres = heightCm / 100;
  return double.parse((weightKg / (metres * metres)).toStringAsFixed(1));
}
