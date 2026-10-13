import 'package:flutter/material.dart';

import '../data/meal_analysis.dart';
import '../meal_scan_style.dart';
import 'portion_edit_dialog.dart';

/// Shows the detected foods and meal totals. The patient can remove wrongly detected foods
/// and correct portion sizes; totals are then summed again from the current items.
///
/// Model confidence is never shown here (team rule).
class MealResultView extends StatefulWidget {
  const MealResultView({super.key, required this.analysis, required this.onScanAgain});

  final MealAnalysis analysis;
  final VoidCallback onScanAgain;

  @override
  State<MealResultView> createState() => _MealResultViewState();
}

class _MealResultViewState extends State<MealResultView> {
  late List<FoodItem> _items = List.of(widget.analysis.items);

  /// Until the patient changes something, show the server's totals as they are.
  bool _edited = false;

  NutrientProfile get _totals =>
      _edited ? NutrientProfile.sum([for (final item in _items) item.nutrition]) : widget.analysis.totals;

  void _remove(FoodItem item) {
    setState(() {
      _items = List.of(_items)..remove(item);
      _edited = true;
    });
  }

  Future<void> _editPortion(FoodItem item) async {
    final grams = await showPortionEditDialog(context, item);
    if (grams == null || !mounted) return;
    final index = _items.indexOf(item);
    if (index < 0) return;
    setState(() {
      _items = List.of(_items)..[index] = item.withGrams(grams);
      _edited = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final analysis = widget.analysis;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (analysis.isMock) ...[
          const _MockBanner(),
          const SizedBox(height: 12),
        ],
        _SectionTitle(
          analysis.mealType == null ? 'Detected foods' : 'Detected foods · ${analysis.mealType!.label}',
        ),
        const SizedBox(height: 8),
        if (_items.isEmpty)
          const _EmptyItems()
        else
          for (final item in _items) ...[
            _FoodItemCard(
              item: item,
              onEdit: item.canEditPortion ? () => _editPortion(item) : null,
              onRemove: () => _remove(item),
            ),
            const SizedBox(height: 8),
          ],
        const SizedBox(height: 8),
        const _SectionTitle('Estimated meal totals'),
        const SizedBox(height: 8),
        _TotalsCard(totals: _totals),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          style: MealScanStyle.secondaryButton(),
          onPressed: widget.onScanAgain,
          icon: const Icon(Icons.camera_alt_outlined),
          label: const Text('Scan another meal'),
        ),
        const SizedBox(height: 16),
        Text(
          analysis.disclaimer,
          style: const TextStyle(fontSize: 12, color: MealScanStyle.textSecondary),
        ),
      ],
    );
  }
}

class _MockBanner extends StatelessWidget {
  const _MockBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: MealScanStyle.warningTint,
        borderRadius: BorderRadius.circular(MealScanStyle.controlRadius),
        border: Border.all(color: MealScanStyle.warning),
      ),
      child: const Row(
        children: [
          Icon(Icons.info_outline, color: MealScanStyle.warning),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Demo data: these foods and values are placeholders, not real nutrition data.',
              style: TextStyle(color: MealScanStyle.text),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: MealScanStyle.text,
      ),
    );
  }
}

class _EmptyItems extends StatelessWidget {
  const _EmptyItems();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: MealScanStyle.cardDecoration(),
      child: const Text(
        'No foods left. Scan the meal again to start over.',
        style: TextStyle(color: MealScanStyle.textSecondary),
      ),
    );
  }
}

class _FoodItemCard extends StatelessWidget {
  const _FoodItemCard({required this.item, required this.onEdit, required this.onRemove});

  final FoodItem item;

  /// `null` when the portion can't be rescaled (0 g); the edit button is then hidden.
  final VoidCallback? onEdit;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final portion = item.portion;
    final measure = portion.householdMeasure == null ? '' : ' (${portion.householdMeasure})';
    final amount = portion.isUserEdited
        ? '${formatAmount(portion.grams)} g (edited)'
        : 'About ${formatAmount(portion.grams)} g$measure';
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 4, 12),
      decoration: MealScanStyle.cardDecoration(),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.label,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: MealScanStyle.text,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '$amount · ${formatNutrient(item.nutrition.energyKcal, 'kcal')}',
                  style: const TextStyle(color: MealScanStyle.textSecondary),
                ),
                const SizedBox(height: 2),
                Text(
                  'Source: ${sourceLabel(item.nutritionSource)}',
                  style: const TextStyle(fontSize: 12, color: MealScanStyle.textSecondary),
                ),
              ],
            ),
          ),
          if (onEdit != null)
            IconButton(
              tooltip: 'Edit portion of ${item.label}',
              onPressed: onEdit,
              icon: const Icon(Icons.edit_outlined, color: MealScanStyle.textSecondary),
            ),
          IconButton(
            tooltip: 'Remove ${item.label}',
            onPressed: onRemove,
            icon: const Icon(Icons.close, color: MealScanStyle.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _TotalsCard extends StatelessWidget {
  const _TotalsCard({required this.totals});

  final NutrientProfile totals;

  @override
  Widget build(BuildContext context) {
    final rows = <(String, double?, String)>[
      ('Energy', totals.energyKcal, 'kcal'),
      ('Carbohydrate', totals.carbohydrateG, 'g'),
      ('Protein', totals.proteinG, 'g'),
      ('Fat', totals.fatG, 'g'),
      ('Sugars', totals.sugarsG, 'g'),
      ('Dietary fibre', totals.dietaryFiberG, 'g'),
      ('Sodium', totals.sodiumMg, 'mg'),
    ];
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: MealScanStyle.cardDecoration(),
      child: Column(
        children: [
          for (final (name, value, unit) in rows)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: [
                  Expanded(
                    child: Text(name, style: const TextStyle(color: MealScanStyle.text)),
                  ),
                  Text(
                    formatNutrient(value, unit),
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: value == null ? MealScanStyle.textSecondary : MealScanStyle.text,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

/// `null` means the value is unknown; it is never shown as zero.
String formatNutrient(double? value, String unit) =>
    value == null ? 'Not available' : '${formatAmount(value)} $unit';

String formatAmount(double value) =>
    value >= 10 || value == value.roundToDouble() ? value.toStringAsFixed(0) : value.toStringAsFixed(1);

String sourceLabel(String? source) {
  switch (source) {
    case 'MRI_SL_FCDB':
      return 'Sri Lanka food composition database (MRI)';
    case 'USDA_FDC':
      return 'USDA FoodData Central';
    case 'MOCK':
      return 'Placeholder (demo data)';
    default:
      return 'Not available';
  }
}
