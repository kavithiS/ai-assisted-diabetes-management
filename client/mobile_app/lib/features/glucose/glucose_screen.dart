import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import 'glucose_models.dart';
import 'glucose_session.dart';
import 'glucose_trajectory_chart.dart';

/// Shown above the form, so it is read before any estimate is requested.
const glucoseDisclaimer =
    'Research prototype only. These estimates are not medical advice and must not be '
    'used for diagnosis, treatment or insulin dosing.';

/// Repeated under the results, which the screen scrolls to after a forecast.
const glucoseResultsReminder =
    'Not for diagnosis, treatment or insulin dosing.';

/// Shown when the inputs have changed since the displayed forecast.
const glucoseStaleForecastMessage =
    'You changed the meal details. This estimate is for the previous values. '
    'Tap "Get 4-hour estimate" to update it.';

// Neutral palette shared with the Dynamic Dietary Risk page. Teal accents come
// from the app theme's colour scheme.
const _pageBackground = Color(0xFFF4F7F7);
const _cardBorder = Color(0xFFE2E8EA);
const _mutedText = Color(0xFF5F6B6D);
const _amber = Color(0xFFB4610E);
const _amberSoft = Color(0xFFFFF1DC);
const _tealSoft = Color(0xFFE6F4F2);

/// Nutrition fields switch to two columns at this width.
const _twoColumnWidth = 520.0;

/// Glucose (C2): four-hour glucose forecast from pre-meal glucose and the meal's nutrition.
class GlucoseScreen extends StatefulWidget {
  const GlucoseScreen({
    super.key,
    this.apiClient,
    this.session,
    this.nutritionReadOnly = false,
  });

  /// Injected in tests. When null, the screen creates and owns its own client.
  final ApiClient? apiClient;

  /// Inputs and results shared with the Dynamic Dietary Risk page. When null,
  /// the screen creates and owns its own session.
  final GlucoseSession? session;

  /// Keep reviewed scan totals tied to the meal instead of silently editing
  /// them in the forecast form. The standalone glucose page remains editable.
  final bool nutritionReadOnly;

  @override
  State<GlucoseScreen> createState() => _GlucoseScreenState();
}

class _GlucoseScreenState extends State<GlucoseScreen> {
  final _formKey = GlobalKey<FormState>();

  /// Marks the results section so it can be scrolled into view once it is laid out.
  final _resultsKey = GlobalKey();

  late final ApiClient _client = widget.apiClient ?? ApiClient();
  late final GlucoseSession _session = widget.session ?? GlucoseSession();

  TextEditingController get _premeal => _session.premeal;
  TextEditingController get _calories => _session.calories;
  TextEditingController get _carbs => _session.carbs;
  TextEditingController get _protein => _session.protein;
  TextEditingController get _fat => _session.fat;
  TextEditingController get _fiber => _session.fiber;

  @override
  void dispose() {
    if (widget.session == null) {
      _session.dispose();
    }
    if (widget.apiClient == null) {
      _client.close();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    final request = GlucoseForecastRequest(
      premealGlucose: double.parse(_premeal.text.trim()),
      calories: double.parse(_calories.text.trim()),
      carbs: double.parse(_carbs.text.trim()),
      protein: double.parse(_protein.text.trim()),
      fat: double.parse(_fat.text.trim()),
      fiber: double.parse(_fiber.text.trim()),
    );

    final succeeded = await _session.runForecast(_client, request);
    if (succeeded && mounted) _scrollToResults();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _session,
      builder: (context, _) => _buildPage(context),
    );
  }

  Widget _buildPage(BuildContext context) {
    final theme = Theme.of(context);
    final loading = _session.forecastLoading;
    final error = _session.forecastError;
    final forecast = _session.forecast;

    return ColoredBox(
      color: _pageBackground,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 32),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Glucose Forecast',
                  style: theme.textTheme.headlineSmall
                      ?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                Text(
                  'Estimate how your glucose may change over the next four hours after a meal.',
                  style:
                      theme.textTheme.bodyMedium?.copyWith(color: _mutedText),
                ),
                const SizedBox(height: 12),
                _buildDisclaimer(theme),
                const SizedBox(height: 20),
                _buildForm(theme),
                const SizedBox(height: 20),
                _buildSubmitButton(theme, loading),
                if (loading) ...[
                  const SizedBox(height: 12),
                  _buildLoading(theme),
                ],
                if (error != null) ...[
                  const SizedBox(height: 16),
                  _buildError(theme, error),
                ],
                if (forecast != null) ...[
                  const SizedBox(height: 28),
                  if (_session.forecastIsStale) ...[
                    _buildStaleNotice(theme),
                    const SizedBox(height: 12),
                  ],
                  _buildResults(theme, forecast),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  // --- input ------------------------------------------------------------------------

  Widget _buildForm(ThemeData theme) {
    final nutrition = [
      _numberField(
        theme,
        controller: _calories,
        label: 'Calories (kcal)',
        icon: Icons.local_fire_department_outlined,
        validator: (v) => validateNutrient(v, label: 'Calories'),
        readOnly: widget.nutritionReadOnly,
      ),
      _numberField(
        theme,
        controller: _carbs,
        label: 'Carbohydrates (g)',
        icon: Icons.bakery_dining_outlined,
        validator: (v) => validateNutrient(v, label: 'Carbohydrates'),
        readOnly: widget.nutritionReadOnly,
      ),
      _numberField(
        theme,
        controller: _protein,
        label: 'Protein (g)',
        icon: Icons.egg_outlined,
        validator: (v) => validateNutrient(v, label: 'Protein'),
        readOnly: widget.nutritionReadOnly,
      ),
      _numberField(
        theme,
        controller: _fat,
        label: 'Fat (g)',
        icon: Icons.opacity,
        validator: (v) => validateNutrient(v, label: 'Fat'),
        readOnly: widget.nutritionReadOnly,
      ),
      _numberField(
        theme,
        controller: _fiber,
        label: 'Fibre (g)',
        icon: Icons.eco_outlined,
        validator: (v) => validateNutrient(v, label: 'Fibre'),
        readOnly: widget.nutritionReadOnly,
      ),
    ];

    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _SurfaceCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _SectionHeader(
                  icon: Icons.water_drop_outlined,
                  title: 'Before your meal',
                  subtitle: 'Your current glucose reading.',
                ),
                const SizedBox(height: 16),
                _numberField(
                  theme,
                  controller: _premeal,
                  label: 'Current pre-meal glucose (mg/dL)',
                  icon: Icons.bloodtype_outlined,
                  validator: validatePremealGlucose,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _SurfaceCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _SectionHeader(
                  icon: Icons.restaurant_outlined,
                  title: 'The meal',
                  subtitle: widget.nutritionReadOnly
                      ? 'Values from the foods and portions you reviewed.'
                      : 'Enter 0 for any nutrient that does not apply.',
                ),
                const SizedBox(height: 16),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final columns =
                        constraints.maxWidth >= _twoColumnWidth ? 2 : 1;
                    const gap = 12.0;
                    final width =
                        (constraints.maxWidth - gap * (columns - 1)) / columns;
                    return Wrap(
                      spacing: gap,
                      runSpacing: 14,
                      children: [
                        for (final field in nutrition)
                          SizedBox(width: width, child: field),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _numberField(
    ThemeData theme, {
    required TextEditingController controller,
    required String label,
    required IconData icon,
    required String? Function(String?) validator,
    bool readOnly = false,
  }) {
    OutlineInputBorder border(Color color, [double width = 1]) =>
        OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: color, width: width),
        );

    return TextFormField(
      controller: controller,
      readOnly: readOnly,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      textInputAction: TextInputAction.next,
      decoration: InputDecoration(
        labelText: label,
        // Keep the label above the field so long labels and their units stay
        // readable on narrow screens instead of being cut off inside it.
        floatingLabelBehavior: FloatingLabelBehavior.always,
        prefixIcon: Icon(icon, color: theme.colorScheme.primary, size: 20),
        filled: true,
        fillColor: Colors.white,
        border: border(_cardBorder),
        enabledBorder: border(_cardBorder),
        focusedBorder: border(theme.colorScheme.primary, 1.6),
        errorBorder: border(theme.colorScheme.error),
        focusedErrorBorder: border(theme.colorScheme.error, 1.6),
      ),
      validator: validator,
      autovalidateMode: AutovalidateMode.onUserInteraction,
    );
  }

  Widget _buildSubmitButton(ThemeData theme, bool loading) {
    return FilledButton.icon(
      onPressed: loading ? null : _submit,
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(54),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle:
            theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
      ),
      icon: loading
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.show_chart),
      label: Text(loading ? 'Getting estimate…' : 'Get 4-hour estimate'),
    );
  }

  // --- notices ----------------------------------------------------------------------

  Widget _buildDisclaimer(ThemeData theme) {
    return _Notice(
      icon: Icons.info_outline,
      foreground: theme.colorScheme.primary,
      background: _tealSoft,
      child: Text(
        glucoseDisclaimer,
        style: theme.textTheme.bodySmall?.copyWith(height: 1.35),
      ),
    );
  }

  Widget _buildLoading(ThemeData theme) {
    return _Notice(
      icon: Icons.hourglass_top,
      foreground: theme.colorScheme.primary,
      background: Colors.white,
      border: _cardBorder,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Calculating your 4-hour estimate…',
              style: theme.textTheme.bodyMedium),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: const LinearProgressIndicator(minHeight: 4),
          ),
        ],
      ),
    );
  }

  Widget _buildError(ThemeData theme, String message) {
    final onError = theme.colorScheme.onErrorContainer;
    return _Notice(
      icon: Icons.error_outline,
      foreground: onError,
      background: theme.colorScheme.errorContainer,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Could not get an estimate',
            style: theme.textTheme.titleSmall
                ?.copyWith(color: onError, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 2),
          Text(message, style: TextStyle(color: onError)),
        ],
      ),
    );
  }

  Widget _buildStaleNotice(ThemeData theme) {
    return _Notice(
      icon: Icons.update,
      foreground: _amber,
      background: _amberSoft,
      child: Text(
        glucoseStaleForecastMessage,
        style: theme.textTheme.bodySmall?.copyWith(height: 1.35),
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

  // --- results ----------------------------------------------------------------------

  Widget _buildResults(ThemeData theme, GlucoseForecast forecast) {
    final small = theme.textTheme.bodySmall?.copyWith(color: _mutedText);
    return Opacity(
      // Stale results stay readable but recede behind the notice above them.
      opacity: _session.forecastIsStale ? 0.6 : 1,
      child: Column(
        key: _resultsKey,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Estimated glucose, next 4 hours',
            style: theme.textTheme.titleLarge
                ?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text('Estimate only. Values are rounded to whole mg/dL.',
              style: small),
          const SizedBox(height: 14),
          _buildPeakSummary(theme, forecast),
          const SizedBox(height: 16),
          _SurfaceCard(
            padding: const EdgeInsets.fromLTRB(12, 18, 20, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Padding(
                  padding: const EdgeInsets.only(left: 8, bottom: 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Glucose trajectory',
                          style: theme.textTheme.titleMedium
                              ?.copyWith(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 2),
                      Text('${forecast.unit} · hours after the meal',
                          style: small),
                    ],
                  ),
                ),
                GlucoseTrajectoryChart(
                  predictions: forecast.predictions,
                  horizonMinutes: forecast.horizonMinutes,
                  peakIndex: forecast.peakIndex,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _buildValuesList(theme, forecast),
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
                Text(forecast.disclaimer, style: small),
                const SizedBox(height: 4),
                Text(
                  'Model: ${forecast.modelName} (${forecast.modelVersion})',
                  style: small,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPeakSummary(ThemeData theme, GlucoseForecast forecast) {
    final primary = theme.colorScheme.primary;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: _tealSoft,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: primary.withValues(alpha: 0.25)),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
              border: Border.all(color: primary.withValues(alpha: 0.25)),
            ),
            child: Icon(Icons.trending_up, color: primary),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // One sentence for tests and screen readers; the number is emphasised.
                Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(
                        text: 'Highest estimate: ',
                        style: theme.textTheme.titleSmall
                            ?.copyWith(color: _mutedText),
                      ),
                      TextSpan(
                        text: '${forecast.peakGlucose.round()}',
                        style: theme.textTheme.headlineMedium?.copyWith(
                            color: primary, fontWeight: FontWeight.w800),
                      ),
                      TextSpan(
                        text: ' ${forecast.unit}',
                        style: theme.textTheme.titleMedium?.copyWith(
                            color: primary, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(Icons.schedule, size: 16, color: _mutedText),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        'At +${_formatHorizon(forecast.peakMinutes)} after the meal',
                        style: theme.textTheme.bodyMedium
                            ?.copyWith(color: _mutedText),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildValuesList(ThemeData theme, GlucoseForecast forecast) {
    return _SurfaceCard(
      padding: EdgeInsets.zero,
      child: Theme(
        // Remove the default divider lines the expansion tile draws.
        data: theme.copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          shape: const RoundedRectangleBorder(),
          collapsedShape: const RoundedRectangleBorder(),
          tilePadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 4),
          leading: Icon(Icons.format_list_numbered,
              color: theme.colorScheme.primary),
          title: Text('All ${forecast.predictions.length} estimates',
              style: theme.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.w700)),
          subtitle: Text('Every 15 minutes after the meal',
              style: theme.textTheme.bodySmall?.copyWith(color: _mutedText)),
          childrenPadding: const EdgeInsets.only(bottom: 8),
          children: [
            for (var i = 0; i < forecast.predictions.length; i++)
              ListTile(
                dense: true,
                visualDensity: VisualDensity.compact,
                contentPadding: const EdgeInsets.symmetric(horizontal: 18),
                tileColor: i.isOdd ? _pageBackground : null,
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
    );
  }

  String _formatHorizon(int minutes) {
    if (minutes < 60) return '$minutes min';
    final hours = minutes ~/ 60;
    final rest = minutes % 60;
    return rest == 0 ? '${hours}h' : '${hours}h ${rest}min';
  }
}

/// White card with a subtle border, used for every content block on the page.
class _SurfaceCard extends StatelessWidget {
  const _SurfaceCard({
    required this.child,
    this.padding = const EdgeInsets.all(18),
  });

  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _cardBorder),
      ),
      child: child,
    );
  }
}

/// Icon badge, title and supporting line at the top of a form section.
class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
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
}

/// Compact coloured banner with a leading icon: disclaimer, loading, error, stale.
class _Notice extends StatelessWidget {
  const _Notice({
    required this.icon,
    required this.foreground,
    required this.background,
    required this.child,
    this.border,
  });

  final IconData icon;
  final Color foreground;
  final Color background;
  final Color? border;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(14),
        border: border == null ? null : Border.all(color: border!),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: foreground),
          const SizedBox(width: 12),
          Expanded(child: child),
        ],
      ),
    );
  }
}
