import 'package:flutter/material.dart';

import '../../core/theme.dart';
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
      if (mounted) {
        setState(() => _error = 'Could not load meals. Check your connection.');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Meal history'),
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
            MaterialPageRoute(builder: (_) => AddFoodScreen(api: _api)),
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
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: AppColors.primaryLight,
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Icon(Icons.restaurant_menu_rounded,
                  size: 32, color: AppColors.primary),
            ),
            const SizedBox(height: 18),
            Text('No meals logged yet.',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 7),
            const Text(
              'Scan a plate or add a meal manually. Your meal timeline will appear here.',
              textAlign: TextAlign.center,
              style: TextStyle(height: 1.45, color: AppColors.textSecondary),
            ),
          ]),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(18, 8, 18, 96),
        itemCount: _meals!.length,
        separatorBuilder: (_, __) => const SizedBox(height: 10),
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
      if (kcal != null) '${kcal.toStringAsFixed(0)} kcal',
      '${meal.items.length} item${meal.items.length == 1 ? '' : 's'}',
    ].join(' · ');

    return Material(
      color: AppColors.card,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: AppColors.border),
          ),
          child: Row(children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: AppColors.primaryLight,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(_mealIcon(meal.mealType),
                  color: theme.colorScheme.primary, size: 21),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(meal.mealType?.label ?? 'Meal',
                      style: theme.textTheme.titleMedium),
                  const SizedBox(height: 3),
                  Text('$dateStr  ·  $subtitle',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(
                          color: AppColors.textSecondary, height: 1.35)),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded,
                color: AppColors.textSecondary),
          ]),
        ),
      ),
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
