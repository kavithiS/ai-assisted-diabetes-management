import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/meal_history/data/meal_history_api.dart';
import 'package:mobile_app/features/meal_history/data/meal_history_models.dart';
import 'package:mobile_app/features/meal_history/today_summary_screen.dart';

class _StubApi implements MealHistoryApi {
  _StubApi({required this.summary, this.throwError = false});

  final DailySummary summary;
  final bool throwError;

  @override
  Future<DailySummary> dailySummary(DateTime day,
      {int utcOffsetMinutes = 0}) async {
    if (throwError) throw const MealHistoryException('ERR', 500);
    return summary;
  }

  @override
  dynamic noSuchMethod(Invocation i) => super.noSuchMethod(i);
}

DailySummary _emptySummary() => DailySummary.fromJson({
      'day': '2026-10-16',
      'meal_count': 0,
      'totals': {
        'energy_kcal': null,
        'carbohydrate_g': null,
        'sugars_g': null,
        'dietary_fiber_g': null,
        'protein_g': null,
        'fat_g': null,
        'sodium_mg': null,
      },
      'meals': [],
    });

Widget _wrap(Widget child) => MaterialApp(home: child);

void main() {
  testWidgets('shows spinner while loading', (tester) async {
    await tester.pumpWidget(_wrap(TodaySummaryScreen(api: _StubApi(summary: _emptySummary()))));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('shows zero meals message on empty day', (tester) async {
    await tester.pumpWidget(_wrap(TodaySummaryScreen(api: _StubApi(summary: _emptySummary()))));
    await tester.pumpAndSettle();
    expect(find.text('No meals logged today.'), findsOneWidget);
  });

  testWidgets('shows meal count in summary card', (tester) async {
    final summary = DailySummary.fromJson({
      'day': '2026-10-16',
      'meal_count': 3,
      'totals': {
        'energy_kcal': 1800.0,
        'carbohydrate_g': null,
        'sugars_g': null,
        'dietary_fiber_g': null,
        'protein_g': null,
        'fat_g': null,
        'sodium_mg': null,
      },
      'meals': [],
    });
    await tester.pumpWidget(_wrap(TodaySummaryScreen(api: _StubApi(summary: summary))));
    await tester.pumpAndSettle();
    expect(find.text('3 meals logged'), findsOneWidget);
  });

  testWidgets('shows retry on error', (tester) async {
    await tester.pumpWidget(
        _wrap(TodaySummaryScreen(api: _StubApi(summary: _emptySummary(), throwError: true))));
    await tester.pumpAndSettle();
    expect(find.text('Retry'), findsOneWidget);
  });
}
