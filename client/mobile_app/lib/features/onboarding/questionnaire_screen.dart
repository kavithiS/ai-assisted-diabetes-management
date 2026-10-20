import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';

class QuestionnaireScreen extends StatefulWidget {
  const QuestionnaireScreen({super.key});

  @override
  State<QuestionnaireScreen> createState() => _QuestionnaireScreenState();
}

class _QuestionnaireScreenState extends State<QuestionnaireScreen> {
  int _step = 0;

  // Step 1 answers
  String? _stapleFood = 'White Rice';
  String? _mealsPerDay = '3';
  String? _eatOut = 'Rarely';
  String? _sugarInTea = 'No';

  // Step 2 answers
  String? _diabetesType = 'Type 2';
  String? _usesCgm = 'Yes';
  String? _medication = 'Metformin';

  // Step 3 answers
  String? _activityLevel = 'Moderate';
  String? _cholesterol = 'Borderline High';
  String? _smokes = 'No';

  // Step 4 answers
  String? _footUlcers = 'No';
  String? _footNumbness = 'Yes, sometimes';
  String? _checkFeet = 'Not really';
  String? _footwear = 'Closed Shoes';

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: Column(children: [
            _buildHeader(),
            Expanded(
              child: SingleChildScrollView(
                padding:
                    const EdgeInsets.symmetric(horizontal: 22, vertical: 6),
                child: _buildStep(),
              ),
            ),
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 22, vertical: 12),
              child: FilledButton(
                style: primaryButtonStyle(),
                onPressed: _next,
                child: Text(_step < 3 ? 'Continue' : 'Complete Setup'),
              ),
            ),
          ]),
        ),
      );

  Widget _buildHeader() => Padding(
        padding:
            const EdgeInsets.fromLTRB(22, 12, 22, 8),
        child: Column(children: [
          Row(children: [
            if (_step > 0)
              InkWell(
                onTap: () => setState(() => _step--),
                borderRadius: BorderRadius.circular(11),
                child: Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppColors.card,
                    borderRadius: BorderRadius.circular(11),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: const Icon(Icons.arrow_back, size: 17,
                      color: AppColors.text),
                ),
              )
            else
              const SizedBox(width: 36),
            const SizedBox(width: 12),
            Text('Health Profile Setup',
                style: GoogleFonts.inter(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    color: AppColors.text)),
          ]),
          const SizedBox(height: 14),
          Row(
            children: [
              for (var i = 0; i < 4; i++) ...[
                Expanded(
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    height: 5,
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
            subtitle:
                'Helps our AI recognize your meals and estimate portions accurately.',
          ),
          _QField(
            label: "What's your typical staple food?",
            child: ChipRow(
              options: const [
                'White Rice', 'Red Rice', 'Roti / Bread', 'String Hoppers'
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
            subtitle: 'Used to personalize your glucose prediction model.',
          ),
          _QField(
            label: 'Diabetes type',
            child: ChipRow(
              options: const [
                'Type 1', 'Type 2', 'Prediabetes', 'Gestational'
              ],
              selected: _diabetesType,
              onChanged: (v) => setState(() => _diabetesType = v),
            ),
          ),
          _QField(
            label: 'Years since diagnosis',
            child: TextFormField(
              initialValue: '4',
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
            subtitle:
                'Feeds your multi-factor Diabetic Health Score and explainable AI.',
          ),
          _QField(
            label: 'Blood pressure (mmHg)',
            child: Row(children: [
              Expanded(
                child: TextFormField(
                  initialValue: '128',
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(hintText: 'Systolic'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextFormField(
                  initialValue: '82',
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
            subtitle: 'Helps calibrate your AI foot screening baseline.',
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

  void _next() {
    if (_step < 3) {
      setState(() => _step++);
    } else {
      Navigator.of(context)
          .pushNamedAndRemoveUntil('/home', (_) => false);
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
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(),
              style: GoogleFonts.inter(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w700,
                  letterSpacing: .05,
                  color: AppColors.primaryDark)),
          const SizedBox(height: 4),
          Text(title,
              style: GoogleFonts.inter(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: AppColors.text)),
          const SizedBox(height: 4),
          Text(subtitle,
              style: GoogleFonts.inter(
                  fontSize: 12.5, color: AppColors.textSecondary, height: 1.4)),
          const SizedBox(height: 18),
        ],
      );
}

class _QField extends StatelessWidget {
  const _QField({required this.label, required this.child});
  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label,
              style: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: AppColors.text)),
          const SizedBox(height: 9),
          child,
        ]),
      );
}
