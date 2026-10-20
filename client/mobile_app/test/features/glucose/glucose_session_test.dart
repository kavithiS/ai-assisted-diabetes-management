import 'dart:async';

import 'package:flutter/services.dart' show TextSelection;
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/core/api_client.dart';
import 'package:mobile_app/features/glucose/dietary_risk_models.dart';
import 'package:mobile_app/features/glucose/glucose_models.dart';
import 'package:mobile_app/features/glucose/glucose_session.dart';

import 'fake_glucose_api.dart';

void fill(GlucoseSession session, List<String> values) {
  for (var i = 0; i < values.length; i++) {
    session.controllers[i].text = values[i];
  }
}

void main() {
  test('currentRequest needs all six valid inputs', () {
    final session = GlucoseSession();
    expect(session.currentRequest, isNull);

    fill(session, ['110', '600', '70', '25', '20']);
    expect(session.currentRequest, isNull);

    fill(session, ['0', ...testMealValues.skip(1)]);
    expect(session.currentRequest, isNull);

    fill(session, testMealValues);
    expect(session.currentRequest, testMealRequest);
    session.dispose();
  });

  test('requests are equal only when every input is equal', () {
    const other = GlucoseForecastRequest(
        premealGlucose: 110,
        calories: 600,
        carbs: 70,
        protein: 25,
        fat: 20,
        fiber: 9);
    expect(testMealRequest == other, isFalse);
    expect(
        testMealRequest,
        const GlucoseForecastRequest(
            premealGlucose: 110,
            calories: 600,
            carbs: 70,
            protein: 25,
            fat: 20,
            fiber: 8));
  });

  test(
      'a forecast becomes stale when an input changes and current again '
      'when it is changed back', () async {
    final session = GlucoseSession();
    fill(session, testMealValues);
    await session.runForecast(FakeGlucoseApi(), session.currentRequest!);
    expect(session.hasCurrentForecast, isTrue);

    session.carbs.text = '90';
    expect(session.forecastIsStale, isTrue);
    expect(session.hasCurrentForecast, isFalse);

    session.carbs.text = '70';
    expect(session.hasCurrentForecast, isTrue);
    session.dispose();
  });

  test('assessment uses the current inputs and is marked stale after a change',
      () async {
    final session = GlucoseSession();
    final api = FakeGlucoseApi();
    fill(session, testMealValues);

    await session.runAssessment(api);

    expect(api.assessRequests, [testMealRequest]);
    expect(session.assessmentRequest, testMealRequest);
    expect(session.assessmentIsStale, isFalse);

    session.premeal.text = '150';
    expect(session.assessmentIsStale, isTrue);
    expect(session.assessment, isNotNull,
        reason: 'Old results stay visible, marked stale.');
    session.dispose();
  });

  test('assessment does nothing without valid inputs', () async {
    final session = GlucoseSession();
    final api = FakeGlucoseApi();

    await session.runAssessment(api);

    expect(api.assessRequests, isEmpty);
    session.dispose();
  });

  test('an assessment error is reported and earlier results are kept',
      () async {
    final session = GlucoseSession();
    final api = FakeGlucoseApi();
    fill(session, testMealValues);
    await session.runAssessment(api);

    api.onAssess = () async => throw const ApiException('Model down.');
    await session.runAssessment(api);

    expect(session.assessmentError, 'Model down.');
    expect(session.assessment, isNotNull);
    expect(session.assessmentLoading, isFalse);
    session.dispose();
  });

  test('an older response cannot replace a newer one', () async {
    final session = GlucoseSession();
    final first = Completer<DietaryRiskAssessment>();
    final api = FakeGlucoseApi(assess: () => first.future);
    fill(session, testMealValues);

    final slow = session.runAssessment(api);
    session.carbs.text = '90';
    api.onAssess = () async => testAssessment(estimate: false);
    await session.runAssessment(api);
    first.complete(testAssessment(estimate: true));
    await slow;

    expect(session.assessment!.indicator.estimatedAbove180, isFalse);
    expect(session.assessmentRequest!.carbs, 90);
    session.dispose();
  });

  test('notifies listeners when text changes but not on cursor moves', () {
    final session = GlucoseSession();
    var notifications = 0;
    session.addListener(() => notifications++);

    session.carbs.text = '70';
    expect(notifications, 1);

    session.carbs.selection = const TextSelection.collapsed(offset: 1);
    expect(notifications, 1);
    session.dispose();
  });
}
