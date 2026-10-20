import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import 'dietary_risk_models.dart';
import 'glucose_models.dart';
import 'glucose_session.dart';

/// Shown with every result, so it is never read as a diagnosis.
const dietaryRiskDisclaimer =
    'Research estimate only. Not a diagnosis or a clinically validated '
    'dietary-risk rating.';

/// Explains what the trajectory metrics mean. Describes the forecast only.
const dietaryRiskExplanation =
    'The predicted peak is the highest value in the 4-hour forecast. The metrics '
    'show how far and how quickly the forecast curve rises above your pre-meal '
    'glucose. The area above pre-meal glucose summarises the total rise over four '
    'hours. They describe the forecast curve only, not how healthy the meal is.';

/// Data limitation shown with every result.
const dietaryRiskDataNote =
    'Estimates come from a research model trained on CGMacros data, not a Sri '
    'Lankan clinical validation cohort.';

/// Lists what the reference design showed but this implementation does not use.
const dietaryRiskNotIncludedNote =
    'Not included: glycaemic index (GI), glycaemic load (GL), cumulative daily '
    'carbohydrates, meal timing and activity. The CGMacros training data has no '
    'Sri Lankan meal identities or GI/GL values, and a composite dietary risk '
    'score has not been implemented.';

const dietaryRiskNoInputsMessage =
    'Enter your pre-meal glucose and the meal on the 4-hour forecast tab. '
    'This page uses the same values.';

const dietaryRiskNoForecastMessage =
    'Get the 4-hour estimate for the meal you entered first. This page then '
    'assesses the same meal.';

const dietaryRiskStaleMessage =
    'You changed the meal details. These results are for the previous values. '
    'Assess the meal again to update them.';

// Colours from the reference design. Teal comes from the app theme.
const _pageBackground = Color(0xFFF4F7F7);
const _cardBorder = Color(0xFFE2E8EA);
const _mutedText = Color(0xFF5F6B6D);
const _navy = Color(0xFF1B2A41);
const _barTrack = Color(0xFFE3E9EA);
const _amber = Color(0xFFD9822B);
const _amberSoft = Color(0xFFFFF1DC);
const _tealSoft = Color(0xFFE6F4F2);

/// Libre sensor range in the CGMacros data dictionary; used to scale the peak bar.
const _sensorMin = 40.0;
const _sensorMax = 400.0;
const _threshold = 180.0;

/// Dynamic Dietary Risk (C2): the research-defined "above 180 mg/dL within
/// 4 hours" indicator and the predicted glucose response for the meal entered
/// on the 4-hour forecast tab. Every value shown comes from the API or from the
/// user's own inputs; nothing is hardcoded.
class DietaryRiskScreen extends StatefulWidget {
  const DietaryRiskScreen({super.key, required this.session, this.apiClient});

  /// Inputs and results shared with the 4-hour forecast page.
  final GlucoseSession session;

  /// Injected in tests. When null, the screen creates and owns its own client.
  final ApiClient? apiClient;

  @override
  State<DietaryRiskScreen> createState() => _DietaryRiskScreenState();
}

class _DietaryRiskScreenState extends State<DietaryRiskScreen> {
  late final ApiClient _client = widget.apiClient ?? ApiClient();

  @override
  void dispose() {
    if (widget.apiClient == null) _client.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.session,
      builder: (context, _) => _buildPage(context),
    );
  }

  Widget _buildPage(BuildContext context) {
    final theme = Theme.of(context);
    final session = widget.session;
    final assessment = session.assessment;
    final hasInputs = session.currentRequest != null;

    return ColoredBox(
      color: _pageBackground,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 600),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Dynamic Dietary Risk',
                  style: theme.textTheme.headlineSmall
                      ?.copyWith(fontWeight: FontWeight.w800, color: _navy),
                ),
                const SizedBox(height: 4),
                Text(
                  'Post-meal glucose response for the meal on the 4-hour '
                  'forecast tab.',
                  style:
                      theme.textTheme.bodyMedium?.copyWith(color: _mutedText),
                ),
                const SizedBox(height: 16),
                if (!hasInputs)
                  _guidance(theme, dietaryRiskNoInputsMessage)
                else if (!session.hasCurrentForecast)
                  _guidance(theme, dietaryRiskNoForecastMessage)
                else
                  _assessButton(session),
                if (session.assessmentError != null) ...[
                  const SizedBox(height: 16),
                  _errorCard(theme, session.assessmentError!),
                ],
                if (assessment != null) ...[
                  const SizedBox(height: 16),
                  if (session.assessmentIsStale) ...[
                    _staleCard(theme),
                    const SizedBox(height: 12),
                  ],
                  Opacity(
                    opacity: session.assessmentIsStale ? 0.55 : 1,
                    child:
                        _results(theme, assessment, session.assessmentRequest!),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  // --- states before results ---------------------------------------------------------

  Widget _guidance(ThemeData theme, String message) {
    final tabs = DefaultTabController.maybeOf(context);
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.edit_note, color: theme.colorScheme.primary),
              const SizedBox(width: 12),
              Expanded(child: Text(message)),
            ],
          ),
          if (tabs != null) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.tonalIcon(
                onPressed: () => tabs.animateTo(0),
                icon: const Icon(Icons.show_chart),
                label: const Text('Go to 4-hour forecast'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _assessButton(GlucoseSession session) {
    final loading = session.assessmentLoading;
    final label = loading
        ? 'Assessing meal…'
        : session.assessment == null
            ? 'Assess this meal'
            : 'Assess this meal again';
    return FilledButton.icon(
      onPressed: loading ? null : () => session.runAssessment(_client),
      style: FilledButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
      icon: loading
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.restaurant),
      label: Text(label),
    );
  }

  Widget _errorCard(ThemeData theme, String message) {
    return _card(
      color: theme.colorScheme.errorContainer,
      borderColor: theme.colorScheme.errorContainer,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.error_outline, color: theme.colorScheme.onErrorContainer),
          const SizedBox(width: 12),
          Expanded(
            child: Text(message,
                style: TextStyle(color: theme.colorScheme.onErrorContainer)),
          ),
        ],
      ),
    );
  }

  Widget _staleCard(ThemeData theme) {
    return _card(
      color: _amberSoft,
      borderColor: _amberSoft,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.update, color: _amber),
          const SizedBox(width: 12),
          Expanded(child: Text(dietaryRiskStaleMessage)),
        ],
      ),
    );
  }

  // --- results ----------------------------------------------------------------------

  Widget _results(ThemeData theme, DietaryRiskAssessment result,
      GlucoseForecastRequest inputs) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _summaryCard(theme, result.features, result.unit),
        const SizedBox(height: 24),
        _sectionLabel(theme, 'Dietary metrics'),
        const SizedBox(height: 8),
        _metricsCard(theme, result.features, result.unit),
        const SizedBox(height: 24),
        _sectionLabel(theme, "This meal's inputs"),
        const SizedBox(height: 8),
        _inputsCard(theme, inputs),
        const SizedBox(height: 24),
        _interpretationCard(theme, result),
      ],
    );
  }

  /// Predicted peak and timing from the trajectory features. No status badge.
  Widget _summaryCard(
      ThemeData theme, TrajectoryFeatures features, String unit) {
    final peak = features.predictedPeakGlucose;
    final peakFraction =
        ((peak - _sensorMin) / (_sensorMax - _sensorMin)).clamp(0.0, 1.0);
    const thresholdFraction =
        (_threshold - _sensorMin) / (_sensorMax - _sensorMin);
    final caption = theme.textTheme.bodySmall?.copyWith(color: _mutedText);
    return _card(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Predicted peak glucose',
              style: theme.textTheme.titleSmall
                  ?.copyWith(color: _mutedText, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Text.rich(
            TextSpan(children: [
              TextSpan(
                text: '${peak.round()}',
                style: theme.textTheme.displaySmall
                    ?.copyWith(color: _navy, fontWeight: FontWeight.w800),
              ),
              TextSpan(
                text: ' $unit',
                style: theme.textTheme.titleMedium
                    ?.copyWith(color: _mutedText, fontWeight: FontWeight.w600),
              ),
            ]),
          ),
          const SizedBox(height: 4),
          Text(
            'Reached ${_formatHorizon(features.predictedPeakMinutes)} after the meal',
            style: theme.textTheme.bodyMedium?.copyWith(color: _mutedText),
          ),
          const SizedBox(height: 14),
          _bar(
            color: peak > _threshold ? _amber : theme.colorScheme.primary,
            fraction: peakFraction,
            marker: thresholdFraction,
          ),
          const SizedBox(height: 6),
          Text('Scale 40–400 mg/dL (sensor range). Line marks 180 mg/dL.',
              style: caption),
          const SizedBox(height: 8),
          Text(
              'Research estimate. Not for diagnosis, treatment or insulin dosing.',
              style: caption),
        ],
      ),
    );
  }

  /// Supported trajectory metrics only. Bars appear just where the scale is known.
  Widget _metricsCard(
      ThemeData theme, TrajectoryFeatures features, String unit) {
    final timingFraction =
        (features.predictedPeakMinutes / 240).clamp(0.0, 1.0);
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _barRow(
            theme,
            label: 'Peak timing',
            value: '+${_formatHorizon(features.predictedPeakMinutes)}',
            fraction: timingFraction,
            color: theme.colorScheme.primary,
          ),
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 4),
            child: Text('Scale 0–4 hours after the meal.',
                style: theme.textTheme.bodySmall?.copyWith(color: _mutedText)),
          ),
          const Divider(height: 24, color: _cardBorder),
          _valueRow(theme, 'Change from pre-meal glucose',
              '${_signed(features.peakChangeFromPremeal.round())} $unit'),
          _valueRow(theme, 'Maximum predicted rise',
              '${features.maxRise.round()} $unit'),
          _valueRow(theme, 'Steepest rise rate',
              '${_signed1(features.maxRiseRate)} $unit per min'),
          _valueRow(theme, 'Area above pre-meal glucose',
              '${_grouped(features.predictedIauc.round())} $unit·min'),
        ],
      ),
    );
  }

  Widget _bar({
    required Color color,
    required double fraction,
    double? marker,
  }) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        return SizedBox(
          height: 12,
          child: Stack(
            alignment: Alignment.centerLeft,
            children: [
              Container(
                height: 8,
                decoration: BoxDecoration(
                    color: _barTrack, borderRadius: BorderRadius.circular(4)),
              ),
              Container(
                width: width * fraction,
                height: 8,
                decoration: BoxDecoration(
                    color: color, borderRadius: BorderRadius.circular(4)),
              ),
              if (marker != null)
                Positioned(
                  left: (width * marker - 1).clamp(0.0, width - 2),
                  child: Container(width: 2, height: 12, color: _navy),
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _inputsCard(ThemeData theme, GlucoseForecastRequest inputs) {
    final grams = inputs.carbs + inputs.protein + inputs.fat;
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _valueRow(theme, 'Pre-meal glucose',
              '${_number(inputs.premealGlucose)} mg/dL'),
          _valueRow(theme, 'Calories', '${_number(inputs.calories)} kcal'),
          _valueRow(theme, 'Carbohydrates', '${_number(inputs.carbs)} g'),
          _valueRow(theme, 'Protein', '${_number(inputs.protein)} g'),
          _valueRow(theme, 'Fat', '${_number(inputs.fat)} g'),
          _valueRow(theme, 'Fibre', '${_number(inputs.fiber)} g'),
          if (grams > 0) ...[
            const SizedBox(height: 12),
            Text('Carbohydrate, protein and fat by weight',
                style: theme.textTheme.bodySmall?.copyWith(color: _mutedText)),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: SizedBox(
                height: 8,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (final (value, color) in [
                      (inputs.carbs, theme.colorScheme.primary),
                      (inputs.protein, _amber),
                      (inputs.fat, _mutedText),
                    ])
                      if (value > 0)
                        Expanded(
                          flex: (value / grams * 1000).round().clamp(1, 1000),
                          child: ColoredBox(color: color),
                        ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 12,
              children: [
                _legend(theme, theme.colorScheme.primary, 'Carbohydrate'),
                _legend(theme, _amber, 'Protein'),
                _legend(theme, _mutedText, 'Fat'),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _interpretationCard(ThemeData theme, DietaryRiskAssessment result) {
    final small = theme.textTheme.bodySmall?.copyWith(color: _mutedText);

    return _card(
      color: _tealSoft,
      borderColor: theme.colorScheme.primary.withValues(alpha: 0.25),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_awesome,
                  size: 18, color: theme.colorScheme.primary),
              const SizedBox(width: 8),
              Text(
                'Risk Interpretation',
                style: theme.textTheme.titleSmall?.copyWith(
                    color: theme.colorScheme.primary,
                    fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(dietaryRiskExplanation, style: theme.textTheme.bodyMedium),
          const SizedBox(height: 10),
          Text(dietaryRiskDisclaimer,
              style: theme.textTheme.bodySmall
                  ?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Text(dietaryRiskDataNote, style: theme.textTheme.bodySmall),
          const SizedBox(height: 6),
          Text(dietaryRiskNotIncludedNote, style: theme.textTheme.bodySmall),
          const SizedBox(height: 10),
          Text(
            'Forecast model: ${result.forecastModelName} '
            '(${result.forecastModelVersion}).',
            style: small,
          ),
          const SizedBox(height: 4),
          Text(result.disclaimer, style: small),
        ],
      ),
    );
  }

  // --- building blocks --------------------------------------------------------------

  Widget _card({
    required Widget child,
    Color color = Colors.white,
    Color borderColor = _cardBorder,
    EdgeInsets padding = const EdgeInsets.all(16),
  }) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: borderColor),
      ),
      child: child,
    );
  }

  Widget _sectionLabel(ThemeData theme, String text) {
    return Text(
      text.toUpperCase(),
      style: theme.textTheme.labelLarge?.copyWith(
          color: _mutedText, letterSpacing: 1.1, fontWeight: FontWeight.w700),
    );
  }

  Widget _valueRow(ThemeData theme, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: Text(label, style: theme.textTheme.bodyLarge)),
          const SizedBox(width: 12),
          Text(value,
              style: theme.textTheme.bodyLarge?.copyWith(color: _mutedText)),
        ],
      ),
    );
  }

  Widget _barRow(
    ThemeData theme, {
    required String label,
    required String value,
    required double fraction,
    required Color color,
    double? marker,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _valueRow(theme, label, value),
        const SizedBox(height: 2),
        LayoutBuilder(
          builder: (context, constraints) {
            final width = constraints.maxWidth;
            return SizedBox(
              height: 12,
              child: Stack(
                alignment: Alignment.centerLeft,
                children: [
                  Container(
                    height: 6,
                    decoration: BoxDecoration(
                        color: _barTrack,
                        borderRadius: BorderRadius.circular(3)),
                  ),
                  Container(
                    width: width * fraction,
                    height: 6,
                    decoration: BoxDecoration(
                        color: color, borderRadius: BorderRadius.circular(3)),
                  ),
                  if (marker != null)
                    Positioned(
                      left: (width * marker - 1).clamp(0.0, width - 2),
                      child: Container(
                          width: 2, height: 12, color: Colors.black87),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }

  Widget _legend(ThemeData theme, Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text(label, style: theme.textTheme.bodySmall),
      ],
    );
  }

  static String _number(double value) => value == value.roundToDouble()
      ? value.round().toString()
      : value.toStringAsFixed(1);

  static String _signed(int value) => value > 0 ? '+$value' : '$value';

  static String _signed1(double value) {
    final text = value.toStringAsFixed(1);
    return value > 0 && text != '0.0' ? '+$text' : text;
  }

  static String _grouped(int value) {
    final digits = value.abs().toString();
    final buffer = StringBuffer(value < 0 ? '-' : '');
    for (var i = 0; i < digits.length; i++) {
      if (i > 0 && (digits.length - i) % 3 == 0) buffer.write(',');
      buffer.write(digits[i]);
    }
    return buffer.toString();
  }

  static String _formatHorizon(int minutes) {
    if (minutes < 60) return '$minutes min';
    final hours = minutes ~/ 60;
    final rest = minutes % 60;
    return rest == 0 ? '${hours}h' : '${hours}h ${rest}min';
  }
}
