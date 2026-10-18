import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/theme.dart';
import '../../../core/widgets.dart';
import '../../meal_history/data/meal_history_api.dart';
import '../../meal_history/data/meal_history_models.dart';
import '../data/meal_analysis.dart';
import 'meal_result_view.dart' show formatAmount, formatNutrient, sourceLabel;

/// Patient-facing C1 review flow.
class MealModuleFlow extends StatefulWidget {
  const MealModuleFlow({
    super.key,
    required this.analysis,
    required this.capturedAt,
    required this.onScanAgain,
    this.historyApi,
    this.image,
  });

  final MealAnalysis analysis;
  final DateTime capturedAt;
  final VoidCallback onScanAgain;
  final MealHistoryApi? historyApi;
  final Uint8List? image;

  @override
  State<MealModuleFlow> createState() => _MealModuleFlowState();
}

enum _ReviewStep {
  recognition,
  foods,
  editFood,
  portions,
  nutrition,
  details,
  glycemic,
  summary,
  recommendation
}

class _MealModuleFlowState extends State<MealModuleFlow> {
  late List<FoodItem> _foods = List.of(widget.analysis.items);
  late List<bool> _included = List<bool>.filled(_foods.length, true);
  _ReviewStep _step = _ReviewStep.recognition;
  int? _editingIndex;
  late final MealHistoryApi _historyApi =
      widget.historyApi ?? MealHistoryApi();
  bool _saving = false;
  bool _saved = false;
  String? _saveError;

  List<FoodItem> get _includedFoods => [
        for (var i = 0; i < _foods.length; i++)
          if (_included[i]) _foods[i],
      ];

  NutrientProfile get _totals => NutrientProfile.sum([
        for (final food in _includedFoods) food.nutrition,
      ]);

  /// Included foods missing any of the headline nutrients; they make the meal total unknown.
  List<String> get _foodsWithoutData => [
        for (final food in _includedFoods)
          if (food.nutrition.energyKcal == null ||
              food.nutrition.carbohydrateG == null ||
              food.nutrition.proteinG == null ||
              food.nutrition.fatG == null)
            foodDisplayName(food.label),
      ];

  bool get _hasMockNutrition =>
      _foods.any((food) => food.nutritionSource == 'MOCK');

  Widget _notices() => Column(children: [
        if (widget.analysis.isMock) _DemoNotice(mockNutrition: _hasMockNutrition),
        if (_foodsWithoutData.isNotEmpty)
          _MissingDataNotice(foods: _foodsWithoutData),
      ]);

  static const _mainSteps = <_ReviewStep>[
    _ReviewStep.recognition,
    _ReviewStep.foods,
    _ReviewStep.portions,
    _ReviewStep.nutrition,
    _ReviewStep.details,
    _ReviewStep.glycemic,
    _ReviewStep.summary,
    _ReviewStep.recommendation,
  ];

  String get _title => switch (_step) {
        _ReviewStep.recognition => 'Detected Foods',
        _ReviewStep.foods => 'Confirm Detected Foods',
        _ReviewStep.editFood => 'Edit Food',
        _ReviewStep.portions => 'Confirm Portions',
        _ReviewStep.nutrition => 'Nutrition Analysis',
        _ReviewStep.details => 'Nutrition Details',
        _ReviewStep.glycemic => 'Glycemic Profile',
        _ReviewStep.summary => 'Meal Analysis Complete',
        _ReviewStep.recommendation => 'Portion Recommendation',
      };

  void _next() {
    final index = _mainSteps.indexOf(_step);
    if (index >= 0 && index < _mainSteps.length - 1) {
      setState(() => _step = _mainSteps[index + 1]);
    }
  }

  void _back() {
    if (_step == _ReviewStep.editFood) {
      setState(() => _step = _ReviewStep.foods);
      return;
    }
    final index = _mainSteps.indexOf(_step);
    if (index > 0) setState(() => _step = _mainSteps[index - 1]);
  }

  void _addFood() {
    final controller = TextEditingController();
    showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add a food'),
        content: TextField(
          controller: controller,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(labelText: 'Food name'),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Add food'),
          ),
        ],
      ),
    ).then((label) {
      controller.dispose();
      if (!mounted || label == null || label.isEmpty) return;
      setState(() {
        _foods = [
          ..._foods,
          FoodItem(
            itemId: 'user-${DateTime.now().microsecondsSinceEpoch}',
            label: label,
            portion: const Portion(
                grams: 100, estimationMethod: Portion.userEdited),
            nutrition: const NutrientProfile(),
          ),
        ];
        _included = [..._included, true];
      });
    });
  }

  void _saveFood(FoodItem food) {
    final index = _editingIndex;
    if (index == null) return;
    setState(() {
      _foods = List.of(_foods)..[index] = food;
      _editingIndex = null;
      _step = _ReviewStep.foods;
    });
  }

  Future<void> _saveMeal() async {
    if (_saving || _includedFoods.isEmpty) return;
    setState(() {
      _saving = true;
      _saveError = null;
    });
    try {
      await _historyApi.logMeal(MealCreate(
        eatenAt: widget.capturedAt,
        mealType: widget.analysis.mealType,
        note: widget.analysis.isMock ? 'Demo meal analysis' : null,
        items: [
          for (final food in _includedFoods)
            MealItemIn.free(
              name: food.label,
              grams: food.portion.grams,
              nutrients: food.nutrition,
            ),
        ],
      ));
      if (mounted) setState(() => _saved = true);
    } on MealHistoryException catch (e) {
      if (mounted) setState(() => _saveError = e.userMessage);
    } catch (_) {
      if (mounted) {
        setState(() => _saveError =
            'Could not save the meal. Check the connection and try again.');
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _savePortion(int index, double grams) {
    final food = _foods[index];
    final updated = food.canEditPortion
        ? food.withGrams(grams)
        : FoodItem(
            itemId: food.itemId,
            label: food.label,
            portion:
                Portion(grams: grams, estimationMethod: Portion.userEdited),
            nutrition: food.nutrition,
            nutritionSource: food.nutritionSource,
          );
    setState(() => _foods = List.of(_foods)..[index] = updated);
  }

  @override
  Widget build(BuildContext context) {
    if (_step == _ReviewStep.editFood && _editingIndex != null) {
      return _EditFoodPage(
        food: _foods[_editingIndex!],
        onCancel: _back,
        onSave: _saveFood,
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(children: [
          _buildTopBar(),
          if (_step != _ReviewStep.recognition)
            _StepProgress(
                value: (_mainSteps.indexOf(_step)) /
                    (_mainSteps.length - 1)),
          Expanded(child: _buildStep()),
        ]),
      ),
    );
  }

  Widget _buildTopBar() => Padding(
        padding: const EdgeInsets.fromLTRB(22, 8, 22, 4),
        child: Row(children: [
          if (_step != _ReviewStep.recognition)
            InkWell(
              onTap: _back,
              borderRadius: BorderRadius.circular(11),
              child: Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppColors.card,
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(color: AppColors.border),
                ),
                child: const Icon(Icons.arrow_back,
                    size: 17, color: AppColors.text),
              ),
            )
          else
            const SizedBox(width: 36),
          const SizedBox(width: 12),
          Expanded(
            child: Text(_title,
                style: GoogleFonts.inter(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    color: AppColors.text)),
          ),
        ]),
      );

  Widget _buildStep() => switch (_step) {
        _ReviewStep.recognition => _buildRecognition(),
        _ReviewStep.foods => _buildFoods(),
        _ReviewStep.portions => _buildPortions(),
        _ReviewStep.nutrition => _buildNutrition(),
        _ReviewStep.details => _buildDetails(),
        _ReviewStep.glycemic => _buildGlycemic(),
        _ReviewStep.summary => _buildSummary(),
        _ReviewStep.recommendation => _buildRecommendation(),
        _ReviewStep.editFood => const SizedBox.shrink(),
      };

  // ── Step: Recognition ────────────────────────────────────────────────────

  Widget _buildRecognition() => Column(children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 16),
            children: [
              _MealPhoto(image: widget.image, icon: Icons.camera_alt_outlined),
              Row(children: [
                AiTag(_foods.isEmpty
                    ? 'No foods recognised'
                    : 'AI matched ${_foods.length} Sri Lankan '
                        '${_foods.length == 1 ? 'dish' : 'dishes'}'),
              ]),
              const SizedBox(height: 14),
              _notices(),
              for (final food in _foods) ...[
                _RecognitionRow(label: food.label),
                const SizedBox(height: 4),
              ],
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(22, 0, 22, 12),
          child: FilledButton(
            style: primaryButtonStyle(),
            onPressed: _next,
            child: const Text('Confirm Detected Foods'),
          ),
        ),
      ]);

  // ── Step: Confirm Foods ───────────────────────────────────────────────────

  Widget _buildFoods() => Column(children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 16),
            children: [
              Row(children: [
                AiTag('Multi-label recognition · ${_foods.length} '
                    '${_foods.length == 1 ? 'dish' : 'dishes'} matched'),
              ]),
              const SizedBox(height: 12),
              _notices(),
              for (var i = 0; i < _foods.length; i++) ...[
                _FoodCard(
                  food: _foods[i],
                  selected: _included[i],
                  onSelected: (v) => setState(() => _included[i] = v),
                  onEdit: () => setState(() {
                    _editingIndex = i;
                    _step = _ReviewStep.editFood;
                  }),
                  onRemove: () => setState(() {
                    _foods = List.of(_foods)..removeAt(i);
                    _included = List.of(_included)..removeAt(i);
                  }),
                ),
                const SizedBox(height: 8),
              ],
              InkWell(
                onTap: _addFood,
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  decoration: appCardDecoration(),
                  child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                    const Icon(Icons.add,
                        size: 16, color: AppColors.primary),
                    const SizedBox(width: 8),
                    Text('Add Food',
                        style: GoogleFonts.inter(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w700,
                            color: AppColors.primary)),
                  ]),
                ),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(22, 0, 22, 12),
          child: FilledButton(
            style: primaryButtonStyle(),
            onPressed: _includedFoods.isEmpty ? null : _next,
            child: const Text('Confirm Foods'),
          ),
        ),
      ]);

  // ── Step: Portions ────────────────────────────────────────────────────────

  Widget _buildPortions() => Column(children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 16),
            children: [
              Text(
                'Review the AI-estimated portion for each detected food, or adjust it.',
                style: GoogleFonts.inter(
                    fontSize: 12, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 14),
              for (final food in _includedFoods) ...[
                _PortionCard(
                  food: food,
                  onPortionChanged: (grams) =>
                      _savePortion(_foods.indexOf(food), grams),
                ),
                const SizedBox(height: 10),
              ],
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(22, 0, 22, 12),
          child: FilledButton(
            style: primaryButtonStyle(),
            onPressed: _includedFoods.isEmpty ? null : _next,
            child: const Text('Continue to Nutrition'),
          ),
        ),
      ]);

  // ── Step: Nutrition ────────────────────────────────────────────────────────

  Widget _buildNutrition() {
    final totals = _totals;
    final maxMacro = [
      totals.carbohydrateG ?? 0,
      totals.proteinG ?? 0,
      totals.fatG ?? 0,
    ].reduce((a, b) => a > b ? a : b);
    double fraction(double? v) =>
        v == null || maxMacro <= 0 ? 0 : v / maxMacro;
    final kcal = totals.energyKcal;

    return Column(children: [
      Expanded(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(22, 8, 22, 16),
          children: [
            _notices(),
            // Calorie hero
            Container(
              padding: const EdgeInsets.all(16),
              margin: const EdgeInsets.only(bottom: 14),
              decoration: appCardDecoration(),
              child: Column(children: [
                Text('ESTIMATED CALORIES',
                    style: GoogleFonts.inter(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w700,
                        letterSpacing: .05,
                        color: AppColors.textSecondary)),
                const SizedBox(height: 8),
                RichText(
                  text: TextSpan(children: [
                    TextSpan(
                        text: kcal == null ? 'Not available' : '${formatAmount(kcal)} ',
                        style: GoogleFonts.inter(
                            fontSize: kcal == null ? 22 : 34,
                            fontWeight: FontWeight.w800,
                            color: AppColors.text)),
                    TextSpan(
                        text: kcal == null ? '' : 'kcal',
                        style: GoogleFonts.inter(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textSecondary)),
                  ]),
                ),
              ]),
            ),
            NutritionBarRow(
              label: 'Carbohydrates',
              value: _roundedTotal(totals.carbohydrateG, 'g'),
              fraction: fraction(totals.carbohydrateG),
              color: AppColors.primary,
            ),
            NutritionBarRow(
              label: 'Protein',
              value: _roundedTotal(totals.proteinG, 'g'),
              fraction: fraction(totals.proteinG),
              color: AppColors.success,
            ),
            NutritionBarRow(
              label: 'Fat',
              value: _roundedTotal(totals.fatG, 'g'),
              fraction: fraction(totals.fatG),
              color: AppColors.warning,
            ),
          ],
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(22, 0, 22, 12),
        child: FilledButton(
          style: primaryButtonStyle(),
          onPressed: _next,
          child: const Text('View Nutrition Details'),
        ),
      ),
    ]);
  }

  // ── Step: Details ──────────────────────────────────────────────────────────

  Widget _buildDetails() => Column(children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 16),
            children: [
              _notices(),
              for (final food in _includedFoods) ...[
                _FoodNutritionCard(food: food),
                const SizedBox(height: 10),
              ],
              const SectionLabel('Meal Total'),
              Container(
                padding: const EdgeInsets.all(16),
                margin: const EdgeInsets.only(bottom: 14),
                decoration: appCardDecoration(),
                child: Column(children: [
                  _NutrientGridRow(
                    items: [
                      ('Calories', _roundedTotal(_totals.energyKcal, 'kcal')),
                      ('Carbohydrates', _roundedTotal(_totals.carbohydrateG, 'g')),
                      ('Protein', _roundedTotal(_totals.proteinG, 'g')),
                      ('Fat', _roundedTotal(_totals.fatG, 'g')),
                    ],
                  ),
                  if (_totals.dietaryFiberG != null) ...[
                    const Divider(height: 1, color: AppColors.border),
                    Padding(
                      padding: const EdgeInsets.only(top: 11),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Fibre',
                              style: GoogleFonts.inter(
                                  fontSize: 11.5,
                                  color: AppColors.textSecondary)),
                          Text(
                              formatNutrient(_totals.dietaryFiberG, "g"),
                              style: GoogleFonts.inter(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.text)),
                        ],
                      ),
                    ),
                  ],
                ]),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(22, 0, 22, 12),
          child: FilledButton(
            style: primaryButtonStyle(),
            onPressed: _next,
            child: const Text('Continue to Glycemic Profile'),
          ),
        ),
      ]);

  // ── Step: Glycemic ─────────────────────────────────────────────────────────

  Widget _buildGlycemic() => Column(children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 16),
            children: [
              Text('Estimated glycemic impact of this meal',
                  style: GoogleFonts.inter(
                      fontSize: 12, color: AppColors.textSecondary)),
              const SizedBox(height: 14),
              // 2x2 grid of GI metrics
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisSpacing: 11,
                mainAxisSpacing: 11,
                childAspectRatio: 1.5,
                children: [
                  const _GlycemicMetricCard(
                      label: 'Glycemic Index', value: 'Not available'),
                  const _GlycemicMetricCard(
                      label: 'Glycemic Load', value: 'Not available'),
                  _GlycemicMetricCard(
                      label: 'Carbohydrates',
                      value: _roundedTotal(_totals.carbohydrateG, 'g')),
                  _GlycemicMetricCard(
                      label: 'Fibre',
                      value: formatNutrient(_totals.dietaryFiberG, 'g')),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                'Glycemic index and load are not estimated yet.',
                style: GoogleFonts.inter(
                    fontSize: 12, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 14),
              _ExpandableCard(
                title: 'How is this calculated?',
                body:
                    'Glycemic Index reflects the relative effect of carbohydrate-containing foods on blood glucose. Glycemic Load considers both GI and the amount of carbohydrate in the portion eaten.',
              ),
              Text(
                'This is an estimate for monitoring purposes and not medical treatment advice.',
                style: GoogleFonts.inter(
                    fontSize: 10.5, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 14),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(22, 0, 22, 12),
          child: FilledButton(
            style: primaryButtonStyle(),
            onPressed: _next,
            child: const Text('Continue to Meal Summary'),
          ),
        ),
      ]);

  // ── Step: Summary ──────────────────────────────────────────────────────────

  Widget _buildSummary() => Column(children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 16),
            children: [
              _MealPhoto(image: widget.image, icon: Icons.check_circle_outline),
              Center(
                child: Column(children: [
                  Text(
                      widget.analysis.mealType?.label ?? 'Meal',
                      style: GoogleFonts.inter(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: AppColors.text)),
                  Text('${_includedFoods.length} foods detected',
                      style: GoogleFonts.inter(
                          fontSize: 12, color: AppColors.textSecondary)),
                ]),
              ),
              const SizedBox(height: 14),
              // 2x2 nutrition grid
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisSpacing: 11,
                mainAxisSpacing: 11,
                childAspectRatio: 1.6,
                children: [
                  _SummaryMetricCard(
                      label: 'Calories',
                      value: _roundedTotal(_totals.energyKcal, 'kcal')),
                  _SummaryMetricCard(
                      label: 'Carbs',
                      value: _roundedTotal(_totals.carbohydrateG, 'g')),
                  _SummaryMetricCard(
                      label: 'Protein',
                      value: _roundedTotal(_totals.proteinG, 'g')),
                  _SummaryMetricCard(
                      label: 'Fat',
                      value: _roundedTotal(_totals.fatG, 'g')),
                ],
              ),
              const SizedBox(height: 11),
              _notices(),
              const AppBadge('Research prototype: estimates only',
                  variant: AppBadgeVariant.neutral),
              const SizedBox(height: 14),
              if (_saved) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.successBg,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text('Meal saved to your history.',
                      style: GoogleFonts.inter(
                          fontSize: 12, color: AppColors.success)),
                ),
                const SizedBox(height: 10),
              ],
              if (_saveError != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.warningBg,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(_saveError!,
                      style: GoogleFonts.inter(
                          fontSize: 12, color: AppColors.warning)),
                ),
                const SizedBox(height: 10),
              ],
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(22, 0, 22, 12),
          child: Column(children: [
            FilledButton(
              style: primaryButtonStyle(),
              onPressed: _next,
              child: const Text('View Portion Recommendation'),
            ),
            const SizedBox(height: 10),
            OutlinedButton(
              style: secondaryButtonStyle(),
              onPressed: (_saving || _saved) ? null : _saveMeal,
              child: Text(_saving
                  ? 'Saving…'
                  : _saved
                      ? 'Meal Saved ✓'
                      : 'Save Meal'),
            ),
          ]),
        ),
      ]);

  // ── Step: Recommendation ──────────────────────────────────────────────────

  Widget _buildRecommendation() => Column(children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 16),
            children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.primaryLight,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFFCFEDEF)),
                ),
                child: Text(
                  'Portion recommendations are not available yet.',
                  style: GoogleFonts.inter(
                      fontSize: 12.5, height: 1.45, color: AppColors.text),
                ),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(22, 0, 22, 12),
          child: Column(children: [
            FilledButton(
              style: primaryButtonStyle(),
              onPressed: widget.onScanAgain,
              child: const Text('Scan Another Meal'),
            ),
            const SizedBox(height: 10),
            OutlinedButton(
              style: secondaryButtonStyle(),
              onPressed: _back,
              child: const Text('Edit Portion'),
            ),
          ]),
        ),
      ]);
}

// ─── Recognition Row ─────────────────────────────────────────────────────────

class _RecognitionRow extends StatelessWidget {
  const _RecognitionRow({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: appCardDecoration(),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Expanded(
            child: Text(foodDisplayName(label),
                style: GoogleFonts.inter(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w600,
                    color: AppColors.text)),
          ),
          const AppBadge('Detected', variant: AppBadgeVariant.success),
        ]),
      );
}

// ─── Food Card ────────────────────────────────────────────────────────────────

class _FoodCard extends StatelessWidget {
  const _FoodCard({
    required this.food,
    required this.selected,
    required this.onSelected,
    required this.onEdit,
    required this.onRemove,
  });

  final FoodItem food;
  final bool selected;
  final ValueChanged<bool> onSelected;
  final VoidCallback onEdit;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) => Container(
        padding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: appCardDecoration(),
        child: Row(children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
                color: AppColors.primaryLight,
                borderRadius: BorderRadius.circular(11)),
            child: const Icon(Icons.water_drop_outlined,
                size: 19, color: AppColors.primary),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
              Text(foodDisplayName(food.label),
                  style: GoogleFonts.inter(
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                      color: AppColors.text)),
              Text('AI Detected',
                  style: GoogleFonts.inter(
                      fontSize: 11,
                      color: AppColors.textSecondary)),
            ]),
          ),
          const AppBadge('Detected',
              variant: AppBadgeVariant.success),
          const SizedBox(width: 4),
          _SmallIconBtn(icon: Icons.edit_outlined, onTap: onEdit),
          _SmallIconBtn(
              icon: Icons.close,
              onTap: onRemove,
              color: AppColors.danger),
        ]),
      );
}

class _SmallIconBtn extends StatelessWidget {
  const _SmallIconBtn(
      {required this.icon, required this.onTap, this.color});
  final IconData icon;
  final VoidCallback onTap;
  final Color? color;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.border),
          ),
          child: Icon(icon,
              size: 14, color: color ?? AppColors.textSecondary),
        ),
      );
}

// ─── Portion Card ─────────────────────────────────────────────────────────────

class _PortionCard extends StatefulWidget {
  const _PortionCard({required this.food, required this.onPortionChanged});
  final FoodItem food;
  final ValueChanged<double> onPortionChanged;

  @override
  State<_PortionCard> createState() => _PortionCardState();
}

class _PortionCardState extends State<_PortionCard> {
  late int _selectedIdx = 1; // middle = AI estimate

  List<(String, double)> get _options {
    final base = widget.food.portion.grams > 0
        ? widget.food.portion.grams
        : 100.0;
    return [
      ('Smaller (${(base * 0.5).round()} g)', base * 0.5),
      (widget.food.portion.householdMeasure != null
          ? '${widget.food.portion.householdMeasure} (${base.round()} g)'
          : 'As analysed (${base.round()} g)', base),
      ('Larger (${(base * 1.5).round()} g)', base * 1.5),
    ];
  }

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: appCardDecoration(),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(foodDisplayName(widget.food.label),
                style: GoogleFonts.inter(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w700,
                    color: AppColors.text)),
            AppBadge(
              _options[_selectedIdx].$1.split(' ').first,
              variant: AppBadgeVariant.neutral,
            ),
          ]),
          const SizedBox(height: 9),
          ChipRow(
            options: _options.map((o) => o.$1).toList(),
            selected: _options[_selectedIdx].$1,
            onChanged: (label) {
              final idx =
                  _options.indexWhere((o) => o.$1 == label);
              if (idx < 0) return;
              setState(() => _selectedIdx = idx);
              widget.onPortionChanged(_options[idx].$2);
            },
          ),
        ]),
      );
}

// ─── Food Nutrition Card ──────────────────────────────────────────────────────

class _FoodNutritionCard extends StatelessWidget {
  const _FoodNutritionCard({required this.food});
  final FoodItem food;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: appCardDecoration(),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
                child: Text(foodDisplayName(food.label),
                    style: GoogleFonts.inter(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w700,
                        color: AppColors.text))),
            Text(
                food.portion.grams > 0
                    ? '${formatAmount(food.portion.grams)} g'
                    : 'Not available',
                style: GoogleFonts.inter(
                    fontSize: 11.5, color: AppColors.textSecondary)),
          ]),
          const SizedBox(height: 10),
          _NutrientGridRow(
            items: [
              ('Calories',
                  formatNutrient(food.nutrition.energyKcal, "kcal")),
              ('Carbs',
                  formatNutrient(food.nutrition.carbohydrateG, "g")),
              ('Protein',
                  formatNutrient(food.nutrition.proteinG, "g")),
              ('Fat', formatNutrient(food.nutrition.fatG, "g")),
            ],
          ),
          const SizedBox(height: 6),
          Text('Source: ${sourceLabel(food.nutritionSource)}',
              style: GoogleFonts.inter(
                  fontSize: 11, color: AppColors.textSecondary)),
        ]),
      );
}

class _NutrientGridRow extends StatelessWidget {
  const _NutrientGridRow({required this.items});
  final List<(String, String)> items;

  @override
  Widget build(BuildContext context) => GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
        childAspectRatio: 2.8,
        children: [
          for (final (label, value) in items)
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(label,
                  style: GoogleFonts.inter(
                      fontSize: 11.5, color: AppColors.textSecondary)),
              Text(value,
                  style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppColors.text)),
            ]),
        ],
      );
}

// ─── Glycemic Metric Card ─────────────────────────────────────────────────────

class _GlycemicMetricCard extends StatelessWidget {
  const _GlycemicMetricCard({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(12),
        decoration: appCardDecoration(),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label.toUpperCase(),
              style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: .05,
                  color: AppColors.textSecondary)),
          const SizedBox(height: 4),
          Text(value,
              style: GoogleFonts.inter(
                  fontSize: 19,
                  fontWeight: FontWeight.w800,
                  color: AppColors.text)),
        ]),
      );
}

// ─── Summary Metric Card ──────────────────────────────────────────────────────

class _SummaryMetricCard extends StatelessWidget {
  const _SummaryMetricCard({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(12),
        decoration: appCardDecoration(),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label.toUpperCase(),
              style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: .05,
                  color: AppColors.textSecondary)),
          const SizedBox(height: 4),
          Text(value,
              style: GoogleFonts.inter(
                  fontSize: 19,
                  fontWeight: FontWeight.w800,
                  color: AppColors.text)),
        ]),
      );
}

// ─── Expandable Card ──────────────────────────────────────────────────────────

class _ExpandableCard extends StatefulWidget {
  const _ExpandableCard({required this.title, required this.body});
  final String title;
  final String body;

  @override
  State<_ExpandableCard> createState() => _ExpandableCardState();
}

class _ExpandableCardState extends State<_ExpandableCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: () => setState(() => _expanded = !_expanded),
        child: Container(
          padding: const EdgeInsets.all(14),
          margin: const EdgeInsets.only(bottom: 10),
          decoration: appCardDecoration(),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
              Text(widget.title,
                  style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: AppColors.text)),
              AnimatedRotation(
                turns: _expanded ? 0.25 : 0,
                duration: const Duration(milliseconds: 150),
                child: const Icon(Icons.chevron_right,
                    size: 16, color: AppColors.primary),
              ),
            ]),
            if (_expanded) ...[
              const SizedBox(height: 8),
              Text(widget.body,
                  style: GoogleFonts.inter(
                      fontSize: 12,
                      height: 1.5,
                      color: AppColors.textSecondary)),
            ],
          ]),
        ),
      );
}

// ─── Step Progress ────────────────────────────────────────────────────────────

class _StepProgress extends StatelessWidget {
  const _StepProgress({required this.value});
  final double value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 4),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
              value: value,
              minHeight: 5,
              color: AppColors.primary,
              backgroundColor: AppColors.border),
        ),
      );
}

// ─── Demo Notice ──────────────────────────────────────────────────────────────

class _DemoNotice extends StatelessWidget {
  const _DemoNotice({required this.mockNutrition});

  /// True when the nutrient values themselves are placeholders, not only the portions.
  final bool mockNutrition;

  @override
  Widget build(BuildContext context) => _Notice(
      mockNutrition
          ? 'Demo data: these foods and values are placeholders.'
          : 'Portions are not measured from the photo yet. Each food starts at '
              'a fixed amount; change it in the portion step if you know it.');
}

class _MissingDataNotice extends StatelessWidget {
  const _MissingDataNotice({required this.foods});
  final List<String> foods;

  @override
  Widget build(BuildContext context) => _Notice(
      'No nutrition data for ${foods.join(', ')}, so the meal totals are not '
      'available. Remove ${foods.length == 1 ? 'it' : 'them'} in "Confirm '
      'Foods" to see totals for the other foods.');
}

class _Notice extends StatelessWidget {
  const _Notice(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.warningBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.warning),
        ),
        child: Row(children: [
          const Icon(Icons.info_outline, color: AppColors.warning),
          const SizedBox(width: 8),
          Expanded(
              child: Text(text,
                  style: GoogleFonts.inter(
                      fontSize: 12, color: AppColors.text))),
        ]),
      );
}

class _MealPhoto extends StatelessWidget {
  const _MealPhoto({required this.image, required this.icon});
  final Uint8List? image;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
        height: 140,
        margin: const EdgeInsets.only(bottom: 14),
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          gradient: const LinearGradient(
              colors: [Color(0xFFF4C77B), Color(0xFFE7A64C)]),
          borderRadius: BorderRadius.circular(14),
        ),
        child: image != null
            ? Image.memory(image!, fit: BoxFit.cover, width: double.infinity)
            : Center(child: Icon(icon, size: 34, color: Colors.white)),
      );
}

/// A meal total for display; an unknown total is "Not available", never 0.
String _roundedTotal(double? value, String unit) => formatNutrient(value, unit);

/// "white_rice" -> "White rice". Labels typed by the patient are shown as typed.
String foodDisplayName(String label) {
  if (!label.contains('_')) return label;
  final words = label.replaceAll('_', ' ').trim();
  return words.isEmpty ? label : words[0].toUpperCase() + words.substring(1);
}

// ─── Edit Food Page ────────────────────────────────────────────────────────────

class _EditFoodPage extends StatefulWidget {
  const _EditFoodPage(
      {required this.food, required this.onCancel, required this.onSave});

  final FoodItem food;
  final VoidCallback onCancel;
  final ValueChanged<FoodItem> onSave;

  @override
  State<_EditFoodPage> createState() => _EditFoodPageState();
}

class _EditFoodPageState extends State<_EditFoodPage> {
  late final TextEditingController _label =
      TextEditingController(text: widget.food.label);
  late String? _category = 'Curries';

  static const _categories = [
    'Curries', 'Rice', 'Vegetables', 'Sambols',
    'Short Eats', 'Desserts', 'Beverages',
  ];

  static const _suggestions = [
    'Brinjal Moju', 'Fish Curry', 'Pol Sambol', 'Lunu Miris',
    'Parippu', 'Gotukola Sambol', 'Jackfruit Curry',
  ];

  @override
  void dispose() {
    _label.dispose();
    super.dispose();
  }

  void _save() {
    final label = _label.text.trim();
    if (label.isEmpty) return;
    widget.onSave(FoodItem(
      itemId: widget.food.itemId,
      label: label,
      portion: widget.food.portion,
      nutrition: widget.food.nutrition,
      nutritionSource: widget.food.nutritionSource,
    ));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(22, 8, 22, 8),
              child: Row(children: [
                InkWell(
                  onTap: widget.onCancel,
                  borderRadius: BorderRadius.circular(11),
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: AppColors.card,
                      borderRadius: BorderRadius.circular(11),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: const Icon(Icons.arrow_back,
                        size: 17, color: AppColors.text),
                  ),
                ),
                const SizedBox(width: 12),
                Text('Edit Food',
                    style: GoogleFonts.inter(
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        color: AppColors.text)),
              ]),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(22, 6, 22, 16),
                children: [
                  const SectionLabel('Detected'),
                  TextField(
                    controller: _label,
                    textCapitalization: TextCapitalization.words,
                    decoration:
                        const InputDecoration(hintText: 'Food name'),
                    style: GoogleFonts.inter(
                        fontSize: 13.5, color: AppColors.text),
                  ),
                  const SizedBox(height: 18),
                  const SectionLabel('Category'),
                  ChipRow(
                    options: _categories,
                    selected: _category,
                    onChanged: (v) => setState(() => _category = v),
                  ),
                  const SizedBox(height: 18),
                  const SectionLabel('Suggested Sri Lankan Foods'),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 2),
                    decoration: appCardDecoration(),
                    child: Column(children: [
                      for (final s in _suggestions)
                        InkWell(
                          onTap: () =>
                              setState(() => _label.text = s),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                vertical: 12, horizontal: 2),
                            decoration: BoxDecoration(
                              border: Border(
                                  bottom: BorderSide(
                                      color: AppColors.border,
                                      width: _suggestions.last == s
                                          ? 0
                                          : 1)),
                            ),
                            child: Row(children: [
                              Expanded(
                                child: Text(s,
                                    style: GoogleFonts.inter(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.text)),
                              ),
                            ]),
                          ),
                        ),
                    ]),
                  ),
                  const SizedBox(height: 18),
                  Row(children: [
                    Expanded(
                      child: OutlinedButton(
                        style: ghostButtonStyle(),
                        onPressed: widget.onCancel,
                        child: const Text('Cancel'),
                      ),
                    ),
                    const SizedBox(width: 11),
                    Expanded(
                      child: FilledButton(
                        style: primaryButtonStyle(),
                        onPressed: _save,
                        child: const Text('Save Changes'),
                      ),
                    ),
                  ]),
                ],
              ),
            ),
          ]),
        ),
      );
}
