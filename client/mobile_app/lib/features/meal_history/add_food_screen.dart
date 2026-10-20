import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/theme.dart';
import 'data/meal_history_api.dart';
import 'data/meal_history_models.dart';

/// Search the food database and log a meal, or enter a food manually.
class AddFoodScreen extends StatefulWidget {
  const AddFoodScreen({super.key, this.api});

  final MealHistoryApi? api;

  @override
  State<AddFoodScreen> createState() => _AddFoodScreenState();
}

class _AddFoodScreenState extends State<AddFoodScreen> {
  late final MealHistoryApi _api;

  final _queryController = TextEditingController();
  Timer? _searchDebounce;
  List<FoodResult>? _results;
  String? _searchError;
  bool _searching = false;

  final List<_StagedItem> _staged = [];
  MealType _mealType = MealType.values[DateTime.now().hour < 11
      ? 0
      : DateTime.now().hour < 16
          ? 1
          : 2];

  bool _saving = false;
  String? _saveError;

  @override
  void initState() {
    super.initState();
    _api = widget.api ?? MealHistoryApi();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _queryController.dispose();
    super.dispose();
  }

  Future<void> _search(String q) async {
    if (q.trim().length < 2) {
      setState(() {
        _results = null;
        _searchError = null;
      });
      return;
    }
    setState(() {
      _searching = true;
      _searchError = null;
      _results = null;
    });
    try {
      final r = await _api.searchFoods(q.trim());
      if (mounted && _queryController.text.trim() == q.trim()) {
        setState(() => _results = r);
      }
    } on MealHistoryException catch (e) {
      if (mounted && _queryController.text.trim() == q.trim()) {
        setState(() => _searchError = e.userMessage);
      }
    } catch (_) {
      if (mounted && _queryController.text.trim() == q.trim()) {
        setState(() => _searchError = 'Search failed. Check your connection.');
      }
    } finally {
      if (mounted && _queryController.text.trim() == q.trim()) {
        setState(() => _searching = false);
      }
    }
  }

  void _queueSearch(String query) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(
      const Duration(milliseconds: 350),
      () => _search(query),
    );
  }

  NutrientProfile get _knownTotals => NutrientProfile.sumAvailable([
        for (final item in _staged)
          if (item.per100g != null) item.per100g!.scale(item.grams / 100),
      ]);

  void _addFromSearch(FoodResult food) {
    _showGramsDialog(
      foodName: food.name,
      onConfirm: (grams) {
        setState(() {
          _staged.add(_StagedItem.fromFood(food: food, grams: grams));
        });
      },
    );
  }

  void _addManual() {
    _showManualDialog(
      onConfirm: (name, grams) {
        setState(() {
          _staged.add(_StagedItem.manual(name: name, grams: grams));
        });
      },
    );
  }

  Future<void> _save() async {
    if (_staged.isEmpty) return;
    setState(() {
      _saving = true;
      _saveError = null;
    });
    try {
      final create = MealCreate(
        mealType: _mealType,
        items: [for (final s in _staged) s.toMealItemIn()],
      );
      await _api.logMeal(create);
      if (mounted) {
        Navigator.pop(context, true); // signal refresh to caller
      }
    } on MealHistoryException catch (e) {
      if (mounted) setState(() => _saveError = e.userMessage);
    } catch (_) {
      if (mounted) {
        setState(() => _saveError = 'Could not save meal. Try again.');
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add meal')),
      body: Column(
        children: [
          if (_saveError != null)
            MaterialBanner(
              content: Text(_saveError!),
              actions: [
                TextButton(
                  onPressed: () => setState(() => _saveError = null),
                  child: const Text('Dismiss'),
                ),
              ],
            ),
          _MealTypeSelector(
            value: _mealType,
            onChanged: (t) => setState(() => _mealType = t),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 8, 18, 8),
            child: SearchBar(
              controller: _queryController,
              hintText: 'Search foods (e.g. rice, dhal)',
              onChanged: _queueSearch,
              onSubmitted: _search,
              trailing: [
                if (_searching)
                  const Padding(
                    padding: EdgeInsets.only(right: 8),
                    child: SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  )
                else
                  IconButton(
                    icon: const Icon(Icons.search),
                    onPressed: () => _search(_queryController.text),
                  ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(18, 10, 18, 28),
              children: [
                if (_results == null &&
                    _staged.isEmpty &&
                    _queryController.text.isEmpty) ...[
                  Text('Start with a food',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  const Text(
                      'Search for a dish to use its available nutrient data, or enter your own food below.',
                      style: TextStyle(
                          color: AppColors.textSecondary, height: 1.4)),
                  const SizedBox(height: 12),
                  Wrap(spacing: 8, children: [
                    for (final suggestion in ['Rice', 'Dhal', 'Roti'])
                      ActionChip(
                        label: Text(suggestion),
                        onPressed: () {
                          _queryController.text = suggestion;
                          _search(suggestion);
                        },
                      ),
                  ]),
                  const SizedBox(height: 14),
                ],
                if (_staged.isNotEmpty) ...[
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text('Items to log',
                        style: Theme.of(context).textTheme.titleMedium),
                  ),
                  for (final s in _staged)
                    Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        leading: Container(
                          width: 38,
                          height: 38,
                          decoration: BoxDecoration(
                            color: AppColors.primaryLight,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.restaurant_outlined,
                              size: 18, color: AppColors.primary),
                        ),
                        title: Text(s.name),
                        subtitle: Text('${s.grams.toStringAsFixed(0)} g'),
                        trailing: IconButton(
                          icon: const Icon(Icons.close_rounded),
                          onPressed: () => setState(() => _staged.remove(s)),
                        ),
                      ),
                    ),
                  const SizedBox(height: 12),
                  Card(
                    color: AppColors.primaryLight,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(children: [
                        const Icon(Icons.summarize_outlined,
                            color: AppColors.primary),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Estimated energy',
                                  style:
                                      Theme.of(context).textTheme.titleMedium),
                              Text(
                                  _knownTotals.energyKcal == null
                                      ? 'Nutrition is not available for these items'
                                      : '${_knownTotals.energyKcal!.round()} kcal from matched foods',
                                  style: Theme.of(context).textTheme.bodySmall),
                            ],
                          ),
                        ),
                      ]),
                    ),
                  ),
                  const SizedBox(height: 14),
                ],
                if (_searchError != null)
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: Text(_searchError!,
                        style: TextStyle(
                            color: Theme.of(context).colorScheme.error)),
                  ),
                if (_results != null) ...[
                  for (final f in _results!)
                    ListTile(
                      title: Text(f.name),
                      subtitle: Text('${f.category ?? f.source}  ·  per 100 g: '
                          '${f.per100g.energyKcal?.toStringAsFixed(0) ?? '—'} kcal'),
                      onTap: () => _addFromSearch(f),
                      trailing: const Icon(Icons.add),
                    ),
                  if (_results!.isEmpty)
                    const ListTile(
                      title: Text('No foods matched.'),
                      subtitle: Text('Try another name or enter it manually.'),
                    ),
                ],
                Card(
                  color: AppColors.primaryLight,
                  child: ListTile(
                    leading: const Icon(Icons.edit_outlined,
                        color: AppColors.primary),
                    title: const Text('Enter food manually'),
                    subtitle: const Text('Add an item not found in search'),
                    onTap: _addManual,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Manual foods are saved to your meal, but nutrient values will stay unavailable until matched to the food database.',
                  style: TextStyle(
                      fontSize: 11.5,
                      height: 1.4,
                      color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(18, 12, 18, 12),
            decoration: const BoxDecoration(
              color: AppColors.card,
              border: Border(top: BorderSide(color: AppColors.border)),
            ),
            child: SafeArea(
              top: false,
              child: FilledButton.icon(
                onPressed: _saving || _staged.isEmpty ? null : _save,
                icon: const Icon(Icons.check_rounded),
                label: Text(_saving
                    ? 'Saving meal…'
                    : 'Save ${_staged.length} ${_staged.length == 1 ? 'food' : 'foods'}'),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showGramsDialog({
    required String foodName,
    required void Function(double grams) onConfirm,
  }) {
    final controller = TextEditingController(text: '100');
    String? error;
    showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
          builder: (ctx, update) => AlertDialog(
                title: Text(foodName),
                content: TextField(
                  controller: controller,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: 'Grams eaten',
                    suffixText: 'g',
                    errorText: error,
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Cancel'),
                  ),
                  FilledButton(
                    onPressed: () {
                      final g = double.tryParse(controller.text);
                      if (g != null && g > 0 && g <= 5000) {
                        Navigator.pop(ctx);
                        onConfirm(g);
                      } else {
                        update(
                            () => error = 'Enter an amount from 1 to 5000 g.');
                      }
                    },
                    child: const Text('Add'),
                  ),
                ],
              )),
    );
  }

  void _showManualDialog({
    required void Function(String name, double grams) onConfirm,
  }) {
    final nameCtrl = TextEditingController();
    final gramsCtrl = TextEditingController(text: '100');
    String? error;
    showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
          builder: (ctx, update) => AlertDialog(
                title: const Text('Enter food'),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                        controller: nameCtrl,
                        decoration:
                            const InputDecoration(labelText: 'Food name')),
                    const SizedBox(height: 8),
                    TextField(
                      controller: gramsCtrl,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(
                          labelText: 'Grams',
                          suffixText: 'g',
                          errorText: error),
                    ),
                  ],
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Cancel'),
                  ),
                  FilledButton(
                    onPressed: () {
                      final name = nameCtrl.text.trim();
                      final g = double.tryParse(gramsCtrl.text);
                      if (name.isNotEmpty && g != null && g > 0 && g <= 5000) {
                        Navigator.pop(ctx);
                        onConfirm(name, g);
                      } else {
                        update(() => error = 'Enter a name and 1 to 5000 g.');
                      }
                    },
                    child: const Text('Add'),
                  ),
                ],
              )),
    );
  }
}

class _MealTypeSelector extends StatelessWidget {
  const _MealTypeSelector({required this.value, required this.onChanged});

  final MealType value;
  final ValueChanged<MealType> onChanged;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Row(
        children: [
          for (final t in MealType.values)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(t.label),
                selected: value == t,
                onSelected: (_) => onChanged(t),
              ),
            ),
        ],
      ),
    );
  }
}

class _StagedItem {
  _StagedItem.fromFood({required FoodResult food, required this.grams})
      : name = food.name,
        foodId = food.id,
        per100g = food.per100g;

  _StagedItem.manual({required this.name, required this.grams})
      : foodId = null,
        per100g = null;

  final String name;
  final double grams;
  final int? foodId;
  final NutrientProfile? per100g;

  MealItemIn toMealItemIn() {
    if (foodId != null) {
      return MealItemIn.fromFood(foodId: foodId!, grams: grams);
    }
    return MealItemIn.free(name: name, grams: grams);
  }
}
