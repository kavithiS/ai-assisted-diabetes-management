/// Models for the meal history and food search endpoints.
///
/// Maps GET/POST/DELETE /v1/meals, GET /v1/meals/summary, GET /v1/foods.
/// No model confidence is parsed here.
library;

import '../../meal_scan/data/meal_analysis.dart';

export '../../meal_scan/data/meal_analysis.dart' show MealType, NutrientProfile;

// ── Food search ──────────────────────────────────────────────────────────────

class FoodResult {
  const FoodResult({
    required this.id,
    required this.name,
    this.nameSi,
    this.nameTa,
    this.category,
    required this.source,
    required this.per100g,
  });

  factory FoodResult.fromJson(Map<String, dynamic> json) => FoodResult(
        id: json['id'] as int,
        name: json['name'] as String,
        nameSi: json['name_si'] as String?,
        nameTa: json['name_ta'] as String?,
        category: json['category'] as String?,
        source: json['source'] as String,
        per100g: NutrientProfile.fromJson(json['per_100g'] as Map<String, dynamic>),
      );

  final int id;
  final String name;
  final String? nameSi;
  final String? nameTa;
  final String? category;
  final String source;
  final NutrientProfile per100g;
}

// ── Meal history ─────────────────────────────────────────────────────────────

class MealItemOut {
  const MealItemOut({
    required this.id,
    this.foodId,
    required this.name,
    required this.grams,
    required this.nutrients,
  });

  factory MealItemOut.fromJson(Map<String, dynamic> json) => MealItemOut(
        id: json['id'] as int,
        foodId: json['food_id'] as int?,
        name: json['name'] as String,
        grams: (json['grams'] as num).toDouble(),
        nutrients: NutrientProfile.fromJson(json['nutrients'] as Map<String, dynamic>),
      );

  final int id;
  final int? foodId;
  final String name;
  final double grams;
  final NutrientProfile nutrients;
}

class MealOut {
  const MealOut({
    required this.id,
    required this.eatenAt,
    this.mealType,
    this.note,
    required this.items,
    required this.totals,
  });

  factory MealOut.fromJson(Map<String, dynamic> json) => MealOut(
        id: json['id'] as int,
        eatenAt: DateTime.parse(json['eaten_at'] as String),
        mealType: _parseMealType(json['meal_type'] as String?),
        note: json['note'] as String?,
        items: [
          for (final i in json['items'] as List<dynamic>)
            MealItemOut.fromJson(i as Map<String, dynamic>),
        ],
        totals: NutrientProfile.fromJson(json['totals'] as Map<String, dynamic>),
      );

  final int id;
  final DateTime eatenAt;
  final MealType? mealType;
  final String? note;
  final List<MealItemOut> items;
  final NutrientProfile totals;

  static MealType? _parseMealType(String? v) =>
      MealType.values.where((t) => t.apiValue == v).firstOrNull;
}

class DailySummary {
  const DailySummary({
    required this.day,
    required this.mealCount,
    required this.totals,
    required this.meals,
  });

  factory DailySummary.fromJson(Map<String, dynamic> json) => DailySummary(
        day: DateTime.parse(json['day'] as String),
        mealCount: json['meal_count'] as int,
        totals: NutrientProfile.fromJson(json['totals'] as Map<String, dynamic>),
        meals: [
          for (final m in json['meals'] as List<dynamic>)
            MealOut.fromJson(m as Map<String, dynamic>),
        ],
      );

  final DateTime day;
  final int mealCount;
  final NutrientProfile totals;
  final List<MealOut> meals;
}

// ── POST /v1/meals request ────────────────────────────────────────────────────

class MealItemIn {
  const MealItemIn.fromFood({required this.foodId, required this.grams})
      : name = null,
        nutrients = null;

  const MealItemIn.free({required this.name, required this.grams, this.nutrients})
      : foodId = null;

  final int? foodId;
  final String? name;
  final double grams;
  final NutrientProfile? nutrients;

  Map<String, dynamic> toJson() {
    if (foodId != null) return {'food_id': foodId, 'grams': grams};
    final m = <String, dynamic>{'name': name, 'grams': grams};
    if (nutrients != null) m['nutrients'] = _nutrientsToJson(nutrients!);
    return m;
  }

  static Map<String, dynamic> _nutrientsToJson(NutrientProfile n) => {
        'energy_kcal': n.energyKcal,
        'carbohydrate_g': n.carbohydrateG,
        'sugars_g': n.sugarsG,
        'dietary_fiber_g': n.dietaryFiberG,
        'protein_g': n.proteinG,
        'fat_g': n.fatG,
        'sodium_mg': n.sodiumMg,
      };
}

class MealCreate {
  const MealCreate({
    this.eatenAt,
    this.mealType,
    this.note,
    required this.items,
  });

  final DateTime? eatenAt;
  final MealType? mealType;
  final String? note;
  final List<MealItemIn> items;

  Map<String, dynamic> toJson() => {
        if (eatenAt != null) 'eaten_at': eatenAt!.toIso8601String(),
        if (mealType != null) 'meal_type': mealType!.apiValue,
        if (note != null) 'note': note,
        'items': [for (final i in items) i.toJson()],
      };
}
