import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../domain/field_rules.dart';
import '../domain/risk_profile.dart';
import 'risk_controller.dart';
import 'risk_result_screen.dart';

/// Seven-step questionnaire that builds a RiskProfile (contract 0.1) and opens the result.
///
/// Ranges are checked before sending (FieldRule copies the server's ranges). Empty
/// answers are sent as missing: the server decides what is critical and says so.
class RiskQuestionnaireScreen extends StatefulWidget {
  const RiskQuestionnaireScreen({super.key, required this.controller});

  final RiskController controller;

  @override
  State<RiskQuestionnaireScreen> createState() => _RiskQuestionnaireScreenState();
}

class _RiskQuestionnaireScreenState extends State<RiskQuestionnaireScreen> {
  static const _stepCount = 7;
  final _formKeys = List.generate(_stepCount, (_) => GlobalKey<FormState>());
  int _step = 0;

  final _age = TextEditingController();
  final _height = TextEditingController();
  final _weight = TextEditingController();
  final _systolic = TextEditingController();
  final _diastolic = TextEditingController();
  final _pulse = TextEditingController();
  final _glucose = TextEditingController();
  int? _sexMale;
  bool _hasGlucose = false;
  int? _familyDiabetes;
  int? _familyPressure;
  int? _hypertensive;
  int? _heartDisease;
  int? _stroke;

  @override
  void initState() {
    super.initState();
    _height.addListener(() => setState(() {}));
    _weight.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    for (final c in [_age, _height, _weight, _systolic, _diastolic, _pulse, _glucose]) {
      c.dispose();
    }
    super.dispose();
  }

  double? _number(TextEditingController c) => double.tryParse(c.text.trim().replaceAll(',', '.'));

  double? get _bmi {
    final height = _number(_height);
    final weight = _number(_weight);
    if (height == null || weight == null) return null;
    if (!heightRule.accepts(height) || !weightRule.accepts(weight)) return null;
    return bmiFrom(heightCm: height, weightKg: weight);
  }

  /// Empty is allowed (sent as missing); otherwise the value must be in range.
  FormFieldValidator<String> _range(FieldRule rule) => (text) {
        if (text == null || text.trim().isEmpty) return null;
        final value = double.tryParse(text.trim().replaceAll(',', '.'));
        if (value == null) return C3Strings.notANumber;
        return rule.accepts(value) ? null : C3Strings.outOfRange(rule.min, rule.max);
      };

  RiskProfile _profile() => RiskProfile(
        age: _number(_age),
        sexMale: _sexMale,
        bmi: _bmi,
        systolicBp: _number(_systolic),
        diastolicBp: _number(_diastolic),
        pulseRate: _number(_pulse),
        glucoseMmol: _hasGlucose ? _number(_glucose) : null,
        familyHistoryDiabetes: _familyDiabetes,
        familyHistoryHypertension: _familyPressure,
        hypertensive: _hypertensive,
        cardiovascularDisease: _heartDisease,
        stroke: _stroke,
      );

  void _continue() {
    if (!(_formKeys[_step].currentState?.validate() ?? true)) return;
    if (_step < _stepCount - 1) {
      setState(() => _step += 1);
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => RiskResultScreen(controller: widget.controller, profile: _profile()),
      ),
    );
  }

  Widget _numberField(TextEditingController c, String label, FieldRule rule, {String? help}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextFormField(
          controller: c,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(
            labelText: '$label (${rule.unit})',
            helperText: help,
            helperMaxLines: 2,
            border: const OutlineInputBorder(),
          ),
          validator: _range(rule),
        ),
      );

  Widget _form(int index, List<Widget> children) => Form(
        key: _formKeys[index],
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
      );

  @override
  Widget build(BuildContext context) {
    final bmi = _bmi;
    final steps = [
      _step0(),
      Step(
        title: const Text(C3Strings.stepBody),
        isActive: _step >= 1,
        content: _form(1, [
          _numberField(_height, 'Height', heightRule, help: C3Strings.required),
          _numberField(_weight, 'Weight', weightRule, help: C3Strings.required),
          if (bmi != null) Text('${C3Strings.bmiPrefix}$bmi'),
        ]),
      ),
      Step(
        title: const Text(C3Strings.stepPressure),
        isActive: _step >= 2,
        content: _form(2, [
          _numberField(_systolic, 'Upper number (systolic)', systolicRule, help: C3Strings.required),
          _numberField(_diastolic, 'Lower number (diastolic)', diastolicRule, help: C3Strings.required),
        ]),
      ),
      Step(
        title: const Text(C3Strings.stepPulse),
        isActive: _step >= 3,
        content: _form(3, [_numberField(_pulse, 'Resting pulse', pulseRule, help: C3Strings.optional)]),
      ),
      Step(
        title: const Text(C3Strings.stepGlucose),
        isActive: _step >= 4,
        content: _form(4, [
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text(C3Strings.hasGlucose),
            value: _hasGlucose,
            onChanged: (value) => setState(() => _hasGlucose = value),
          ),
          if (_hasGlucose)
            _numberField(_glucose, 'Blood glucose', glucoseRule)
          else
            const Text(C3Strings.glucoseOffNote),
        ]),
      ),
      Step(
        title: const Text(C3Strings.stepFamily),
        isActive: _step >= 5,
        content: _form(5, [
          YesNoQuestion(
            question: C3Strings.familyDiabetes,
            value: _familyDiabetes,
            onChanged: (v) => setState(() => _familyDiabetes = v),
          ),
          YesNoQuestion(
            question: C3Strings.familyPressure,
            value: _familyPressure,
            onChanged: (v) => setState(() => _familyPressure = v),
          ),
        ]),
      ),
      Step(
        title: const Text(C3Strings.stepMedical),
        isActive: _step >= 6,
        content: _form(6, [
          YesNoQuestion(
            question: C3Strings.diagnosedPressure,
            value: _hypertensive,
            onChanged: (v) => setState(() => _hypertensive = v),
          ),
          YesNoQuestion(
            question: C3Strings.heartDisease,
            value: _heartDisease,
            onChanged: (v) => setState(() => _heartDisease = v),
          ),
          YesNoQuestion(
            question: C3Strings.stroke,
            value: _stroke,
            onChanged: (v) => setState(() => _stroke = v),
          ),
        ]),
      ),
    ];
    return Scaffold(
      appBar: AppBar(title: const Text(C3Strings.questionnaireTitle)),
      body: Stepper(
        currentStep: _step,
        steps: steps,
        onStepTapped: (index) => setState(() => _step = index),
        onStepContinue: _continue,
        onStepCancel: _step == 0 ? null : () => setState(() => _step -= 1),
        controlsBuilder: (context, details) => Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Wrap(
            spacing: 12,
            children: [
              FilledButton(
                onPressed: details.onStepContinue,
                child: Text(_step == _stepCount - 1 ? C3Strings.getResult : C3Strings.next),
              ),
              if (details.onStepCancel != null)
                TextButton(onPressed: details.onStepCancel, child: const Text(C3Strings.back)),
            ],
          ),
        ),
      ),
    );
  }

  Step _step0() => Step(
        title: const Text(C3Strings.stepAbout),
        isActive: true,
        content: _form(0, [
          _numberField(_age, 'Age', ageRule, help: C3Strings.required),
          const Text(C3Strings.sex),
          Wrap(
            spacing: 8,
            children: [
              ChoiceChip(
                label: const Text(C3Strings.male),
                selected: _sexMale == 1,
                onSelected: (_) => setState(() => _sexMale = 1),
              ),
              ChoiceChip(
                label: const Text(C3Strings.female),
                selected: _sexMale == 0,
                onSelected: (_) => setState(() => _sexMale = 0),
              ),
            ],
          ),
        ]),
      );
}

/// Yes / No / Not sure. "Not sure" is sent as missing (null), never guessed.
class YesNoQuestion extends StatelessWidget {
  const YesNoQuestion({
    super.key,
    required this.question,
    required this.value,
    required this.onChanged,
  });

  final String question;
  final int? value;
  final ValueChanged<int?> onChanged;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(question),
            Wrap(
              spacing: 8,
              children: [
                for (final (label, option) in [
                  (C3Strings.yes, 1),
                  (C3Strings.no, 0),
                  (C3Strings.notSure, null),
                ])
                  ChoiceChip(
                    label: Text(label),
                    selected: value == option,
                    onSelected: (_) => onChanged(option),
                  ),
              ],
            ),
          ],
        ),
      );
}
