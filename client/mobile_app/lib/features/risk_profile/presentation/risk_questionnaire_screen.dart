import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../c3_theme.dart';
import '../domain/field_rules.dart';
import '../domain/risk_profile.dart';
import 'risk_analysis_screen.dart';
import 'risk_controller.dart';
import 'widgets/c3_widgets.dart';

/// "Health & Lifestyle Info" (prototype Module 3): one scrolling form that builds a
/// RiskProfile 0.2 and opens the analysis screen.
///
/// Ranges are checked before sending (FieldRule copies the server's ranges). Empty or
/// unselected answers are sent as missing: the server decides what is critical.
class RiskQuestionnaireScreen extends StatefulWidget {
  const RiskQuestionnaireScreen({super.key, required this.controller, this.initial});

  final RiskController controller;

  /// Previous answers to start from ("Update health info").
  final RiskProfile? initial;

  @override
  State<RiskQuestionnaireScreen> createState() => _RiskQuestionnaireScreenState();
}

class _RiskQuestionnaireScreenState extends State<RiskQuestionnaireScreen> {
  final _formKey = GlobalKey<FormState>();

  /// One key per number field, in screen order, to scroll to the first answer with a problem.
  final _fieldKeys = <TextEditingController, GlobalKey<FormFieldState<String>>>{};
  late final TextEditingController _age;
  final _height = TextEditingController();
  final _weight = TextEditingController();
  late final TextEditingController _systolic;
  late final TextEditingController _diastolic;
  late final TextEditingController _pulse;
  late final TextEditingController _glucose;
  late final TextEditingController _weightChange;
  int? _sexMale;
  late bool _hasGlucose;
  String? _activity;
  int? _smoker;
  String? _adherence;
  String? _cholesterol;
  int? _kidney;
  int? _liver;
  int? _familyDiabetes;
  int? _familyPressure;
  int? _hypertensive;
  int? _heartDisease;
  int? _stroke;

  static String _text(num? value) {
    if (value == null) return '';
    return value == value.roundToDouble() ? value.toInt().toString() : value.toString();
  }

  @override
  void initState() {
    super.initState();
    final p = widget.initial ?? const RiskProfile();
    _age = TextEditingController(text: _text(p.age));
    _systolic = TextEditingController(text: _text(p.systolicBp));
    _diastolic = TextEditingController(text: _text(p.diastolicBp));
    _pulse = TextEditingController(text: _text(p.pulseRate));
    _glucose = TextEditingController(text: _text(p.glucoseMmol));
    _weightChange = TextEditingController(text: _text(p.weightChangeKg));
    _hasGlucose = p.glucoseMmol != null;
    _sexMale = p.sexMale;
    _activity = p.physicalActivity;
    _smoker = p.smoker;
    _adherence = p.medicationAdherence;
    _cholesterol = p.cholesterolLevel;
    _kidney = p.kidneyDisease;
    _liver = p.liverDisease;
    _familyDiabetes = p.familyHistoryDiabetes;
    _familyPressure = p.familyHistoryHypertension;
    _hypertensive = p.hypertensive;
    _heartDisease = p.cardiovascularDisease;
    _stroke = p.stroke;
    _height.addListener(() => setState(() {}));
    _weight.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    for (final c in [
      _age,
      _height,
      _weight,
      _systolic,
      _diastolic,
      _pulse,
      _glucose,
      _weightChange,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  double? _number(TextEditingController c) =>
      double.tryParse(c.text.trim().replaceAll(',', '.').replaceAll('+', ''));

  /// BMI from height and weight; otherwise the previous BMI, if there is one.
  double? get _bmi {
    final height = _number(_height);
    final weight = _number(_weight);
    if (height != null && weight != null) {
      if (!heightRule.accepts(height) || !weightRule.accepts(weight)) {
        return null;
      }
      return bmiFrom(heightCm: height, weightKg: weight);
    }
    return widget.initial?.bmi;
  }

  FormFieldValidator<String> _range(FieldRule rule) => (text) {
        if (text == null || text.trim().isEmpty) return null;
        final value = double.tryParse(text.trim().replaceAll(',', '.').replaceAll('+', ''));
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
        physicalActivity: _activity,
        smoker: _smoker,
        medicationAdherence: _adherence,
        cholesterolLevel: _cholesterol,
        kidneyDisease: _kidney,
        liverDisease: _liver,
        weightChangeKg: _number(_weightChange),
      );

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) {
      // The button is at the bottom: bring the first problem into view and say so.
      final firstError = _fieldKeys.values
          .map((key) => key.currentState)
          .firstWhere((state) => state?.hasError ?? false, orElse: () => null);
      if (firstError != null) {
        Scrollable.ensureVisible(firstError.context,
            alignment: 0.2, duration: const Duration(milliseconds: 300));
      }
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(const SnackBar(content: Text(C3Strings.checkAnswers)));
      return;
    }
    c3Push<void>(context, RiskAnalysisScreen(controller: widget.controller, profile: _profile()));
  }

  Widget _field(TextEditingController c, String label, FieldRule rule, {String? help}) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: TextFormField(
          key: _fieldKeys.putIfAbsent(c, GlobalKey<FormFieldState<String>>.new),
          controller: c,
          keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
          decoration: InputDecoration(labelText: '$label (${rule.unit})', helperText: help),
          validator: _range(rule),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final bmi = _bmi;
    return Scaffold(
      appBar: AppBar(title: const Text(C3Strings.inputTitle)),
      body: Form(
        key: _formKey,
        // Not a lazy ListView: every field stays built, so every field is validated
        // even when it is scrolled off screen.
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(C3Strings.inputIntro, style: TextStyle(color: C3Colors.text2)),
              const C3Label(C3Strings.stepAbout),
              _field(_age, C3Strings.age, ageRule, help: C3Strings.required),
              ChoiceGroup<int>(
                label: C3Strings.sex,
                value: _sexMale,
                options: const {1: C3Strings.male, 0: C3Strings.female},
                onChanged: (v) => setState(() => _sexMale = v),
              ),
              const C3Label(C3Strings.stepBody),
              Row(
                children: [
                  Expanded(child: _field(_height, C3Strings.height, heightRule)),
                  const SizedBox(width: 10),
                  Expanded(child: _field(_weight, C3Strings.weight, weightRule)),
                ],
              ),
              Text(
                bmi == null ? C3Strings.bmiNeeded : '${C3Strings.bmiPrefix}$bmi',
                style: const TextStyle(color: C3Colors.text2),
              ),
              const C3Label(C3Strings.bloodPressure),
              Row(
                children: [
                  Expanded(child: _field(_systolic, C3Strings.systolic, systolicRule)),
                  const SizedBox(width: 10),
                  Expanded(child: _field(_diastolic, C3Strings.diastolic, diastolicRule)),
                ],
              ),
              const C3Label(C3Strings.lifestyleTitle),
              const Text(C3Strings.lifestyleNote,
                  style: TextStyle(color: C3Colors.text2, fontSize: 12)),
              const SizedBox(height: 8),
              ChoiceGroup<String>(
                label: C3Strings.activityLevel,
                value: _activity,
                options: const {
                  'low': C3Strings.activityLow,
                  'moderate': C3Strings.activityModerate,
                  'high': C3Strings.activityHigh,
                },
                onChanged: (v) => setState(() => _activity = v),
              ),
              ChoiceGroup<int>(
                label: C3Strings.smokingStatus,
                value: _smoker,
                options: const {1: C3Strings.yes, 0: C3Strings.no},
                onChanged: (v) => setState(() => _smoker = v),
              ),
              ChoiceGroup<String>(
                label: C3Strings.adherence,
                value: _adherence,
                options: const {
                  'poor': C3Strings.adherencePoor,
                  'fair': C3Strings.adherenceFair,
                  'good': C3Strings.adherenceGood,
                },
                onChanged: (v) => setState(() => _adherence = v),
              ),
              ChoiceGroup<String>(
                label: C3Strings.cholesterol,
                value: _cholesterol,
                options: const {
                  'normal': C3Strings.cholesterolNormal,
                  'borderline_high': C3Strings.cholesterolBorderlineHigh,
                  'high': C3Strings.cholesterolHigh,
                },
                onChanged: (v) => setState(() => _cholesterol = v),
              ),
              ChoiceGroup<int>(
                label: C3Strings.kidney,
                value: _kidney,
                options: const {1: C3Strings.yes, 0: C3Strings.no},
                onChanged: (v) => setState(() => _kidney = v),
              ),
              ChoiceGroup<int>(
                label: C3Strings.liver,
                value: _liver,
                options: const {1: C3Strings.yes, 0: C3Strings.no},
                onChanged: (v) => setState(() => _liver = v),
              ),
              _field(_weightChange, C3Strings.weightChange, weightChangeRule,
                  help: C3Strings.weightChangeHelp),
              const C3Label(C3Strings.optionalClinical),
              _field(_pulse, C3Strings.restingPulse, pulseRule, help: C3Strings.optional),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text(C3Strings.hasGlucose),
                value: _hasGlucose,
                onChanged: (value) => setState(() => _hasGlucose = value),
              ),
              if (_hasGlucose)
                _field(_glucose, C3Strings.bloodGlucose, glucoseRule)
              else
                const Text(C3Strings.glucoseOffNote, style: TextStyle(color: C3Colors.text2)),
              const C3Label(C3Strings.historyTitle),
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
              const SizedBox(height: 12),
              FilledButton(onPressed: _submit, child: const Text(C3Strings.saveAndRecalculate)),
            ],
          ),
        ),
      ),
    );
  }
}

/// Labelled row of choice chips (prototype "pick" chips). Tapping the selected chip
/// again clears it, so an answer can be left out instead of guessed.
class ChoiceGroup<T> extends StatelessWidget {
  const ChoiceGroup({
    super.key,
    required this.label,
    required this.value,
    required this.options,
    required this.onChanged,
  });

  final String label;
  final T? value;
  final Map<T, String> options;
  final ValueChanged<T?> onChanged;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Wrap(
              spacing: 8,
              children: [
                for (final entry in options.entries)
                  ChoiceChip(
                    label: Text(entry.value),
                    selected: value == entry.key,
                    onSelected: (_) => onChanged(value == entry.key ? null : entry.key),
                  ),
              ],
            ),
          ],
        ),
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
        padding: const EdgeInsets.only(bottom: 10),
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
