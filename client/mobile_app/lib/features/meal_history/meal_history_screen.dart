import 'package:flutter/material.dart';

import 'add_food_screen.dart';
import 'data/meal_history_api.dart';
import 'data/meal_history_models.dart';
import 'meal_detail_screen.dart';

/// Shows the list of logged meals, newest first.
class MealHistoryScreen extends StatefulWidget {
  const MealHistoryScreen({super.key, this.api});

  final MealHistoryApi? api;

  @override
  State<MealHistoryScreen> createState() => _MealHistoryScreenState();
}

class _MealHistoryScreenState extends State<MealHistoryScreen> {
  late final MealHistoryApi _api;
  List<MealOut>? _meals;
  String? _error;

  @override
  void initState() {
    super.initState();
    _api = widget.api ?? MealHistoryApi();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _meals = null;
      _error = null;
    });
    try {
      final meals = await _api.listMeals();
      if (mounted) setState(() => _meals = meals);
    } on MealHistoryException catch (e) {
      if (mounted) setState(() => _error = e.userMessage);
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not load meals. Check your connection.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Meal History'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _load,
          ),
        ],
      ),
      body: _body(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await Navigator.push<void>(
            context,
            MaterialPageRoute(
                builder: (_) => AddFoodScreen(api: _api)),
          );
          _load();
        },
        icon: const Icon(Icons.add),
        label: const Text('Add meal'),
      ),
    );
  }

  Widget _body() {
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(onPressed: _load, child: const Text('Retry')),
          ],
        ),
      );
    }
    if (_meals == null) return const Center(child: CircularProgressIndicator());
    if (_meals!.isEmpty) {
      return const Center(child: Text('No meals logged yet.'));
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(vertical: 8),
        itemCount: _meals!.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, i) => _MealTile(
          meal: _meals![i],
          onTap: () async {
            await Navigator.push<void>(
              context,
              MaterialPageRoute(
                builder: (_) => MealDetailScreen(meal: _meals![i], api: _api),
              ),
            );
            _load();
          },
        ),
      ),
    );
  }
}

class _MealTile extends StatelessWidget {
  const _MealTile({required this.meal, required this.onTap});

  final MealOut meal;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dt = meal.eatenAt.toLocal();
    final dateStr =
        '${dt.day}/${dt.month}/${dt.year}  ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    final kcal = meal.totals.energyKcal;
    final subtitle = [
      if (meal.mealType != null) meal.mealType!.label,
      if (kcal != null) '${kcal.toStringAsFixed(0)} kcal',
      '${meal.items.length} item${meal.items.length == 1 ? '' : 's'}',
    ].join(' · ');

    return ListTile(
      onTap: onTap,
      leading: Icon(
        _mealIcon(meal.mealType),
        color: theme.colorScheme.primary,
      ),
      title: Text(dateStr),
      subtitle: Text(subtitle),
      trailing: const Icon(Icons.chevron_right),
    );
  }

  IconData _mealIcon(MealType? t) {
    switch (t) {
      case MealType.breakfast:
        return Icons.free_breakfast_outlined;
      case MealType.lunch:
        return Icons.lunch_dining_outlined;
      case MealType.dinner:
        return Icons.dinner_dining_outlined;
      case MealType.snack:
        return Icons.cookie_outlined;
      case null:
        return Icons.restaurant_outlined;
    }
  }
}
