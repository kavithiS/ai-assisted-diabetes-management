import 'dart:convert';
import 'dart:typed_data';

/// A valid 1x1 PNG (generated test image, never a real foot photo).
final Uint8List tinyPng = base64Decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
);

/// Shaped like the C4 mock response. Values are test fixtures, not results.
Map<String, dynamic> footAnalysisJson({String riskBand = 'High', bool isMock = true}) => {
      'analysis_id': '00000000-0000-0000-0000-000000000004',
      'classification': riskBand == 'High' ? 'ulcer' : 'normal',
      'risk_band': riskBand,
      'recommendations': ['Test recommendation one', 'Test recommendation two'],
      'disclaimer': 'Test disclaimer',
      'meta': {'is_mock': isMock, 'model_name': 'mock', 'model_version': '0.0.0'},
    };
