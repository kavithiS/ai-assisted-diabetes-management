import 'package:flutter/material.dart';

import '../../core/theme.dart';
import 'data/meal_history_api.dart';
import 'data/meal_history_models.dart';
import 'widgets/nutrient_row.dart';

/// Shows one logged meal with its items, totals, and a delete action.
class MealDetailScreen extends StatelessWidget {
  const MealDetailScreen({super.key, required this.meal, required this.api});

  final MealOut meal;
  final MealHistoryApi api;

  @override
  Widget build(BuildContext context) {
    final dt = meal.eatenAt.toLocal();
    final dateStr =
        '${dt.day}/${dt.month}/${dt.year}  ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';

    return Scaffold(
      appBar: AppBar(
        title: Text(meal.mealType?.label ?? 'Meal'),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: 'Delete meal',
            onPressed: () => _confirmDelete(context),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 8, 18, 28),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.primaryDark,
              borderRadius: BorderRadius.circular(22),
            ),
            child: Row(children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: AppColors.accent,
                  borderRadius: BorderRadius.circular(15),
                ),
                child: const Icon(Icons.restaurant_rounded,
                    color: AppColors.primaryDark),
              ),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(meal.mealType?.label ?? 'Meal',
                        style: Theme.of(context)
                            .textTheme
                            .titleLarge
                            ?.copyWith(color: Colors.white)),
                    const SizedBox(height: 3),
                    Text(dateStr,
                        style: const TextStyle(
                            fontSize: 11.5, color: Colors.white70)),
                  ],
                ),
              ),
            ]),
          ),
          if (meal.note != null && meal.note!.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(meal.note!, style: Theme.of(context).textTheme.bodyMedium),
          ],
          const SizedBox(height: 22),
          Text('Foods', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 10),
          for (final item in meal.items) _ItemCard(item: item),
          const SizedBox(height: 18),
          Text('Totals', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: NutrientTable(meal.totals),
            ),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.warningBg,
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Text(
              'These are estimates. Portions and nutrient values are approximate.',
              style: TextStyle(
                  fontSize: 11.5, height: 1.4, color: AppColors.textSecondary),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete meal?'),
        content: const Text('This cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    try {
      await api.deleteMeal(meal.id);
      if (context.mounted) Navigator.pop(context);
    } on MealHistoryException catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.userMessage)));
      }
    }
  }
}

class _ItemCard extends StatelessWidget {
  const _ItemCard({required this.item});

  final MealItemOut item;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(item.name,
                      style: Theme.of(context).textTheme.titleSmall),
                ),
                Text('${item.grams.toStringAsFixed(0)} g',
                    style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
            const SizedBox(height: 8),
            NutrientTable(item.nutrients),
          ],
        ),
      ),
    );
  }
}
