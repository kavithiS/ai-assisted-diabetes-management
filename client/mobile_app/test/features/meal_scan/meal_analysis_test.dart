import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/meal_scan/data/meal_analysis.dart';

import 'meal_scan_test_data.dart';

void main() {
  FoodItem foodA() => MealAnalysis.fromJson(mockAnalysisJson()).items.first;

  test('scale multiplies known nutrients and keeps unknown ones null', () {
    const profile = NutrientProfile(energyKcal: 200, carbohydrateG: 40, sugarsG: null);
    final scaled = profile.scale(1.5);

    expect(scaled.energyKcal, 300);
    expect(scaled.carbohydrateG, 60);
    expect(scaled.sugarsG, isNull);
  });

  test('withGrams rescales nutrients and marks the portion as edited', () {
    final item = foodA(); // 150 g, 200 kcal, sugars unknown
    final edited = item.withGrams(300);

    expect(edited.portion.grams, 300);
    expect(edited.portion.isUserEdited, isTrue);
    expect(edited.portion.estimationMethod, 'user_edited');
    expect(edited.portion.householdMeasure, isNull);
    expect(edited.nutrition.energyKcal, 400);
    expect(edited.nutrition.carbohydrateG, 80);
    expect(edited.nutrition.sugarsG, isNull);
    expect(edited.itemId, item.itemId);
    expect(edited.label, item.label);
    expect(edited.nutritionSource, item.nutritionSource);
  });

  test('editing twice scales from the current portion', () {
    final edited = foodA().withGrams(300).withGrams(75);

    expect(edited.portion.grams, 75);
    expect(edited.nutrition.energyKcal, 100);
  });

  test('a 0 g portion cannot be rescaled', () {
    final json = mockAnalysisJson();
    (json['items'] as List).first['portion']['grams'] = 0.0;
    final item = MealAnalysis.fromJson(json).items.first;

    expect(item.canEditPortion, isFalse);
    expect(() => item.withGrams(100), throwsStateError);
  });
}
