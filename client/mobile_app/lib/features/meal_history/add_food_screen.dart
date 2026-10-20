import 'package:flutter/material.dart';

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
  List<FoodResult>? _results;
  String? _searchError;
  bool _searching = false;

  final List<_StagedItem> _staged = [];
  MealType? _mealType;

  bool _saving = false;
  String? _saveError;

  @override
  void initState() {
    super.initState();
    _api = widget.api ?? MealHistoryApi();
  }

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  Future<void> _search(String q) async {
    if (q.trim().length < 2) return;
    setState(() {
      _searching = true;
      _searchError = null;
      _results = null;
    });
    try {
      final r = await _api.searchFoods(q.trim());
      if (mounted) setState(() => _results = r);
    } on MealHistoryException catch (e) {
      if (mounted) setState(() => _searchError = e.userMessage);
    } catch (_) {
      if (mounted) setState(() => _searchError = 'Search failed. Check your connection.');
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

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
      if (mounted) setState(() => _saveError = 'Could not save meal. Try again.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Add Meal'),
        actions: [
          if (_staged.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.save_outlined),
              tooltip: 'Save meal',
              onPressed: _saving ? null : _save,
            ),
        ],
      ),
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
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: SearchBar(
              controller: _queryController,
              hintText: 'Search foods (e.g. rice, dhal)',
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
              padding: const EdgeInsets.all(8),
              children: [
                if (_staged.isNotEmpty) ...[
                  Padding(
                    padding: const EdgeInsets.only(left: 4, bottom: 4),
                    child: Text('Items to log',
                        style: Theme.of(context).textTheme.labelLarge),
                  ),
                  for (final s in _staged)
                    ListTile(
                      title: Text(s.name),
                      subtitle: Text('${s.grams.toStringAsFixed(0)} g'),
                      trailing: IconButton(
                        icon: const Icon(Icons.remove_circle_outline),
                        onPressed: () => setState(() => _staged.remove(s)),
                      ),
                    ),
                  const Divider(),
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
                      subtitle: Text(
                          '${f.category ?? f.source}  ·  per 100 g: '
                          '${f.per100g.energyKcal?.toStringAsFixed(0) ?? '—'} kcal'),
                      onTap: () => _addFromSearch(f),
                      trailing: const Icon(Icons.add),
                    ),
                  if (_results!.isEmpty)
                    const ListTile(title: Text('No foods matched.')),
                ],
                ListTile(
                  leading: const Icon(Icons.edit_outlined),
                  title: const Text('Enter food manually'),
                  onTap: _addManual,
                ),
              ],
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
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(foodName),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: 'Grams eaten',
            suffixText: 'g',
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
              if (g != null && g > 0) {
                Navigator.pop(ctx);
                onConfirm(g);
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  void _showManualDialog({
    required void Function(String name, double grams) onConfirm,
  }) {
    final nameCtrl = TextEditingController();
    final gramsCtrl = TextEditingController(text: '100');
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Enter food'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(labelText: 'Food name')),
            const SizedBox(height: 8),
            TextField(
              controller: gramsCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                  labelText: 'Grams', suffixText: 'g'),
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
              if (name.isNotEmpty && g != null && g > 0) {
                Navigator.pop(ctx);
                onConfirm(name, g);
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }
}

class _MealTypeSelector extends StatelessWidget {
  const _MealTypeSelector({required this.value, required this.onChanged});

  final MealType? value;
  final ValueChanged<MealType?> onChanged;

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
                onSelected: (_) => onChanged(value == t ? null : t),
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
