import 'package:flutter/widgets.dart';

import '../../core/api_client.dart';
import 'dietary_risk_models.dart';
import 'glucose_models.dart';

/// Meal inputs and results shared by the 4-hour forecast and Dynamic Dietary
/// Risk pages, so the meal is entered once and nothing is lost when switching
/// tabs.
///
/// Each result remembers the inputs it was computed from. When the inputs
/// change, the result is stale until it is requested again.
class GlucoseSession extends ChangeNotifier {
  GlucoseSession() {
    for (final controller in controllers) {
      controller.addListener(_onInputChanged);
    }
  }

  final premeal = TextEditingController();
  final calories = TextEditingController();
  final carbs = TextEditingController();
  final protein = TextEditingController();
  final fat = TextEditingController();
  final fiber = TextEditingController();

  /// In form order: pre-meal glucose, calories, carbs, protein, fat, fibre.
  List<TextEditingController> get controllers =>
      [premeal, calories, carbs, protein, fat, fiber];

  bool forecastLoading = false;
  String? forecastError;
  GlucoseForecast? forecast;
  GlucoseForecastRequest? forecastRequest;
  int _forecastSequence = 0;

  bool assessmentLoading = false;
  String? assessmentError;
  DietaryRiskAssessment? assessment;
  GlucoseForecastRequest? assessmentRequest;
  int _assessmentSequence = 0;

  /// The entered meal, or null unless all six fields pass the form's rules.
  GlucoseForecastRequest? get currentRequest {
    if (validatePremealGlucose(premeal.text) != null) return null;
    for (final controller in controllers.skip(1)) {
      if (validateNutrient(controller.text, label: '') != null) return null;
    }
    return GlucoseForecastRequest(
      premealGlucose: double.parse(premeal.text.trim()),
      calories: double.parse(calories.text.trim()),
      carbs: double.parse(carbs.text.trim()),
      protein: double.parse(protein.text.trim()),
      fat: double.parse(fat.text.trim()),
      fiber: double.parse(fiber.text.trim()),
    );
  }

  bool get forecastIsStale =>
      forecast != null && forecastRequest != currentRequest;

  /// A forecast exists for exactly the inputs currently entered.
  bool get hasCurrentForecast => forecast != null && !forecastIsStale;

  bool get assessmentIsStale =>
      assessment != null && assessmentRequest != currentRequest;

  /// Requests a forecast. Clears the previous forecast, as the forecast page
  /// always has. Returns true when a new forecast was stored.
  Future<bool> runForecast(
      ApiClient client, GlucoseForecastRequest request) async {
    final sequence = ++_forecastSequence;
    forecastLoading = true;
    forecastError = null;
    forecast = null;
    forecastRequest = null;
    notifyListeners();
    try {
      final result = await client.forecastGlucose(request);
      if (sequence != _forecastSequence) return false;
      forecast = result;
      forecastRequest = request;
      return true;
    } on ApiException catch (error) {
      if (sequence != _forecastSequence) return false;
      forecastError = error.message;
      return false;
    } finally {
      if (sequence == _forecastSequence) {
        forecastLoading = false;
        notifyListeners();
      }
    }
  }

  /// Requests the dietary-risk assessment for the current inputs. A previous
  /// assessment stays visible, marked stale, until the new one arrives.
  Future<void> runAssessment(ApiClient client) async {
    final request = currentRequest;
    if (request == null) return;
    final sequence = ++_assessmentSequence;
    assessmentLoading = true;
    assessmentError = null;
    notifyListeners();
    try {
      final result = await client.assessDietaryRisk(request);
      if (sequence != _assessmentSequence) return;
      assessment = result;
      assessmentRequest = request;
    } on ApiException catch (error) {
      if (sequence != _assessmentSequence) return;
      assessmentError = error.message;
    } finally {
      if (sequence == _assessmentSequence) {
        assessmentLoading = false;
        notifyListeners();
      }
    }
  }

  /// Controllers also notify on cursor moves; only notify when the text changes.
  void _onInputChanged() {
    final texts = [for (final c in controllers) c.text];
    if (_listEquals(texts, _lastTexts)) return;
    _lastTexts = texts;
    notifyListeners();
  }

  List<String> _lastTexts = List.filled(6, '');

  static bool _listEquals(List<String> a, List<String> b) {
    for (var i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }

  @override
  void dispose() {
    for (final controller in controllers) {
      controller.dispose();
    }
    super.dispose();
  }
}
