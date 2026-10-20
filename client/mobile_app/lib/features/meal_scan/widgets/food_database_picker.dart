import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/theme.dart';
import '../../meal_history/data/meal_history_api.dart';
import '../../meal_history/data/meal_history_models.dart';

/// Search the connected food table and return an exact row selected by the user.
Future<FoodResult?> showFoodDatabasePicker(
        BuildContext context, MealHistoryApi api,
        {String initialQuery = ''}) =>
    showModalBottomSheet<FoodResult>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      backgroundColor: AppColors.background,
      builder: (_) => _FoodDatabasePicker(api: api, initialQuery: initialQuery),
    );

class _FoodDatabasePicker extends StatefulWidget {
  const _FoodDatabasePicker({required this.api, required this.initialQuery});

  final MealHistoryApi api;
  final String initialQuery;

  @override
  State<_FoodDatabasePicker> createState() => _FoodDatabasePickerState();
}

class _FoodDatabasePickerState extends State<_FoodDatabasePicker> {
  late final TextEditingController _query;
  Timer? _debounce;
  List<FoodResult>? _results;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _query = TextEditingController(text: widget.initialQuery);
    if (widget.initialQuery.trim().length >= 2) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _search(widget.initialQuery);
      });
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _query.dispose();
    super.dispose();
  }

  void _schedule(String value) {
    _debounce?.cancel();
    if (value.trim().length < 2) {
      setState(() {
        _results = null;
        _error = null;
        _busy = false;
      });
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 300), () => _search(value));
  }

  Future<void> _search(String value) async {
    final term = value.trim();
    setState(() {
      _busy = true;
      _results = null;
      _error = null;
    });
    try {
      final results = await widget.api.searchFoods(term);
      if (mounted && _query.text.trim() == term) {
        setState(() => _results = results);
      }
    } on MealHistoryException catch (error) {
      if (mounted && _query.text.trim() == term) {
        setState(() => _error = error.userMessage);
      }
    } catch (_) {
      if (mounted && _query.text.trim() == term) {
        setState(() => _error = 'Could not search foods. Try again.');
      }
    } finally {
      if (mounted && _query.text.trim() == term) {
        setState(() => _busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Padding(
        padding:
            EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * .78,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Find a food',
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 4),
                    const Text('Choose a food with nutrition data.',
                        style: TextStyle(color: AppColors.textSecondary)),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _query,
                      autofocus: true,
                      onChanged: _schedule,
                      onSubmitted: _search,
                      decoration: const InputDecoration(
                        hintText: 'Search rice, dhal, curry…',
                        prefixIcon: Icon(Icons.search_rounded),
                      ),
                    ),
                  ],
                ),
              ),
              if (_busy) const LinearProgressIndicator(minHeight: 2),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
                  children: [
                    if (_error != null)
                      ListTile(
                        title: Text(_error!),
                        trailing: IconButton(
                          tooltip: 'Retry',
                          onPressed: () => _search(_query.text),
                          icon: const Icon(Icons.refresh_rounded),
                        ),
                      )
                    else if (_results == null)
                      const Padding(
                        padding: EdgeInsets.only(top: 20),
                        child: Text('Enter at least two letters to search.'),
                      )
                    else if (_results!.isEmpty)
                      const Padding(
                        padding: EdgeInsets.only(top: 20),
                        child: Text('No matching foods found.'),
                      )
                    else
                      for (final food in _results!)
                        Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            title: Text(food.name),
                            subtitle: Text(food.per100g.energyKcal == null
                                ? 'Nutrition details vary by source'
                                : '${food.per100g.energyKcal!.round()} kcal per 100 g'),
                            trailing: const Icon(
                                Icons.add_circle_outline_rounded,
                                color: AppColors.primary),
                            onTap: () => Navigator.pop(context, food),
                          ),
                        ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
}
