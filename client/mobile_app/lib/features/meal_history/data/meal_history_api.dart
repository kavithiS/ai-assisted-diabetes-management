import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/api_client.dart';
import 'meal_history_models.dart';

/// Calls C1 through the gateway for meal history and food search.
class MealHistoryApi {
  MealHistoryApi({ApiClient? apiClient, http.Client? httpClient})
      : _apiClient = apiClient ?? ApiClient(),
        _http = httpClient ?? http.Client();

  final ApiClient _apiClient;
  final http.Client _http;

  static const Duration _timeout = Duration(seconds: 15);

  Future<List<FoodResult>> searchFoods(String query, {int limit = 20}) async {
    final uri = _apiClient
        .uri('/api/v1/foods')
        .replace(queryParameters: {'q': query, 'limit': '$limit'});
    final response = await _http.get(uri).timeout(_timeout);
    _check(response);
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return [
      for (final f in body['foods'] as List<dynamic>)
        FoodResult.fromJson(f as Map<String, dynamic>),
    ];
  }

  Future<List<MealOut>> listMeals({int limit = 50, int offset = 0}) async {
    final uri = _apiClient.uri('/api/v1/meals').replace(
        queryParameters: {'limit': '$limit', 'offset': '$offset'});
    final response = await _http.get(uri).timeout(_timeout);
    _check(response);
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return [
      for (final m in body['meals'] as List<dynamic>)
        MealOut.fromJson(m as Map<String, dynamic>),
    ];
  }

  Future<MealOut> getMeal(int id) async {
    final response =
        await _http.get(_apiClient.uri('/api/v1/meals/$id')).timeout(_timeout);
    _check(response);
    return MealOut.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<MealOut> logMeal(MealCreate create) async {
    final response = await _http
        .post(
          _apiClient.uri('/api/v1/meals'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(create.toJson()),
        )
        .timeout(_timeout);
    _check(response, expectedStatus: 201);
    return MealOut.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<void> deleteMeal(int id) async {
    final response =
        await _http.delete(_apiClient.uri('/api/v1/meals/$id')).timeout(_timeout);
    _check(response, expectedStatus: 204);
  }

  Future<DailySummary> dailySummary(DateTime day, {int utcOffsetMinutes = 0}) async {
    final iso = '${day.year.toString().padLeft(4, '0')}'
        '-${day.month.toString().padLeft(2, '0')}'
        '-${day.day.toString().padLeft(2, '0')}';
    final uri = _apiClient.uri('/api/v1/meals/summary').replace(queryParameters: {
      'day': iso,
      'utc_offset_minutes': '$utcOffsetMinutes',
    });
    final response = await _http.get(uri).timeout(_timeout);
    _check(response);
    return DailySummary.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  void _check(http.Response r, {int expectedStatus = 200}) {
    if (r.statusCode == expectedStatus) return;
    String code = 'HTTP_${r.statusCode}';
    try {
      final body = jsonDecode(r.body);
      if (body is Map && body['error'] is Map && body['error']['code'] is String) {
        code = body['error']['code'] as String;
      }
    } on FormatException {/* keep HTTP code */}
    throw MealHistoryException(code, r.statusCode);
  }
}

class MealHistoryException implements Exception {
  const MealHistoryException(this.code, this.statusCode);

  final String code;
  final int statusCode;

  String get userMessage {
    if (statusCode == 404) return 'Meal not found.';
    if (statusCode >= 500) return 'Server error. Please try again later.';
    return 'Something went wrong ($code). Please try again.';
  }

  @override
  String toString() => 'MealHistoryException($code, $statusCode)';
}
