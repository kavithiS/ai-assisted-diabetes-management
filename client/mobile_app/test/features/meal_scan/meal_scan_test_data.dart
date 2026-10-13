import 'dart:convert';
import 'dart:typed_data';

/// A valid 1x1 PNG (generated test image, never a real meal photo).
final Uint8List tinyPng = base64Decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
);

/// Shaped like the C1 mock response. Values are arbitrary test fixtures, not nutrition data.
Map<String, dynamic> mockAnalysisJson() => {
      'analysis_id': '00000000-0000-0000-0000-000000000001',
      'meta': {
        'is_mock': true,
        'api_version': 'v1',
        'model_name': 'mock-recognizer',
        'model_version': '0.0.0-mock',
        'generated_at': '2026-10-03T07:00:01Z',
        'request_id': 'test',
        'warnings': ['MOCK RESPONSE'],
      },
      'metadata': {'meal_type': 'lunch', 'captured_at': '2026-10-03T07:00:00Z', 'reference_object': null},
      'image': {'media_type': 'image/png', 'width': 1, 'height': 1, 'size_bytes': 68},
      'items': [
        {
          'item_id': 'item-1',
          'label': 'Test Food A',
          'food_code': null,
          'confidence': 0.87,
          'region': null,
          'portion': {
            'grams': 150.0,
            'household_measure': '1 cup',
            'estimation_method': 'mock',
            'confidence': 0.42,
          },
          'nutrition': {
            'energy_kcal': 200.0,
            'carbohydrate_g': 40.0,
            'sugars_g': null,
            'dietary_fiber_g': 2.0,
            'protein_g': 5.0,
            'fat_g': 1.0,
            'sodium_mg': 10.0,
          },
          'nutrition_source': {'source': 'MOCK', 'source_food_id': null},
        },
        {
          'item_id': 'item-2',
          'label': 'Test Food B',
          'food_code': null,
          'confidence': 0.65,
          'region': null,
          'portion': {'grams': 80.0, 'household_measure': null, 'estimation_method': 'mock', 'confidence': null},
          'nutrition': {
            'energy_kcal': 100.0,
            'carbohydrate_g': 5.0,
            'sugars_g': 1.0,
            'dietary_fiber_g': 3.0,
            'protein_g': 8.0,
            'fat_g': 6.0,
            'sodium_mg': 300.0,
          },
          'nutrition_source': {'source': 'MOCK', 'source_food_id': null},
        },
      ],
      'totals': {
        'energy_kcal': 300.0,
        'carbohydrate_g': 45.0,
        'sugars_g': null,
        'dietary_fiber_g': 5.0,
        'protein_g': 13.0,
        'fat_g': 7.0,
        'sodium_mg': 310.0,
      },
      'disclaimer': 'Research prototype (J26-IT-352). Not a diagnostic or clinically validated tool.',
    };
