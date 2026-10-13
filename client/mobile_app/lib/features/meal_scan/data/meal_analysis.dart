/// Models for the C1 response of `POST /api/v1/meals/analyze`.
///
/// The response also carries model-confidence fields (`items[].confidence`,
/// `items[].portion.confidence`). They are for C2/C3 only, so they are deliberately not
/// parsed here: the patient-facing UI must never show model confidence.
library;

enum MealType {
  breakfast('Breakfast'),
  lunch('Lunch'),
  dinner('Dinner'),
  snack('Snack');

  const MealType(this.label);

  final String label;

  /// Value sent to the API (lower case).
  String get apiValue => name;
}

/// Nutrient amounts. `null` means "not available", never zero.
class NutrientProfile {
  const NutrientProfile({
    this.energyKcal,
    this.carbohydrateG,
    this.sugarsG,
    this.dietaryFiberG,
    this.proteinG,
    this.fatG,
    this.sodiumMg,
  });

  factory NutrientProfile.fromJson(Map<String, dynamic> json) {
    return NutrientProfile(
      energyKcal: _toDouble(json['energy_kcal']),
      carbohydrateG: _toDouble(json['carbohydrate_g']),
      sugarsG: _toDouble(json['sugars_g']),
      dietaryFiberG: _toDouble(json['dietary_fiber_g']),
      proteinG: _toDouble(json['protein_g']),
      fatG: _toDouble(json['fat_g']),
      sodiumMg: _toDouble(json['sodium_mg']),
    );
  }

  /// Sums [profiles] per nutrient. Like the server, a total is `null` if that nutrient is
  /// unknown for any profile. An empty list gives all zeros.
  factory NutrientProfile.sum(List<NutrientProfile> profiles) {
    double? total(double? Function(NutrientProfile p) pick) {
      var sum = 0.0;
      for (final profile in profiles) {
        final value = pick(profile);
        if (value == null) return null;
        sum += value;
      }
      return sum;
    }

    return NutrientProfile(
      energyKcal: total((p) => p.energyKcal),
      carbohydrateG: total((p) => p.carbohydrateG),
      sugarsG: total((p) => p.sugarsG),
      dietaryFiberG: total((p) => p.dietaryFiberG),
      proteinG: total((p) => p.proteinG),
      fatG: total((p) => p.fatG),
      sodiumMg: total((p) => p.sodiumMg),
    );
  }

  final double? energyKcal;
  final double? carbohydrateG;
  final double? sugarsG;
  final double? dietaryFiberG;
  final double? proteinG;
  final double? fatG;
  final double? sodiumMg;
}

class Portion {
  const Portion({required this.grams, this.householdMeasure, required this.estimationMethod});

  factory Portion.fromJson(Map<String, dynamic> json) {
    return Portion(
      grams: _toDouble(json['grams']) ?? 0,
      householdMeasure: json['household_measure'] as String?,
      estimationMethod: json['estimation_method'] as String? ?? 'unknown',
    );
  }

  final double grams;
  final String? householdMeasure;
  final String estimationMethod;
}

class FoodItem {
  const FoodItem({
    required this.itemId,
    required this.label,
    required this.portion,
    required this.nutrition,
    this.nutritionSource,
  });

  factory FoodItem.fromJson(Map<String, dynamic> json) {
    final source = json['nutrition_source'] as Map<String, dynamic>?;
    return FoodItem(
      itemId: json['item_id'] as String,
      label: json['label'] as String,
      portion: Portion.fromJson(json['portion'] as Map<String, dynamic>),
      nutrition: NutrientProfile.fromJson(json['nutrition'] as Map<String, dynamic>),
      nutritionSource: source?['source'] as String?,
    );
  }

  final String itemId;
  final String label;
  final Portion portion;
  final NutrientProfile nutrition;

  /// `MRI_SL_FCDB`, `USDA_FDC` or `MOCK`.
  final String? nutritionSource;
}

class MealAnalysis {
  const MealAnalysis({
    required this.analysisId,
    required this.isMock,
    required this.items,
    required this.totals,
    required this.disclaimer,
    this.mealType,
  });

  factory MealAnalysis.fromJson(Map<String, dynamic> json) {
    final meta = json['meta'] as Map<String, dynamic>;
    final metadata = json['metadata'] as Map<String, dynamic>?;
    final mealType = metadata?['meal_type'] as String?;
    return MealAnalysis(
      analysisId: json['analysis_id'] as String,
      isMock: meta['is_mock'] as bool,
      items: [
        for (final item in json['items'] as List<dynamic>)
          FoodItem.fromJson(item as Map<String, dynamic>),
      ],
      totals: NutrientProfile.fromJson(json['totals'] as Map<String, dynamic>),
      disclaimer: json['disclaimer'] as String? ?? '',
      mealType: MealType.values.where((t) => t.apiValue == mealType).firstOrNull,
    );
  }

  final String analysisId;
  final bool isMock;
  final List<FoodItem> items;
  final NutrientProfile totals;
  final String disclaimer;
  final MealType? mealType;
}

double? _toDouble(Object? value) => value is num ? value.toDouble() : null;
