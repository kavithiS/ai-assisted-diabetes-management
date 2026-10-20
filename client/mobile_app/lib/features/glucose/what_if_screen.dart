import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import 'glucose_models.dart';
import 'glucose_screen.dart' show glucoseDisclaimer, glucoseResultsReminder;
import 'glucose_session.dart';
import 'what_if_models.dart';
import 'what_if_session.dart';
import 'what_if_trajectory_chart.dart';

/// Shown when the forecast tab has no valid meal to simulate from.
const whatIfNoInputsMessage =
    'Enter your pre-meal glucose and the meal on the 4-hour forecast tab. '
    'This page simulates changes to that meal.';

/// Shown when the meal or the carbohydrate amount changed after the comparison.
const whatIfStaleMessage =
    'You changed the meal or the carbohydrate amount. This comparison is for the '
    'previous values. Tap "Compare scenario" to update it.';

/// Explains why the rice portion options are off.
const whatIfRiceUnavailableMessage =
    'Carbohydrate values for rice portions have not been verified yet, so these '
    'options are unavailable. They can be turned on once verified nutrition data '
    'is added.';

/// Limitations shown on every comparison. Describes the simulation only.
const whatIfExplanationPoints = [
  'This is a hypothetical, model-based estimate. It shows what the research model '
      'predicts when only the carbohydrate amount is changed.',
  'Real glucose responses may differ from this simulation.',
  'The comparison is not a clinical recommendation, a diagnosis or a guaranteed '
      'effect of changing the meal.',
  'The model uses pre-meal glucose and the meal\'s energy, carbohydrate, protein, '
      'fat and fibre. It does not use glycaemic index, glycaemic load, daily '
      'carbohydrate totals, meal timing or activity.',
];

// Neutral palette shared with the other Glucose pages. Teal accents come from
// the app theme.
const _pageBackground = Color(0xFFF4F7F7);
const _cardBorder = Color(0xFFE2E8EA);
const _mutedText = Color(0xFF5F6B6D);
const _navy = Color(0xFF1B2A41);
const _amber = Color(0xFFB4610E);
const _amberSoft = Color(0xFFFFF1DC);
const _tealSoft = Color(0xFFE6F4F2);

/// What-If Meal Simulation (C2): compares the forecast for the entered meal with
/// the forecast for the same meal at a different carbohydrate amount. Every
/// value shown comes from the user's inputs or the forecast API.
class WhatIfScreen extends StatefulWidget {
  const WhatIfScreen({
    super.key,
    required this.session,
    required this.whatIf,
    this.apiClient,
    this.ricePortionMapping = verifiedRicePortionMapping,
  });

  /// Meal inputs shared with the 4-hour forecast page.
  final GlucoseSession session;

  /// Simulation state: the simulated carbohydrate amount and the last comparison.
  final WhatIfSession whatIf;

  /// Injected in tests. When null, the screen creates and owns its own client.
  final ApiClient? apiClient;

  /// Carbohydrate grams for each rice portion. Null keeps the rice portion
  /// options disabled.
  final RicePortionMapping? ricePortionMapping;

  @override
  State<WhatIfScreen> createState() => _WhatIfScreenState();
}

class _WhatIfScreenState extends State<WhatIfScreen> {
  /// Marks the comparison so it can be scrolled into view once it is laid out.
  final _resultsKey = GlobalKey();

  late final ApiClient _client = widget.apiClient ?? ApiClient();

  @override
  void dispose() {
    if (widget.apiClient == null) _client.close();
    super.dispose();
  }

  Future<void> _compare(GlucoseForecastRequest baseline) async {
    final whatIf = widget.whatIf;
    final succeeded = await whatIf.runComparison(
      _client,
      baseline,
      whatIf.carbsFor(baseline.carbs),
    );
    if (succeeded && mounted) _scrollToResults();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([widget.session, widget.whatIf]),
      builder: (context, _) => _buildPage(context),
    );
  }

  Widget _buildPage(BuildContext context) {
    final theme = Theme.of(context);
    final baseline = widget.session.currentRequest;

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
                  'What-If Meal Simulation',
                  style: theme.textTheme.headlineSmall
                      ?.copyWith(fontWeight: FontWeight.w800, color: _navy),
                ),
                const SizedBox(height: 4),
                Text(
                  'Explore how changing the meal could affect the estimated glucose response.',
                  style:
                      theme.textTheme.bodyMedium?.copyWith(color: _mutedText),
                ),
                const SizedBox(height: 16),
                _notice(
                  theme,
                  icon: Icons.info_outline,
                  foreground: theme.colorScheme.primary,
                  background: _tealSoft,
                  text: glucoseDisclaimer,
                ),
                const SizedBox(height: 16),
                if (baseline == null)
                  _guidanceCard(theme)
                else
                  ..._simulationSections(theme, baseline),
              ],
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _simulationSections(
      ThemeData theme, GlucoseForecastRequest baseline) {
    final whatIf = widget.whatIf;
    final carbs = whatIf.carbsFor(baseline.carbs);
    final comparison = whatIf.comparison;
    final stale = whatIf.isStale(baseline, carbs);

    return [
      _originalMealCard(theme, baseline),
      const SizedBox(height: 16),
      _carbCard(theme, baseline, carbs),
      const SizedBox(height: 16),
      _ricePortionCard(theme, carbs),
      const SizedBox(height: 16),
      FilledButton.icon(
        onPressed: whatIf.loading ? null : () => _compare(baseline),
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(54),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle:
              theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
        ),
        icon: whatIf.loading
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.compare_arrows),
        label: Text(whatIf.loading ? 'Comparing…' : 'Compare scenario'),
      ),
      const SizedBox(height: 8),
      Text(
        'Runs the forecast for the current and what-if meals. Moving the slider '
        'sends no requests.',
        textAlign: TextAlign.center,
        style: theme.textTheme.bodySmall?.copyWith(color: _mutedText),
      ),
      if (whatIf.loading) ...[
        const SizedBox(height: 12),
        _notice(
          theme,
          icon: Icons.hourglass_top,
          foreground: theme.colorScheme.primary,
          background: Colors.white,
          border: _cardBorder,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Calculating the two estimates…',
                  style: theme.textTheme.bodyMedium),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: const LinearProgressIndicator(minHeight: 4),
              ),
            ],
          ),
        ),
      ],
      if (whatIf.error != null) ...[
        const SizedBox(height: 16),
        _errorCard(theme, whatIf.error!),
      ],
      if (comparison != null) ...[
        const SizedBox(height: 24),
        if (stale) ...[
          _notice(
            theme,
            icon: Icons.update,
            foreground: _amber,
            background: _amberSoft,
            text: whatIfStaleMessage,
          ),
          const SizedBox(height: 12),
        ],
        Opacity(
          opacity: stale ? 0.6 : 1,
          child: _resultsSection(theme, comparison),
        ),
      ],
      const SizedBox(height: 24),
      _explanationCard(theme),
    ];
  }

  // --- guidance ---------------------------------------------------------------------

  Widget _guidanceCard(ThemeData theme) {
    final tabs = DefaultTabController.maybeOf(context);
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.info_outline, color: theme.colorScheme.primary),
              const SizedBox(width: 12),
              Expanded(
                child: Text(whatIfNoInputsMessage,
                    style: theme.textTheme.bodyMedium?.copyWith(height: 1.35)),
              ),
            ],
          ),
          if (tabs != null) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
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

  // --- inputs -----------------------------------------------------------------------

  Widget _originalMealCard(ThemeData theme, GlucoseForecastRequest baseline) {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _sectionHeader(
            theme,
            icon: Icons.restaurant_outlined,
            title: 'Original meal',
            subtitle: 'Values you entered on the 4-hour forecast tab.',
          ),
          const SizedBox(height: 12),
          _inputRow(theme, 'Carbohydrates', '${_grams(baseline.carbs)} g'),
          _inputRow(theme, 'Pre-meal glucose',
              '${_grams(baseline.premealGlucose)} mg/dL'),
          _inputRow(
              theme, 'Other nutrition', 'Kept the same in the simulation'),
        ],
      ),
    );
  }

  Widget _carbCard(
      ThemeData theme, GlucoseForecastRequest baseline, double carbs) {
    final max = whatIfMaxCarbsGrams(baseline.carbs);
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _sectionHeader(
            theme,
            icon: Icons.bakery_dining_outlined,
            title: 'Carbohydrate amount',
            subtitle: 'Drag to simulate a different amount.',
          ),
          const SizedBox(height: 16),
          Text(
            'Original ${_grams(baseline.carbs)} g',
            style: theme.textTheme.bodyMedium?.copyWith(color: _mutedText),
          ),
          const SizedBox(height: 2),
          Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: _grams(carbs),
                  style: theme.textTheme.headlineMedium?.copyWith(
                      color: theme.colorScheme.primary,
                      fontWeight: FontWeight.w800),
                ),
                TextSpan(
                  text: ' g simulated',
                  style: theme.textTheme.titleSmall?.copyWith(
                      color: theme.colorScheme.primary,
                      fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
          Slider(
            value: carbs,
            min: whatIfMinCarbsGrams,
            max: max,
            label: '${_grams(carbs)} g',
            onChanged: (value) => widget.whatIf
                .setScenarioCarbs((value * 10).roundToDouble() / 10),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('${whatIfMinCarbsGrams.round()} g',
                  style:
                      theme.textTheme.bodySmall?.copyWith(color: _mutedText)),
              Text('${max.round()} g',
                  style:
                      theme.textTheme.bodySmall?.copyWith(color: _mutedText)),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'The slider range only limits this simulation. It is not a '
            'recommended or safe amount.',
            style: theme.textTheme.bodySmall?.copyWith(color: _mutedText),
          ),
        ],
      ),
    );
  }

  Widget _ricePortionCard(ThemeData theme, double carbs) {
    final mapping = widget.ricePortionMapping;
    final selected = _selectedPortion(mapping, carbs);
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _sectionHeader(
            theme,
            icon: Icons.rice_bowl_outlined,
            title: 'Rice portion (optional)',
            subtitle:
                'Sets the carbohydrate amount from a verified portion value.',
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final portion in RicePortion.values)
                ChoiceChip(
                  label: Text(portion.label),
                  selected: selected == portion,
                  onSelected: _portionGrams(mapping, portion) == null
                      ? null
                      : (_) => widget.whatIf
                          .setScenarioCarbs(_portionGrams(mapping, portion)!),
                ),
            ],
          ),
          if (mapping == null) ...[
            const SizedBox(height: 12),
            _notice(
              theme,
              icon: Icons.lock_outline,
              foreground: _mutedText,
              background: _pageBackground,
              text: whatIfRiceUnavailableMessage,
            ),
          ],
        ],
      ),
    );
  }

  double? _portionGrams(RicePortionMapping? mapping, RicePortion portion) =>
      mapping?.carbsGramsByPortion[portion];

  RicePortion? _selectedPortion(RicePortionMapping? mapping, double carbs) {
    if (mapping == null) return null;
    for (final portion in RicePortion.values) {
      final grams = _portionGrams(mapping, portion);
      if (grams != null && (grams - carbs).abs() < 1e-9) return portion;
    }
    return null;
  }

  // --- results ----------------------------------------------------------------------

  Widget _resultsSection(ThemeData theme, WhatIfComparison comparison) {
    final small = theme.textTheme.bodySmall?.copyWith(color: _mutedText);
    final difference = comparison.peakDifferenceMgDl;
    final timing = comparison.peakTimingDifferenceMinutes;
    return Column(
      key: _resultsKey,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Current meal vs what-if meal',
          style:
              theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 4),
        Text('Estimates only. Values are rounded to whole mg/dL.',
            style: small),
        const SizedBox(height: 14),
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: _peakTile(
                  theme,
                  title: 'Current meal',
                  forecast: comparison.baseline,
                  accent: whatIfCurrentColor,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _peakTile(
                  theme,
                  title: 'What-if meal',
                  forecast: comparison.scenario,
                  accent: whatIfScenarioColor,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        _card(
          color: _tealSoft,
          borderColor: theme.colorScheme.primary.withValues(alpha: 0.25),
          child: Row(
            children: [
              Expanded(
                child: _differenceColumn(
                  theme,
                  label: 'Peak difference',
                  value: '${_signed(difference)} mg/dL',
                ),
              ),
              Expanded(
                child: _differenceColumn(
                  theme,
                  label: 'Peak timing',
                  value: _timingText(timing),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Difference = what-if meal minus current meal. Estimated, not observed.',
          style: small,
        ),
        const SizedBox(height: 16),
        _card(
          padding: const EdgeInsets.fromLTRB(12, 18, 20, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.only(left: 8, bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Glucose trajectory',
                        style: theme.textTheme.titleMedium
                            ?.copyWith(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text('mg/dL · hours after the meal', style: small),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 16,
                      runSpacing: 6,
                      children: [
                        _legendItem(theme, whatIfCurrentColor, 'Current meal',
                            dashed: true),
                        _legendItem(theme, whatIfScenarioColor, 'What-if meal'),
                      ],
                    ),
                  ],
                ),
              ),
              WhatIfTrajectoryChart(
                horizonMinutes: comparison.baseline.horizonMinutes,
                currentPredictions: comparison.baseline.predictions,
                scenarioPredictions: comparison.scenario.predictions,
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: _cardBorder),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(glucoseResultsReminder,
                  style: theme.textTheme.bodySmall
                      ?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              Text(comparison.baseline.disclaimer, style: small),
              const SizedBox(height: 4),
              Text(
                'Model: ${comparison.baseline.modelName} '
                '(${comparison.baseline.modelVersion})',
                style: small,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _peakTile(
    ThemeData theme, {
    required String title,
    required GlucoseForecast forecast,
    required Color accent,
  }) {
    return _card(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: theme.textTheme.titleSmall
                  ?.copyWith(color: accent, fontWeight: FontWeight.w700)),
          const SizedBox(height: 2),
          Text('Model estimate',
              style: theme.textTheme.labelSmall?.copyWith(color: _mutedText)),
          const SizedBox(height: 10),
          Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: '${forecast.peakGlucose.round()}',
                  style: theme.textTheme.headlineSmall
                      ?.copyWith(color: _navy, fontWeight: FontWeight.w800),
                ),
                TextSpan(
                  text: ' mg/dL',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: _navy, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Peak at +${_formatMinutes(forecast.peakMinutes)}',
            style: theme.textTheme.bodySmall?.copyWith(color: _mutedText),
          ),
        ],
      ),
    );
  }

  Widget _differenceColumn(
    ThemeData theme, {
    required String label,
    required String value,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: theme.textTheme.bodySmall?.copyWith(color: _mutedText)),
        const SizedBox(height: 4),
        Text(value,
            style: theme.textTheme.titleMedium?.copyWith(
                color: theme.colorScheme.primary, fontWeight: FontWeight.w800)),
      ],
    );
  }

  Widget _legendItem(ThemeData theme, Color color, String label,
      {bool dashed = false}) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // A short sample in the series colour. The current meal is also drawn
        // dashed on the chart, so the legend shows which line is which without
        // relying on colour alone.
        if (dashed)
          Row(
            children: [
              for (var i = 0; i < 3; i++) ...[
                if (i > 0) const SizedBox(width: 3),
                Container(width: 6, height: 3, color: color),
              ],
            ],
          )
        else
          Container(
            width: 22,
            height: 3,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        const SizedBox(width: 6),
        Text(label, style: theme.textTheme.bodySmall),
      ],
    );
  }

  // --- explanation ------------------------------------------------------------------

  Widget _explanationCard(ThemeData theme) {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('About this simulation',
              style: theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          for (final point in whatIfExplanationPoints)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('•  '),
                  Expanded(
                    child: Text(point,
                        style:
                            theme.textTheme.bodySmall?.copyWith(height: 1.4)),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  // --- notices and shared pieces ----------------------------------------------------

  Widget _errorCard(ThemeData theme, String message) {
    final onError = theme.colorScheme.onErrorContainer;
    return _notice(
      theme,
      icon: Icons.error_outline,
      foreground: onError,
      background: theme.colorScheme.errorContainer,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Could not compare the meals',
            style: theme.textTheme.titleSmall
                ?.copyWith(color: onError, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 2),
          Text(message, style: TextStyle(color: onError)),
        ],
      ),
    );
  }

  Widget _inputRow(ThemeData theme, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: Text(label,
                style: theme.textTheme.bodyMedium?.copyWith(color: _mutedText)),
          ),
          Expanded(
            flex: 3,
            child: Text(value,
                textAlign: TextAlign.end,
                style: theme.textTheme.bodyLarge
                    ?.copyWith(fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }

  Widget _sectionHeader(
    ThemeData theme, {
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return Row(
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: _tealSoft,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, size: 20, color: theme.colorScheme.primary),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title,
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700)),
              Text(subtitle,
                  style:
                      theme.textTheme.bodySmall?.copyWith(color: _mutedText)),
            ],
          ),
        ),
      ],
    );
  }

  Widget _notice(
    ThemeData theme, {
    required IconData icon,
    required Color foreground,
    required Color background,
    String? text,
    Widget? child,
    Color? border,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(14),
        border: border == null ? null : Border.all(color: border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: foreground),
          const SizedBox(width: 12),
          Expanded(
            child: child ??
                Text(text ?? '',
                    style: theme.textTheme.bodySmall?.copyWith(height: 1.35)),
          ),
        ],
      ),
    );
  }

  Widget _card({
    required Widget child,
    EdgeInsets padding = const EdgeInsets.all(18),
    Color color = Colors.white,
    Color borderColor = _cardBorder,
  }) {
    return Container(
      padding: padding,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: borderColor),
      ),
      child: child,
    );
  }

  /// Brings the comparison into view. It renders below the sliders, usually
  /// off-screen, so this runs after the next frame, once it has been laid out.
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

  static String _grams(double value) => value == value.roundToDouble()
      ? '${value.round()}'
      : value.toStringAsFixed(1);

  static String _signed(int value) => value > 0 ? '+$value' : '$value';

  static String _timingText(int minutes) {
    if (minutes == 0) return 'Same time';
    if (minutes > 0) return '${_formatMinutes(minutes)} later';
    return '${_formatMinutes(-minutes)} earlier';
  }

  static String _formatMinutes(int minutes) {
    if (minutes < 60) return '$minutes min';
    final hours = minutes ~/ 60;
    final rest = minutes % 60;
    return rest == 0 ? '${hours}h' : '${hours}h ${rest}min';
  }
}
