import 'package:flutter/material.dart';

import '../../core/theme.dart';
import 'data/meal_history_api.dart';
import 'data/meal_history_models.dart';
import 'meal_detail_screen.dart';
import 'widgets/nutrient_row.dart';

/// Today's intake summary, with a list of meals logged today.
class TodaySummaryScreen extends StatefulWidget {
  const TodaySummaryScreen({super.key, this.api});

  final MealHistoryApi? api;

  @override
  State<TodaySummaryScreen> createState() => _TodaySummaryScreenState();
}

class _TodaySummaryScreenState extends State<TodaySummaryScreen> {
  late final MealHistoryApi _api;
  DailySummary? _summary;
  String? _error;

  @override
  void initState() {
    super.initState();
    _api = widget.api ?? MealHistoryApi();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _summary = null;
      _error = null;
    });
    try {
      final now = DateTime.now();
      final offsetMinutes = now.timeZoneOffset.inMinutes;
      final summary =
          await _api.dailySummary(now, utcOffsetMinutes: offsetMinutes);
      if (mounted) setState(() => _summary = summary);
    } on MealHistoryException catch (e) {
      if (mounted) setState(() => _error = e.userMessage);
    } catch (_) {
      if (mounted) {
        setState(
            () => _error = 'Could not load summary. Check your connection.');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Today's Intake"),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: _body(),
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
    if (_summary == null) {
      return const Center(child: CircularProgressIndicator());
    }

    final s = _summary!;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(18, 8, 18, 28),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.primaryDark,
              borderRadius: BorderRadius.circular(22),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Text('Today',
                      style: Theme.of(context)
                          .textTheme
                          .titleLarge
                          ?.copyWith(color: Colors.white)),
                  const Spacer(),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.accent,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${s.mealCount} meal${s.mealCount == 1 ? '' : 's'} logged',
                      style: const TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w800,
                          color: AppColors.primaryDark),
                    ),
                  ),
                ]),
                const SizedBox(height: 16),
                NutrientTable(
                  s.totals,
                  color: Colors.white,
                  mutedColor: Colors.white60,
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          if (s.meals.isEmpty)
            const Center(child: Text('No meals logged today.'))
          else ...[
            Text('Meals today', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 10),
            for (final meal in s.meals)
              Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: ListTile(
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
                  leading: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: AppColors.primaryLight,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.restaurant_outlined,
                        size: 19, color: AppColors.primary),
                  ),
                  title: Text(meal.mealType?.label ?? 'Meal'),
                  subtitle: Text(
                    _timeStr(meal.eatenAt) +
                        (meal.totals.energyKcal != null
                            ? '  ·  ${meal.totals.energyKcal!.toStringAsFixed(0)} kcal'
                            : ''),
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () async {
                    await Navigator.push<void>(
                      context,
                      MaterialPageRoute(
                        builder: (_) => MealDetailScreen(meal: meal, api: _api),
                      ),
                    );
                    _load();
                  },
                ),
              ),
          ],
          const SizedBox(height: 16),
          const Text(
            'These are estimated values. Portions and nutrients are approximate.',
            style: TextStyle(fontSize: 12),
          ),
        ],
      ),
    );
  }

  String _timeStr(DateTime dt) {
    final local = dt.toLocal();
    return '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }
}
