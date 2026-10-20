import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/meal_history/data/meal_history_api.dart';
import 'package:mobile_app/features/meal_history/data/meal_history_models.dart';
import 'package:mobile_app/features/meal_history/meal_history_screen.dart';

// Minimal stub that returns what tests configure.
class _StubApi implements MealHistoryApi {
  _StubApi({this.meals = const [], this.throwError = false});

  final List<MealOut> meals;
  final bool throwError;

  @override
  Future<List<MealOut>> listMeals({int limit = 50, int offset = 0}) async {
    if (throwError) throw const MealHistoryException('TEST_ERROR', 500);
    return meals;
  }

  @override
  dynamic noSuchMethod(Invocation i) => super.noSuchMethod(i);
}

Widget _wrap(Widget child) =>
    MaterialApp(home: child);

void main() {
  testWidgets('shows loading indicator initially', (tester) async {
    // Never resolves during the pump — just check the spinner is there.
    var loaded = false;
    final api = _StubApi(meals: []);
    await tester.pumpWidget(_wrap(MealHistoryScreen(api: api)));
    // After first pump (before async resolves) we see the spinner.
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    loaded = true;
    expect(loaded, isTrue); // avoid unused warning
  });

  testWidgets('shows empty message when no meals', (tester) async {
    await tester.pumpWidget(_wrap(MealHistoryScreen(api: _StubApi())));
    await tester.pumpAndSettle();
    expect(find.text('No meals logged yet.'), findsOneWidget);
  });

  testWidgets('shows meal tiles when meals are returned', (tester) async {
    final meal = MealOut.fromJson({
      'id': 1,
      'eaten_at': '2026-10-16T08:00:00Z',
      'meal_type': 'breakfast',
      'note': null,
      'items': [],
      'totals': {
        'energy_kcal': 300.0,
        'carbohydrate_g': null,
        'sugars_g': null,
        'dietary_fiber_g': null,
        'protein_g': null,
        'fat_g': null,
        'sodium_mg': null,
      },
    });
    await tester.pumpWidget(_wrap(MealHistoryScreen(api: _StubApi(meals: [meal]))));
    await tester.pumpAndSettle();
    // The subtitle contains "Breakfast" and "300 kcal" separated by ·
    expect(find.textContaining('Breakfast'), findsOneWidget);
    expect(find.textContaining('300 kcal'), findsOneWidget);
  });

  testWidgets('shows error and retry button on failure', (tester) async {
    await tester.pumpWidget(
        _wrap(MealHistoryScreen(api: _StubApi(throwError: true))));
    await tester.pumpAndSettle();
    expect(find.text('Retry'), findsOneWidget);
  });
}
