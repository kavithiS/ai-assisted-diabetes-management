import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/meal_analysis.dart';
import '../meal_scan_style.dart';
import 'meal_result_view.dart' show formatAmount;

/// Upper bound for one food's portion. It only catches typing mistakes; it is not a
/// dietary limit.
const double maxPortionGrams = 2000;

/// Asks the patient for the grams of [item]. Returns `null` if they cancel.
Future<double?> showPortionEditDialog(BuildContext context, FoodItem item) {
  return showDialog<double>(
    context: context,
    builder: (_) => PortionEditDialog(item: item),
  );
}

class PortionEditDialog extends StatefulWidget {
  const PortionEditDialog({super.key, required this.item});

  final FoodItem item;

  @override
  State<PortionEditDialog> createState() => _PortionEditDialogState();
}

class _PortionEditDialogState extends State<PortionEditDialog> {
  late final TextEditingController _controller =
      TextEditingController(text: formatAmount(widget.item.portion.grams));
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _save() {
    final grams = double.tryParse(_controller.text.trim());
    final String? error;
    if (grams == null) {
      error = 'Enter the amount in grams, for example 150.';
    } else if (grams <= 0) {
      error = 'Enter an amount above 0 g. To take this food out, remove it instead.';
    } else if (grams > maxPortionGrams) {
      error = 'Enter an amount up to ${formatAmount(maxPortionGrams)} g.';
    } else {
      error = null;
    }
    if (error != null) {
      setState(() => _error = error);
      return;
    }
    Navigator.of(context).pop(grams);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Portion of ${widget.item.label}'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Change the amount if the estimate looks wrong. The nutrients are recalculated '
            'from the new amount.',
            style: TextStyle(color: MealScanStyle.textSecondary),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _controller,
            autofocus: true,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))],
            decoration: InputDecoration(
              labelText: 'Amount',
              suffixText: 'g',
              errorText: _error,
              errorMaxLines: 3,
            ),
            onSubmitted: (_) => _save(),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: MealScanStyle.primary),
          onPressed: _save,
          child: const Text('Save'),
        ),
      ],
    );
  }
}
