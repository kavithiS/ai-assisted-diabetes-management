import 'package:flutter/material.dart';

import '../../meal_history/data/meal_history_api.dart';
import '../../meal_history/data/meal_history_models.dart';
import '../data/meal_analysis.dart';
import '../meal_scan_style.dart';
import 'meal_result_view.dart' show formatAmount, formatNutrient, sourceLabel;

/// Patient-facing C1 review flow. It uses only values returned or edited in this scan.
class MealModuleFlow extends StatefulWidget {
  const MealModuleFlow({
    super.key,
    required this.analysis,
    required this.capturedAt,
    required this.onScanAgain,
    this.historyApi,
  });

  final MealAnalysis analysis;
  final DateTime capturedAt;
  final VoidCallback onScanAgain;
  final MealHistoryApi? historyApi;

  @override
  State<MealModuleFlow> createState() => _MealModuleFlowState();
}

enum _ReviewStep {
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
  _ReviewStep _step = _ReviewStep.foods;
  int? _editingIndex;
  late final MealHistoryApi _historyApi = widget.historyApi ?? MealHistoryApi();
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

  static const _steps = <_ReviewStep>[
    _ReviewStep.foods,
    _ReviewStep.portions,
    _ReviewStep.nutrition,
    _ReviewStep.details,
    _ReviewStep.glycemic,
    _ReviewStep.summary,
    _ReviewStep.recommendation,
  ];

  String get _title => switch (_step) {
        _ReviewStep.foods => 'Meal Review',
        _ReviewStep.editFood => 'Edit Food',
        _ReviewStep.portions => 'Confirm Portions',
        _ReviewStep.nutrition => 'Nutrition Analysis',
        _ReviewStep.details => 'Nutrition Details',
        _ReviewStep.glycemic => 'Glycemic Profile',
        _ReviewStep.summary => 'Meal Summary',
        _ReviewStep.recommendation => 'Portion Recommendation',
      };

  void _next() {
    final index = _steps.indexOf(_step);
    if (index >= 0 && index < _steps.length - 1) {
      setState(() => _step = _steps[index + 1]);
    }
  }

  void _back() {
    if (_step == _ReviewStep.editFood) {
      setState(() => _step = _ReviewStep.foods);
      return;
    }
    final index = _steps.indexOf(_step);
    if (index > 0) setState(() => _step = _steps[index - 1]);
  }

  void _addFood() {
    final controller = TextEditingController();
    showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add a food'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Food name'),
          textCapitalization: TextCapitalization.words,
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
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
            portion:
                const Portion(grams: 0, estimationMethod: Portion.userEdited),
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
    if (_saving ||
        _includedFoods.isEmpty ||
        _includedFoods.any((food) => food.portion.grams <= 0)) {
      setState(() => _saveError =
          'Set a portion above 0 g for every selected food before saving.');
      return;
    }
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
    } on MealHistoryException catch (error) {
      if (mounted) setState(() => _saveError = error.userMessage);
    } catch (_) {
      if (mounted) {
        setState(() => _saveError =
            'Could not save the meal. Check the connection and try again.');
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _savePortion(int index, double? grams) {
    if (grams == null || grams <= 0) return;
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

    return ColoredBox(
      color: MealScanStyle.background,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: Row(
              children: [
                if (_step != _ReviewStep.foods)
                  IconButton(
                    tooltip: 'Back',
                    onPressed: _back,
                    icon: const Icon(Icons.arrow_back),
                  )
                else
                  const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    _title,
                    style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                        color: MealScanStyle.text),
                  ),
                ),
                if (_step != _ReviewStep.foods)
                  Text('${_steps.indexOf(_step) + 1}/${_steps.length}',
                      style:
                          const TextStyle(color: MealScanStyle.textSecondary)),
              ],
            ),
          ),
          if (_step != _ReviewStep.foods)
            _StepProgress(value: (_steps.indexOf(_step) + 1) / _steps.length),
          Expanded(child: _buildStep()),
        ],
      ),
    );
  }

  Widget _buildStep() => switch (_step) {
        _ReviewStep.foods => _buildFoods(),
        _ReviewStep.portions => _buildPortions(),
        _ReviewStep.nutrition => _buildNutrition(),
        _ReviewStep.details => _buildDetails(),
        _ReviewStep.glycemic => _buildGlycemic(),
        _ReviewStep.summary => _buildSummary(),
        _ReviewStep.recommendation => _buildRecommendation(),
        _ReviewStep.editFood => const SizedBox.shrink(),
      };

  Widget _buildFoods() => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _IntroCard(
            icon: Icons.auto_awesome,
            text:
                'Review the foods recognized in your meal. Select the items you ate.',
          ),
          const SizedBox(height: 14),
          if (widget.analysis.isMock) const _DemoNotice(),
          for (var i = 0; i < _foods.length; i++) ...[
            _FoodCard(
              food: _foods[i],
              selected: _included[i],
              onSelected: (selected) => setState(() => _included[i] = selected),
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
          OutlinedButton.icon(
            style: MealScanStyle.secondaryButton(),
            onPressed: _addFood,
            icon: const Icon(Icons.add),
            label: const Text('Add food'),
          ),
          const SizedBox(height: 10),
          FilledButton(
            style: MealScanStyle.primaryButton(),
            onPressed: _includedFoods.isEmpty ? null : _next,
            child: const Text('Confirm Foods'),
          ),
        ],
      );

  Widget _buildPortions() => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const _IntroCard(
              icon: Icons.scale_outlined,
              text: 'Check each portion and enter the amount in grams.'),
          const SizedBox(height: 14),
          for (final food in _includedFoods) ...[
            _PortionCard(
                food: food,
                onSave: (grams) => _savePortion(_foods.indexOf(food), grams)),
            const SizedBox(height: 10),
          ],
          const SizedBox(height: 6),
          FilledButton(
            style: MealScanStyle.primaryButton(),
            onPressed: _includedFoods.isEmpty ? null : _next,
            child: const Text('Continue to Nutrition'),
          ),
        ],
      );

  Widget _buildNutrition() => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _MetricHero(
              value: formatNutrient(_totals.energyKcal, 'kcal'),
              label: 'Estimated Calories'),
          const SizedBox(height: 14),
          _NutritionTable(profile: _totals),
          const SizedBox(height: 12),
          const _InfoCard(
              text:
                  'Glycemic information is shown separately when the meal analysis provides it.'),
          const SizedBox(height: 16),
          FilledButton(
            style: MealScanStyle.primaryButton(),
            onPressed: _next,
            child: const Text('View Nutrition Details'),
          ),
        ],
      );

  Widget _buildDetails() => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (widget.analysis.isMock) const _DemoNotice(),
          for (final food in _includedFoods) ...[
            _FoodNutritionCard(food: food),
            const SizedBox(height: 10),
          ],
          const Text('Meal Total',
              style: TextStyle(
                  fontWeight: FontWeight.w700, color: MealScanStyle.text)),
          const SizedBox(height: 8),
          _NutritionTable(profile: _totals),
          const SizedBox(height: 16),
          FilledButton(
            style: MealScanStyle.primaryButton(),
            onPressed: _next,
            child: const Text('Continue to Glycemic Profile'),
          ),
        ],
      );

  Widget _buildGlycemic() => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const _IntroCard(
              icon: Icons.bubble_chart_outlined,
              text: 'Estimated glycemic information for this meal.'),
          const SizedBox(height: 14),
          const _UnknownMetricCard(label: 'Glycemic index'),
          const _UnknownMetricCard(label: 'Glycemic load'),
          const _UnknownMetricCard(label: 'Glucose spike risk'),
          const _UnknownMetricCard(label: 'Estimated glucose response'),
          const SizedBox(height: 8),
          const _InfoCard(
            text:
                'Not available. The current meal analysis response does not include GI, GL, spike risk, or a glucose response estimate.',
          ),
          const SizedBox(height: 14),
          const Text(
            'Glycemic Index describes the relative effect of carbohydrate-containing foods on blood glucose. Glycemic Load also accounts for the carbohydrate amount in a portion.',
            style: TextStyle(
                fontSize: 12, height: 1.45, color: MealScanStyle.textSecondary),
          ),
          const SizedBox(height: 16),
          FilledButton(
            style: MealScanStyle.primaryButton(),
            onPressed: _next,
            child: const Text('Continue to Meal Summary'),
          ),
        ],
      );

  Widget _buildSummary() => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const _IntroCard(
              icon: Icons.check_circle_outline, text: 'Meal analysis complete'),
          const SizedBox(height: 14),
          _SummaryHeader(
            mealType: widget.analysis.mealType?.label ?? 'Meal',
            capturedAt: widget.capturedAt,
            foodCount: _includedFoods.length,
          ),
          const SizedBox(height: 12),
          _NutritionTable(profile: _totals),
          const SizedBox(height: 12),
          const _UnknownMetricCard(label: 'Glycemic profile'),
          if (widget.analysis.isMock) ...[
            const SizedBox(height: 10),
            const _DemoNotice(),
          ],
          if (_saved)
            const _InfoCard(text: 'Meal saved to your demo meal history.'),
          if (_saveError != null) ...[
            const SizedBox(height: 10),
            _InfoCard(text: _saveError!),
          ],
          const SizedBox(height: 16),
          FilledButton(
            style: MealScanStyle.primaryButton(),
            onPressed: _saving || _saved ? null : _saveMeal,
            child: Text(_saving
                ? 'Saving…'
                : _saved
                    ? 'Meal Saved'
                    : 'Save Meal'),
          ),
          const SizedBox(height: 8),
          FilledButton(
            style: MealScanStyle.secondaryButton(),
            onPressed: _next,
            child: const Text('View Portion Recommendation'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            style: MealScanStyle.secondaryButton(),
            onPressed: widget.onScanAgain,
            icon: const Icon(Icons.camera_alt_outlined),
            label: const Text('Scan another meal'),
          ),
        ],
      );

  Widget _buildRecommendation() => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const _IntroCard(
              icon: Icons.lightbulb_outline,
              text: 'Portion guidance based on your profile'),
          const SizedBox(height: 14),
          const _UnknownMetricCard(label: 'Profile-based portion suggestion'),
          const _InfoCard(
            text:
                'Not available. A profile-based recommendation is not included in the current meal analysis response.',
          ),
          const SizedBox(height: 16),
          OutlinedButton(
            style: MealScanStyle.secondaryButton(),
            onPressed: () => setState(() => _step = _ReviewStep.portions),
            child: const Text('Review Portions'),
          ),
          const SizedBox(height: 8),
          FilledButton(
            style: MealScanStyle.primaryButton(),
            onPressed: widget.onScanAgain,
            child: const Text('Scan another meal'),
          ),
        ],
      );
}

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
  late final Map<String, TextEditingController> _nutrients = {
    'Energy (kcal)':
        TextEditingController(text: _input(widget.food.nutrition.energyKcal)),
    'Carbohydrate (g)': TextEditingController(
        text: _input(widget.food.nutrition.carbohydrateG)),
    'Protein (g)':
        TextEditingController(text: _input(widget.food.nutrition.proteinG)),
    'Fat (g)': TextEditingController(text: _input(widget.food.nutrition.fatG)),
    'Sugars (g)':
        TextEditingController(text: _input(widget.food.nutrition.sugarsG)),
    'Dietary fibre (g)': TextEditingController(
        text: _input(widget.food.nutrition.dietaryFiberG)),
    'Sodium (mg)':
        TextEditingController(text: _input(widget.food.nutrition.sodiumMg)),
  };
  late final Set<String> _visible = _nutrients.keys.toSet();

  String _input(double? value) => value == null ? '' : formatAmount(value);

  @override
  void dispose() {
    _label.dispose();
    for (final controller in _nutrients.values) {
      controller.dispose();
    }
    super.dispose();
  }

  double? _value(String label) =>
      double.tryParse(_nutrients[label]!.text.trim());

  void _save() {
    final label = _label.text.trim();
    if (label.isEmpty) return;
    widget.onSave(FoodItem(
      itemId: widget.food.itemId,
      label: label,
      portion: widget.food.portion,
      nutrition: NutrientProfile(
        energyKcal:
            _visible.contains('Energy (kcal)') ? _value('Energy (kcal)') : null,
        carbohydrateG: _visible.contains('Carbohydrate (g)')
            ? _value('Carbohydrate (g)')
            : null,
        proteinG:
            _visible.contains('Protein (g)') ? _value('Protein (g)') : null,
        fatG: _visible.contains('Fat (g)') ? _value('Fat (g)') : null,
        sugarsG: _visible.contains('Sugars (g)') ? _value('Sugars (g)') : null,
        dietaryFiberG: _visible.contains('Dietary fibre (g)')
            ? _value('Dietary fibre (g)')
            : null,
        sodiumMg:
            _visible.contains('Sodium (mg)') ? _value('Sodium (mg)') : null,
      ),
      nutritionSource: widget.food.nutritionSource,
    ));
  }

  @override
  Widget build(BuildContext context) => ColoredBox(
        color: MealScanStyle.background,
        child: Column(
          children: [
            ListTile(
              leading: IconButton(
                  onPressed: widget.onCancel,
                  icon: const Icon(Icons.arrow_back)),
              title: const Text('Edit Food',
                  style: TextStyle(fontWeight: FontWeight.w700)),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  TextField(
                    controller: _label,
                    textCapitalization: TextCapitalization.words,
                    decoration: const InputDecoration(
                        labelText: 'Food name', border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 18),
                  const Text('Nutrients',
                      style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  for (final label in _nutrients.keys.where(_visible.contains))
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _nutrients[label],
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                            decoration: InputDecoration(labelText: label),
                          ),
                        ),
                        IconButton(
                          tooltip: 'Remove $label',
                          onPressed: () =>
                              setState(() => _visible.remove(label)),
                          icon: const Icon(Icons.remove_circle_outline),
                        ),
                      ],
                    ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _visible.length == _nutrients.length
                        ? null
                        : () => setState(() => _visible.add(_nutrients.keys
                            .firstWhere((key) => !_visible.contains(key)))),
                    icon: const Icon(Icons.add),
                    label: const Text('Add nutrient'),
                  ),
                  const SizedBox(height: 8),
                  const _InfoCard(
                      text:
                          'Leave a nutrient blank when its value is unknown.'),
                  const SizedBox(height: 16),
                  FilledButton(
                      style: MealScanStyle.primaryButton(),
                      onPressed: _save,
                      child: const Text('Save Changes')),
                  TextButton(
                      onPressed: widget.onCancel, child: const Text('Cancel')),
                ],
              ),
            ),
          ],
        ),
      );
}

class _StepProgress extends StatelessWidget {
  const _StepProgress({required this.value});
  final double value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
              value: value,
              minHeight: 4,
              color: MealScanStyle.primary,
              backgroundColor: MealScanStyle.border),
        ),
      );
}

class _IntroCard extends StatelessWidget {
  const _IntroCard({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: MealScanStyle.primary.withAlpha(15),
          borderRadius: BorderRadius.circular(MealScanStyle.cardRadius),
        ),
        child: Row(children: [
          Icon(icon, color: MealScanStyle.primary),
          const SizedBox(width: 10),
          Expanded(
              child: Text(text,
                  style:
                      const TextStyle(color: MealScanStyle.text, height: 1.35)))
        ]),
      );
}

class _DemoNotice extends StatelessWidget {
  const _DemoNotice();

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: MealScanStyle.warningTint,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: MealScanStyle.warning)),
        child: const Row(children: [
          Icon(Icons.info_outline, color: MealScanStyle.warning),
          SizedBox(width: 8),
          Expanded(
              child: Text('Demo data: these foods and values are placeholders.',
                  style: TextStyle(color: MealScanStyle.text)))
        ]),
      );
}

class _FoodCard extends StatelessWidget {
  const _FoodCard(
      {required this.food,
      required this.selected,
      required this.onSelected,
      required this.onEdit,
      required this.onRemove});
  final FoodItem food;
  final bool selected;
  final ValueChanged<bool> onSelected;
  final VoidCallback onEdit;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) => Container(
        decoration: MealScanStyle.cardDecoration(),
        child: Row(children: [
          Checkbox(
              value: selected,
              onChanged: (value) => onSelected(value ?? false),
              activeColor: MealScanStyle.primary),
          const Icon(Icons.restaurant, color: MealScanStyle.primary),
          const SizedBox(width: 8),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text(food.label,
                    style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: MealScanStyle.text)),
                const SizedBox(height: 3),
                Text(
                    '${formatNutrient(food.nutrition.energyKcal, 'kcal')} · ${food.portion.grams > 0 ? '${formatAmount(food.portion.grams)} g' : 'Portion not available'}',
                    style: const TextStyle(
                        fontSize: 12, color: MealScanStyle.textSecondary))
              ])),
          IconButton(
              tooltip: 'Edit ${food.label}',
              onPressed: onEdit,
              icon: const Icon(Icons.edit_outlined)),
          IconButton(
              tooltip: 'Remove ${food.label}',
              onPressed: onRemove,
              icon: const Icon(Icons.close)),
        ]),
      );
}

class _PortionCard extends StatefulWidget {
  const _PortionCard({required this.food, required this.onSave});
  final FoodItem food;
  final ValueChanged<double?> onSave;

  @override
  State<_PortionCard> createState() => _PortionCardState();
}

class _PortionCardState extends State<_PortionCard> {
  late final TextEditingController _controller = TextEditingController(
      text: widget.food.portion.grams > 0
          ? formatAmount(widget.food.portion.grams)
          : '');
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: MealScanStyle.cardDecoration(),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(widget.food.label,
              style: const TextStyle(
                  fontWeight: FontWeight.w700, color: MealScanStyle.text)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
                child: TextField(
                    controller: _controller,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                        labelText: 'Exact portion',
                        suffixText: 'g',
                        border: OutlineInputBorder()))),
            const SizedBox(width: 8),
            FilledButton(
                onPressed: () {
                  final grams = double.tryParse(_controller.text.trim());
                  if (grams == null || grams <= 0 || grams > 2000) {
                    setState(() => _error = grams == null
                        ? 'Enter the portion in grams.'
                        : grams <= 0
                            ? 'Enter an amount above 0 g.'
                            : 'Enter an amount up to 2000 g.');
                    return;
                  }
                  setState(() => _error = null);
                  widget.onSave(grams);
                },
                child: const Text('Set')),
          ]),
          if (_error != null) ...[
            const SizedBox(height: 4),
            Text(_error!,
                style:
                    const TextStyle(color: MealScanStyle.danger, fontSize: 12)),
          ],
          const SizedBox(height: 4),
          Text(
              'Estimate: ${widget.food.portion.grams > 0 ? '${formatAmount(widget.food.portion.grams)} g' : 'Not available'}',
              style: const TextStyle(
                  fontSize: 12, color: MealScanStyle.textSecondary)),
        ]),
      );
}

class _MetricHero extends StatelessWidget {
  const _MetricHero({required this.value, required this.label});
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
            color: MealScanStyle.card,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: MealScanStyle.border)),
        child: Column(children: [
          Text(label,
              style: const TextStyle(color: MealScanStyle.textSecondary)),
          const SizedBox(height: 8),
          Text(value,
              style: const TextStyle(
                  fontSize: 30,
                  fontWeight: FontWeight.w800,
                  color: MealScanStyle.primary))
        ]),
      );
}

class _NutritionTable extends StatelessWidget {
  const _NutritionTable({required this.profile});
  final NutrientProfile profile;

  @override
  Widget build(BuildContext context) {
    final rows = <(String, double?, String)>[
      ('Carbohydrates', profile.carbohydrateG, 'g'),
      ('Protein', profile.proteinG, 'g'),
      ('Fat', profile.fatG, 'g'),
      ('Sugars', profile.sugarsG, 'g'),
      ('Dietary fibre', profile.dietaryFiberG, 'g'),
      ('Sodium', profile.sodiumMg, 'mg'),
      ('Other micronutrients', null, ''),
    ];
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: MealScanStyle.cardDecoration(),
      child: Column(children: [
        for (var i = 0; i < rows.length; i++) ...[
          if (i > 0) const Divider(height: 1, color: MealScanStyle.border),
          Padding(
              padding: const EdgeInsets.symmetric(vertical: 11),
              child: Row(children: [
                Expanded(
                    child: Text(rows[i].$1,
                        style: const TextStyle(color: MealScanStyle.text))),
                Text(formatNutrient(rows[i].$2, rows[i].$3),
                    style: const TextStyle(
                        fontWeight: FontWeight.w700, color: MealScanStyle.text))
              ])),
        ],
      ]),
    );
  }
}

class _FoodNutritionCard extends StatelessWidget {
  const _FoodNutritionCard({required this.food});
  final FoodItem food;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: MealScanStyle.cardDecoration(),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
                child: Text(food.label,
                    style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: MealScanStyle.text))),
            Text(
                food.portion.grams > 0
                    ? '${formatAmount(food.portion.grams)} g'
                    : 'Not available',
                style: const TextStyle(
                    fontSize: 12, color: MealScanStyle.textSecondary))
          ]),
          const SizedBox(height: 10),
          Wrap(spacing: 10, runSpacing: 10, children: [
            _NutrientMini(
                label: 'Calories',
                value: food.nutrition.energyKcal,
                unit: 'kcal'),
            _NutrientMini(
                label: 'Carbs', value: food.nutrition.carbohydrateG, unit: 'g'),
            _NutrientMini(
                label: 'Protein', value: food.nutrition.proteinG, unit: 'g'),
            _NutrientMini(label: 'Fat', value: food.nutrition.fatG, unit: 'g'),
            _NutrientMini(
                label: 'Fibre', value: food.nutrition.dietaryFiberG, unit: 'g'),
            _NutrientMini(
                label: 'Sodium', value: food.nutrition.sodiumMg, unit: 'mg'),
            const _NutrientMini(
                label: 'Other micronutrients', value: null, unit: ''),
          ]),
          const SizedBox(height: 8),
          Text('Source: ${sourceLabel(food.nutritionSource)}',
              style: const TextStyle(
                  fontSize: 11, color: MealScanStyle.textSecondary)),
        ]),
      );
}

class _NutrientMini extends StatelessWidget {
  const _NutrientMini(
      {required this.label, required this.value, required this.unit});
  final String label;
  final double? value;
  final String unit;

  @override
  Widget build(BuildContext context) => SizedBox(
      width: 96,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label,
            style: const TextStyle(
                fontSize: 11, color: MealScanStyle.textSecondary)),
        const SizedBox(height: 2),
        Text(formatNutrient(value, unit),
            style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: MealScanStyle.text))
      ]));
}

class _UnknownMetricCard extends StatelessWidget {
  const _UnknownMetricCard({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: MealScanStyle.cardDecoration(),
        child: Row(children: [
          Expanded(
              child: Text(label,
                  style: const TextStyle(
                      fontWeight: FontWeight.w600, color: MealScanStyle.text))),
          const Text('Not available',
              style: TextStyle(color: MealScanStyle.textSecondary))
        ]),
      );
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
            color: MealScanStyle.primary.withAlpha(12),
            borderRadius: BorderRadius.circular(12)),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.info_outline,
              size: 18, color: MealScanStyle.primary),
          const SizedBox(width: 8),
          Expanded(
              child: Text(text,
                  style: const TextStyle(
                      fontSize: 12, height: 1.4, color: MealScanStyle.text)))
        ]),
      );
}

class _SummaryHeader extends StatelessWidget {
  const _SummaryHeader(
      {required this.mealType,
      required this.capturedAt,
      required this.foodCount});
  final String mealType;
  final DateTime capturedAt;
  final int foodCount;

  @override
  Widget build(BuildContext context) {
    final time = TimeOfDay.fromDateTime(capturedAt).format(context);
    final date =
        '${capturedAt.year}-${capturedAt.month.toString().padLeft(2, '0')}-${capturedAt.day.toString().padLeft(2, '0')}';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: MealScanStyle.cardDecoration(),
      child: Row(children: [
        const CircleAvatar(
            backgroundColor: MealScanStyle.primary,
            child: Icon(Icons.restaurant, color: Colors.white)),
        const SizedBox(width: 12),
        Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(mealType,
              style: const TextStyle(
                  fontWeight: FontWeight.w700, color: MealScanStyle.text)),
          const SizedBox(height: 3),
          Text('$date · $time · $foodCount foods',
              style: const TextStyle(
                  fontSize: 12, color: MealScanStyle.textSecondary))
        ]))
      ]),
    );
  }
}
