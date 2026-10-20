import 'package:flutter/material.dart';

import '../../meal_scan/data/meal_analysis.dart';

/// Displays a [NutrientProfile] as a table of label / value rows.
class NutrientTable extends StatelessWidget {
  const NutrientTable(
    this.nutrients, {
    super.key,
    this.color,
    this.mutedColor,
  });

  final NutrientProfile nutrients;
  final Color? color;
  final Color? mutedColor;

  @override
  Widget build(BuildContext context) {
    final rows = [
      _Row('Energy', nutrients.energyKcal, 'kcal'),
      _Row('Carbohydrate', nutrients.carbohydrateG, 'g'),
      _Row('Dietary fibre', nutrients.dietaryFiberG, 'g'),
      _Row('Protein', nutrients.proteinG, 'g'),
      _Row('Fat', nutrients.fatG, 'g'),
      _Row('Sodium', nutrients.sodiumMg, 'mg'),
    ];
    return Column(
      children: [
        for (final r in rows)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Row(
              children: [
                Expanded(child: Text(r.label, style: TextStyle(color: color))),
                Text(
                  r.value == null
                      ? 'Not available'
                      : '${r.value!.toStringAsFixed(1)} ${r.unit}',
                  style: TextStyle(
                    color: r.value == null
                        ? mutedColor ?? Theme.of(context).colorScheme.outline
                        : color,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _Row {
  const _Row(this.label, this.value, this.unit);
  final String label;
  final double? value;
  final String unit;
}
