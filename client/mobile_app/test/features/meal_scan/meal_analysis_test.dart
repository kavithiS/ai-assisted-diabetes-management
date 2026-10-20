import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/meal_scan/data/meal_analysis.dart';

import 'meal_scan_test_data.dart';

void main() {
  FoodItem foodA() => MealAnalysis.fromJson(mockAnalysisJson()).items.first;

  test('scale multiplies known nutrients and keeps unknown ones null', () {
    const profile =
        NutrientProfile(energyKcal: 200, carbohydrateG: 40, sugarsG: null);
    final scaled = profile.scale(1.5);

    expect(scaled.energyKcal, 300);
    expect(scaled.carbohydrateG, 60);
    expect(scaled.sugarsG, isNull);
  });

  test('empty meal totals stay unknown', () {
    final totals = NutrientProfile.sum([]);
    expect(totals.energyKcal, isNull);
    expect(totals.carbohydrateG, isNull);
    expect(totals.dietaryFiberG, isNull);
  });

  test('reported subtotal adds known values without filling unknowns with zero',
      () {
    const profiles = [
      NutrientProfile(energyKcal: 200, carbohydrateG: 40, sugarsG: null),
      NutrientProfile(energyKcal: null, carbohydrateG: null, sugarsG: null),
    ];
    final full = NutrientProfile.sum(profiles);
    final reported = NutrientProfile.sumAvailable(profiles);

    expect(full.energyKcal, isNull);
    expect(full.carbohydrateG, isNull);
    expect(reported.energyKcal, 200);
    expect(reported.carbohydrateG, 40);
    expect(reported.sugarsG, isNull);
    expect(NutrientProfile.sumAvailable([]).energyKcal, isNull);
  });

  test('analysis parses nutrition warnings without model confidence', () {
    final json = mockAnalysisJson();
    (json['meta'] as Map<String, dynamic>)['warnings'] = [
      "'bean_curry': nutrition from table entry SL_70 (close match: Beans Curry)",
    ];
    final analysis = MealAnalysis.fromJson(json);
    expect(analysis.warnings, hasLength(1));
    expect(analysis.warnings.single, contains('close match'));
    expect(analysis.items.first.nutritionSource, 'MOCK');
  });

  test('distinguishes trained recognition from placeholder portions', () {
    final json = mockAnalysisJson();
    (json['meta'] as Map<String, dynamic>)['model_name'] =
        'mobilenet_v3_large-multilabel';

    final analysis = MealAnalysis.fromJson(json);

    expect(analysis.isMock, isTrue);
    expect(analysis.recognitionIsMock, isFalse);
    expect(analysis.hasPlaceholderPortions, isTrue);
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
