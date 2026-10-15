import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/meal_history/data/meal_history_models.dart';

void main() {
  group('FoodResult.fromJson', () {
    test('parses required fields', () {
      final f = FoodResult.fromJson({
        'id': 1,
        'name': 'Rice',
        'name_si': null,
        'name_ta': null,
        'category': 'Cereals',
        'source': 'MRI_SL_FCDB',
        'per_100g': {
          'energy_kcal': 130.0,
          'carbohydrate_g': 28.2,
          'sugars_g': null,
          'dietary_fiber_g': 0.4,
          'protein_g': 2.7,
          'fat_g': 0.3,
          'sodium_mg': 1.0,
        },
      });
      expect(f.id, 1);
      expect(f.name, 'Rice');
      expect(f.per100g.energyKcal, 130.0);
      expect(f.per100g.sugarsG, isNull);
    });
  });

  group('MealOut.fromJson', () {
    test('parses meal with items', () {
      final m = MealOut.fromJson({
        'id': 5,
        'eaten_at': '2026-10-16T08:00:00+05:30',
        'meal_type': 'breakfast',
        'note': null,
        'items': [
          {
            'id': 10,
            'food_id': 1,
            'name': 'Rice',
            'grams': 150.0,
            'nutrients': {
              'energy_kcal': 195.0,
              'carbohydrate_g': 42.3,
              'sugars_g': null,
              'dietary_fiber_g': 0.6,
              'protein_g': 4.1,
              'fat_g': 0.5,
              'sodium_mg': 1.5,
            },
          }
        ],
        'totals': {
          'energy_kcal': 195.0,
          'carbohydrate_g': 42.3,
          'sugars_g': null,
          'dietary_fiber_g': 0.6,
          'protein_g': 4.1,
          'fat_g': 0.5,
          'sodium_mg': 1.5,
        },
      });
      expect(m.id, 5);
      expect(m.mealType, MealType.breakfast);
      expect(m.items.length, 1);
      expect(m.items.first.name, 'Rice');
      expect(m.totals.energyKcal, 195.0);
      expect(m.totals.sugarsG, isNull);
    });

    test('unknown meal_type parsed as null', () {
      final m = MealOut.fromJson({
        'id': 1,
        'eaten_at': '2026-10-16T08:00:00Z',
        'meal_type': null,
        'note': null,
        'items': [],
        'totals': {
          'energy_kcal': null,
          'carbohydrate_g': null,
          'sugars_g': null,
          'dietary_fiber_g': null,
          'protein_g': null,
          'fat_g': null,
          'sodium_mg': null,
        },
      });
      expect(m.mealType, isNull);
    });
  });

  group('MealCreate.toJson', () {
    test('food_id item', () {
      final c = MealCreate(
        mealType: MealType.lunch,
        items: [MealItemIn.fromFood(foodId: 3, grams: 200)],
      );
      final j = c.toJson();
      expect(j['meal_type'], 'lunch');
      expect((j['items'] as List).first['food_id'], 3);
    });

    test('free item with no nutrients', () {
      final c = MealCreate(
        items: [MealItemIn.free(name: 'Hoppers', grams: 80)],
      );
      final j = c.toJson();
      final item = (j['items'] as List).first as Map<String, dynamic>;
      expect(item['name'], 'Hoppers');
      expect(item.containsKey('nutrients'), isFalse);
    });
  });

  group('DailySummary.fromJson', () {
    test('parses day and meal_count', () {
      final s = DailySummary.fromJson({
        'day': '2026-10-16',
        'meal_count': 2,
        'totals': {
          'energy_kcal': 400.0,
          'carbohydrate_g': null,
          'sugars_g': null,
          'dietary_fiber_g': null,
          'protein_g': null,
          'fat_g': null,
          'sodium_mg': null,
        },
        'meals': [],
      });
      expect(s.mealCount, 2);
      expect(s.totals.energyKcal, 400.0);
    });
  });
}
