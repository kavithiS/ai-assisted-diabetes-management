import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';
import 'data/health_profile.dart';

class QuestionnaireScreen extends StatefulWidget {
  const QuestionnaireScreen({
    super.key,
    required this.userId,
    this.initialProfile,
    this.store,
    this.onCompleted,
  });

  final String userId;
  final HealthProfile? initialProfile;
  final HealthProfileStore? store;
  final VoidCallback? onCompleted;

  @override
  State<QuestionnaireScreen> createState() => _QuestionnaireScreenState();
}

class _QuestionnaireScreenState extends State<QuestionnaireScreen> {
  int _step = 0;
  bool _saving = false;
  String? _saveError;
  late final HealthProfileStore _store =
      widget.store ?? SecureHealthProfileStore();
  late final TextEditingController _years = TextEditingController(
      text: widget.initialProfile?.answer('years_since_diagnosis'));
  late final TextEditingController _systolic =
      TextEditingController(text: widget.initialProfile?.answer('systolic_bp'));
  late final TextEditingController _diastolic = TextEditingController(
      text: widget.initialProfile?.answer('diastolic_bp'));

  // No health answers are preselected or fabricated.
  String? _stapleFood;
  String? _mealsPerDay;
  String? _eatOut;
  String? _sugarInTea;

  // Step 2 answers
  String? _diabetesType;
  String? _usesCgm;
  String? _medication;

  // Step 3 answers
  String? _activityLevel;
  String? _cholesterol;
  String? _smokes;

  // Step 4 answers
  String? _footUlcers;
  String? _footNumbness;
  String? _checkFeet;
  String? _footwear;

  @override
  void initState() {
    super.initState();
    final answers = widget.initialProfile?.answers ?? const <String, String>{};
    _stapleFood = answers['staple_food'];
    _mealsPerDay = answers['meals_per_day'];
    _eatOut = answers['eat_out'];
    _sugarInTea = answers['sugar_in_tea'];
    _diabetesType = answers['diabetes_type'];
    _usesCgm = answers['uses_glucose_meter'];
    _medication = answers['medication'];
    _activityLevel = answers['activity_level'];
    _cholesterol = answers['cholesterol'];
    _smokes = answers['smokes'];
    _footUlcers = answers['foot_ulcers'];
    _footNumbness = answers['foot_numbness'];
    _checkFeet = answers['checks_feet'];
    _footwear = answers['footwear'];
  }

  @override
  void dispose() {
    _years.dispose();
    _systolic.dispose();
    _diastolic.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: Column(children: [
            _buildHeader(),
            Expanded(
              child: SingleChildScrollView(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                child: _buildStep(),
              ),
            ),
            Container(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 14),
              decoration: const BoxDecoration(
                color: AppColors.card,
                border: Border(top: BorderSide(color: AppColors.border)),
              ),
              child: SafeArea(
                top: false,
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  if (_saveError != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(_saveError!,
                          style: const TextStyle(color: AppColors.danger)),
                    ),
                  FilledButton(
                    style: primaryButtonStyle(),
                    onPressed: _saving ? null : _next,
                    child: Text(_saving
                        ? 'Saving…'
                        : _step < 3
                            ? 'Continue'
                            : widget.onCompleted == null
                                ? 'Complete Setup'
                                : 'Save profile'),
                  ),
                ]),
              ),
            ),
          ]),
        ),
      );

  Widget _buildHeader() => Padding(
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 10),
        child: Column(children: [
          Row(children: [
            if (_step > 0)
              IconButton(
                onPressed: () => setState(() => _step--),
                icon: const Icon(Icons.arrow_back_rounded),
              )
            else
              const SizedBox(width: 48),
            Text('Health Profile Setup',
                style: GoogleFonts.manrope(
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                    color: AppColors.text)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.primaryLight,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text('${_step + 1} / 4',
                  style: GoogleFonts.manrope(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: AppColors.primaryDark)),
            ),
          ]),
          const SizedBox(height: 12),
          Row(
            children: [
              for (var i = 0; i < 4; i++) ...[
                Expanded(
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    height: 4,
                    decoration: BoxDecoration(
                      color: i <= _step ? AppColors.primary : AppColors.border,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
                if (i < 3) const SizedBox(width: 6),
              ],
            ],
          ),
        ]),
      );

  Widget _buildStep() => switch (_step) {
        0 => _buildStep1(),
        1 => _buildStep2(),
        2 => _buildStep3(),
        _ => _buildStep4(),
      };

  Widget _buildStep1() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _StepHeader(
            label: 'Step 1 of 4 · Module 1',
            title: 'Diet & Meal Habits',
            subtitle: 'Keep your usual meal habits with your profile.',
          ),
          _QField(
            label: "What's your typical staple food?",
            child: ChipRow(
              options: const [
                'White Rice',
                'Red Rice',
                'Roti / Bread',
                'String Hoppers'
              ],
              selected: _stapleFood,
              onChanged: (v) => setState(() => _stapleFood = v),
            ),
          ),
          _QField(
            label: 'How many meals do you eat per day?',
            child: ChipRow(
              options: const ['2', '3', '4+'],
              selected: _mealsPerDay,
              onChanged: (v) => setState(() => _mealsPerDay = v),
            ),
          ),
          _QField(
            label: 'How often do you eat out or order food?',
            child: ChipRow(
              options: const ['Rarely', 'Sometimes', 'Often'],
              selected: _eatOut,
              onChanged: (v) => setState(() => _eatOut = v),
            ),
          ),
          _QField(
            label: 'Do you add sugar to tea/coffee?',
            child: ChipRow(
              options: const ['Yes', 'No'],
              selected: _sugarInTea,
              onChanged: (v) => setState(() => _sugarInTea = v),
            ),
          ),
        ],
      );

  Widget _buildStep2() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _StepHeader(
            label: 'Step 2 of 4 · Module 2',
            title: 'Glucose & Medication',
            subtitle: 'Record the information you want to keep on this device.',
          ),
          _QField(
            label: 'Diabetes type',
            child: ChipRow(
              options: const ['Type 1', 'Type 2', 'Prediabetes', 'Gestational'],
              selected: _diabetesType,
              onChanged: (v) => setState(() => _diabetesType = v),
            ),
          ),
          _QField(
            label: 'Years since diagnosis',
            child: TextFormField(
              controller: _years,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(hintText: 'e.g. 4'),
            ),
          ),
          _QField(
            label: 'Do you use a glucometer or CGM?',
            child: ChipRow(
              options: const ['Yes', 'No'],
              selected: _usesCgm,
              onChanged: (v) => setState(() => _usesCgm = v),
            ),
          ),
          _QField(
            label: 'Current medication',
            child: ChipRow(
              options: const ['Metformin', 'Insulin', 'Other', 'None'],
              selected: _medication,
              onChanged: (v) => setState(() => _medication = v),
            ),
          ),
        ],
      );

  Widget _buildStep3() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _StepHeader(
            label: 'Step 3 of 4 · Module 3',
            title: 'Lifestyle & Risk Factors',
            subtitle: 'These answers are saved with your device profile.',
          ),
          _QField(
            label: 'Blood pressure (mmHg)',
            child: Row(children: [
              Expanded(
                child: TextFormField(
                  controller: _systolic,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(hintText: 'Systolic'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextFormField(
                  controller: _diastolic,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(hintText: 'Diastolic'),
                ),
              ),
            ]),
          ),
          _QField(
            label: 'Physical activity level',
            child: ChipRow(
              options: const ['Low', 'Moderate', 'High'],
              selected: _activityLevel,
              onChanged: (v) => setState(() => _activityLevel = v),
            ),
          ),
          _QField(
            label: 'Cholesterol level',
            child: ChipRow(
              options: const ['Normal', 'Borderline High', 'High'],
              selected: _cholesterol,
              onChanged: (v) => setState(() => _cholesterol = v),
            ),
          ),
          _QField(
            label: 'Do you currently smoke?',
            child: ChipRow(
              options: const ['Yes', 'No'],
              selected: _smokes,
              onChanged: (v) => setState(() => _smokes = v),
            ),
          ),
        ],
      );

  Widget _buildStep4() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _StepHeader(
            label: 'Step 4 of 4 · Module 4',
            title: 'Foot Health History',
            subtitle: 'Keep a note of your foot health history.',
          ),
          _QField(
            label: 'Any history of foot ulcers?',
            child: ChipRow(
              options: const ['Yes', 'No'],
              selected: _footUlcers,
              onChanged: (v) => setState(() => _footUlcers = v),
            ),
          ),
          _QField(
            label: 'Numbness or tingling in your feet?',
            child: ChipRow(
              options: const ['Yes, sometimes', 'No, never'],
              selected: _footNumbness,
              onChanged: (v) => setState(() => _footNumbness = v),
            ),
          ),
          _QField(
            label: 'Do you check your feet regularly?',
            child: ChipRow(
              options: const ['Yes', 'Not really'],
              selected: _checkFeet,
              onChanged: (v) => setState(() => _checkFeet = v),
            ),
          ),
          _QField(
            label: 'What footwear do you wear most often?',
            child: ChipRow(
              options: const ['Closed Shoes', 'Sandals', 'Barefoot Often'],
              selected: _footwear,
              onChanged: (v) => setState(() => _footwear = v),
            ),
          ),
        ],
      );

  Future<void> _next() async {
    if (_step < 3) {
      setState(() => _step++);
    } else {
      final years = _years.text.trim();
      final systolic = _systolic.text.trim();
      final diastolic = _diastolic.text.trim();
      if ((years.isNotEmpty &&
              (int.tryParse(years) == null ||
                  int.parse(years) < 0 ||
                  int.parse(years) > 120)) ||
          (systolic.isNotEmpty &&
              (int.tryParse(systolic) == null ||
                  int.parse(systolic) < 1 ||
                  int.parse(systolic) > 300)) ||
          (diastolic.isNotEmpty &&
              (int.tryParse(diastolic) == null ||
                  int.parse(diastolic) < 1 ||
                  int.parse(diastolic) > 200))) {
        setState(() => _saveError = 'Check the number fields and try again.');
        return;
      }
      final values = <String, String>{};
      void add(String key, String? value) {
        if (value != null && value.trim().isNotEmpty) {
          values[key] = value.trim();
        }
      }

      add('staple_food', _stapleFood);
      add('meals_per_day', _mealsPerDay);
      add('eat_out', _eatOut);
      add('sugar_in_tea', _sugarInTea);
      add('diabetes_type', _diabetesType);
      add('years_since_diagnosis', years);
      add('uses_glucose_meter', _usesCgm);
      add('medication', _medication);
      add('systolic_bp', systolic);
      add('diastolic_bp', diastolic);
      add('activity_level', _activityLevel);
      add('cholesterol', _cholesterol);
      add('smokes', _smokes);
      add('foot_ulcers', _footUlcers);
      add('foot_numbness', _footNumbness);
      add('checks_feet', _checkFeet);
      add('footwear', _footwear);
      setState(() {
        _saving = true;
        _saveError = null;
      });
      try {
        await _store.save(widget.userId, HealthProfile(values));
        if (!mounted) return;
        if (widget.onCompleted != null) {
          widget.onCompleted!();
        } else {
          Navigator.of(context).pushNamedAndRemoveUntil('/home', (_) => false);
        }
      } catch (_) {
        if (mounted) {
          setState(() {
            _saving = false;
            _saveError =
                'Could not save your profile on this device. Try again.';
          });
        }
      }
    }
  }
}

class _StepHeader extends StatelessWidget {
  const _StepHeader(
      {required this.label, required this.title, required this.subtitle});
  final String label;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        margin: const EdgeInsets.only(bottom: 20),
        decoration: BoxDecoration(
          color: AppColors.primaryDark,
          borderRadius: BorderRadius.circular(22),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label.toUpperCase(),
                style: GoogleFonts.manrope(
                    fontSize: 9.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.1,
                    color: AppColors.accent)),
            const SizedBox(height: 12),
            Text(title,
                style: GoogleFonts.manrope(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -.4,
                    color: Colors.white)),
            const SizedBox(height: 5),
            Text(subtitle,
                style: GoogleFonts.manrope(
                    fontSize: 12, color: Colors.white70, height: 1.45)),
          ],
        ),
      );
}

class _QField extends StatelessWidget {
  const _QField({required this.label, required this.child});
  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label,
              style: GoogleFonts.manrope(
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  color: AppColors.text)),
          const SizedBox(height: 9),
          child,
        ]),
      );
}
