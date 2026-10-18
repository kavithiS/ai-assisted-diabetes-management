import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import 'glucose_models.dart';
import 'glucose_trajectory_chart.dart';

/// Shown above the form, so it is read before any estimate is requested.
const glucoseDisclaimer =
    'Research prototype only. These estimates are not medical advice and must not be '
    'used for diagnosis, treatment or insulin dosing.';

/// Repeated under the results, which the screen scrolls to after a forecast.
const glucoseResultsReminder =
    'Not for diagnosis, treatment or insulin dosing.';

/// Glucose (C2): four-hour glucose forecast from pre-meal glucose and the meal's nutrition.
class GlucoseScreen extends StatefulWidget {
  const GlucoseScreen({super.key, this.apiClient});

  /// Injected in tests. When null, the screen creates and owns its own client.
  final ApiClient? apiClient;

  @override
  State<GlucoseScreen> createState() => _GlucoseScreenState();
}

class _GlucoseScreenState extends State<GlucoseScreen> {
  final _formKey = GlobalKey<FormState>();

  /// Marks the results section so it can be scrolled into view once it is laid out.
  final _resultsKey = GlobalKey();
  final _premeal = TextEditingController();
  final _calories = TextEditingController();
  final _carbs = TextEditingController();
  final _protein = TextEditingController();
  final _fat = TextEditingController();
  final _fiber = TextEditingController();

  late final ApiClient _client = widget.apiClient ?? ApiClient();

  bool _loading = false;
  String? _error;
  GlucoseForecast? _forecast;

  @override
  void dispose() {
    for (final controller in [
      _premeal,
      _calories,
      _carbs,
      _protein,
      _fat,
      _fiber
    ]) {
      controller.dispose();
    }
    if (widget.apiClient == null) {
      _client.close();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() {
      _loading = true;
      _error = null;
      _forecast = null;
    });

    final request = GlucoseForecastRequest(
      premealGlucose: double.parse(_premeal.text.trim()),
      calories: double.parse(_calories.text.trim()),
      carbs: double.parse(_carbs.text.trim()),
      protein: double.parse(_protein.text.trim()),
      fat: double.parse(_fat.text.trim()),
      fiber: double.parse(_fiber.text.trim()),
    );

    try {
      final forecast = await _client.forecastGlucose(request);
      if (!mounted) return;
      setState(() => _forecast = forecast);
      _scrollToResults();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Estimate how your glucose may change over the next four hours after a meal.',
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 8),
              _buildDisclaimer(theme),
              const SizedBox(height: 16),
              _buildForm(theme),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _loading ? null : _submit,
                icon: _loading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.show_chart),
                label: Text(
                    _loading ? 'Getting estimate…' : 'Get 4-hour estimate'),
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                _buildError(theme, _error!),
              ],
              if (_forecast != null) ...[
                const SizedBox(height: 24),
                _buildResults(theme, _forecast!),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildForm(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Before your meal', style: theme.textTheme.titleMedium),
              const SizedBox(height: 12),
              _numberField(
                controller: _premeal,
                label: 'Current pre-meal glucose (mg/dL)',
                validator: validatePremealGlucose,
              ),
              const SizedBox(height: 16),
              Text('The meal', style: theme.textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                'Enter 0 for any nutrient that does not apply.',
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              _numberField(
                controller: _calories,
                label: 'Calories (kcal)',
                validator: (v) => validateNutrient(v, label: 'Calories'),
              ),
              const SizedBox(height: 12),
              _numberField(
                controller: _carbs,
                label: 'Carbohydrates (g)',
                validator: (v) => validateNutrient(v, label: 'Carbohydrates'),
              ),
              const SizedBox(height: 12),
              _numberField(
                controller: _protein,
                label: 'Protein (g)',
                validator: (v) => validateNutrient(v, label: 'Protein'),
              ),
              const SizedBox(height: 12),
              _numberField(
                controller: _fat,
                label: 'Fat (g)',
                validator: (v) => validateNutrient(v, label: 'Fat'),
              ),
              const SizedBox(height: 12),
              _numberField(
                controller: _fiber,
                label: 'Fibre (g)',
                validator: (v) => validateNutrient(v, label: 'Fibre'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _numberField({
    required TextEditingController controller,
    required String label,
    required String? Function(String?) validator,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration:
          InputDecoration(labelText: label, border: const OutlineInputBorder()),
      validator: validator,
      autovalidateMode: AutovalidateMode.onUserInteraction,
    );
  }

  Widget _buildDisclaimer(ThemeData theme) {
    return Card(
      color: theme.colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.info_outline,
                color: theme.colorScheme.onSecondaryContainer),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                glucoseDisclaimer,
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.onSecondaryContainer),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildError(ThemeData theme, String message) {
    return Card(
      color: theme.colorScheme.errorContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.error_outline,
                color: theme.colorScheme.onErrorContainer),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                message,
                style: TextStyle(color: theme.colorScheme.onErrorContainer),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// The results render below the form, usually off-screen, so bring them into
  /// view. Runs after the next frame, when the results section has been laid out.
  void _scrollToResults() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final resultsContext = _resultsKey.currentContext;
      if (!mounted || resultsContext == null) return;
      Scrollable.ensureVisible(
        resultsContext,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    });
  }

  Widget _buildResults(ThemeData theme, GlucoseForecast forecast) {
    return Column(
      key: _resultsKey,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Estimated glucose, next 4 hours',
            style: theme.textTheme.titleMedium),
        const SizedBox(height: 4),
        Text(
          'Estimate only. Values are rounded to whole mg/dL.',
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(height: 12),
        Card(
          child: ListTile(
            leading: Icon(Icons.trending_up, color: theme.colorScheme.tertiary),
            title: Text(
              'Highest estimate: ${forecast.peakGlucose.round()} ${forecast.unit}',
              style: theme.textTheme.titleSmall,
            ),
            subtitle: Text(
                'At +${_formatHorizon(forecast.peakMinutes)} after the meal'),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
            child: GlucoseTrajectoryChart(
              predictions: forecast.predictions,
              horizonMinutes: forecast.horizonMinutes,
              peakIndex: forecast.peakIndex,
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Column(
            children: [
              for (var i = 0; i < forecast.predictions.length; i++)
                ListTile(
                  dense: true,
                  title: Text('+${_formatHorizon(forecast.horizonMinutes[i])}'),
                  trailing: Text(
                    '${forecast.predictions[i].round()} ${forecast.unit}',
                    style: theme.textTheme.bodyLarge
                        ?.copyWith(fontWeight: FontWeight.w600),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Text(glucoseResultsReminder,
            style: theme.textTheme.bodySmall
                ?.copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        Text(forecast.disclaimer, style: theme.textTheme.bodySmall),
        const SizedBox(height: 4),
        Text(
          'Model: ${forecast.modelName} (${forecast.modelVersion})',
          style: theme.textTheme.bodySmall,
        ),
      ],
    );
  }

  String _formatHorizon(int minutes) {
    if (minutes < 60) return '$minutes min';
    final hours = minutes ~/ 60;
    final rest = minutes % 60;
    return rest == 0 ? '${hours}h' : '${hours}h ${rest}min';
  }
}
