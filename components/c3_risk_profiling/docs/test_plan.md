# Test plan - Component 3

Automated tests live in `tests/test_pipeline.py`. They use stand-in models trained on
generated numbers (`tests/conftest.py`), so they run on any machine without the
dataset. Run `python -m pytest -v` from the project root and screenshot the output
into `outputs/reports/`.

**Fill in Actual Result and Status yourself after running the tests.
Never pre-fill results you have not observed.**

| ID | Feature | Input | Expected result | Actual | Status | Evidence |
|---|---|---|---|---|---|---|
| T01 | Data load | Both Bangladesh files | DiaBD 5,288 rows; Narsingdi 496 unique rows | | | `python -m src.data_loader` screenshot |
| T02 | Duplicate removal | Narsingdi raw file | 569 duplicates removed | | | terminal screenshot |
| T03 | Impossible values | BMI 574, pulse 5 | Set to missing | | | `test_impossible_values_become_missing` |
| T04 | Train/test split | DiaBD | Diabetes rate equal in both splits | | | `python -m src.preprocess` screenshot |
| T05 | Model training | Train split | 3 models x 2 feature sets trained, CV reported, one selected per set | | | `models/` + `model_comparison.json` |
| T06 | Prediction range | Example patient | Status ok, probability 0-1, valid band | | | `test_prediction_returns_valid_probability_and_band` |
| T07 | Model choice | With / without glucose | with_glucose / without_glucose model used | | | `test_glucose_decides_which_model_is_used` |
| T08 | Critical missing | Age + BMI only | insufficient_data, no band | | | `test_missing_critical_field_returns_no_band` |
| T09 | Optional missing | No pulse | ok, pulse listed in imputed_fields | | | `test_missing_optional_field_is_reported_not_hidden` |
| T10 | Invalid input | BMI 500, stroke = 3 | invalid_input | | | `test_impossible_values_are_rejected` |
| T11 | Feature order | Example patient | Column order matches training | | | `test_feature_order_matches_training` |
| T12 | Directional sanity | Low vs high profile | High profile scores higher | | | `test_higher_risk_profile_scores_higher` |
| T13 | Referral | High-band result | Referral note present only for High | | | `test_high_band_carries_referral` |
| T14 | Risk bands | 0.01 / 0.10 / 0.50 | Low / Moderate / High | | | `test_risk_bands_are_ordered` |
| T15 | Band cut-offs | Scores + labels | Cut-offs from data, low <= high | | | `test_thresholds_come_from_data_and_are_ordered` |
| T16 | Calibration | Scores | Ranking unchanged after calibration | | | `test_calibration_keeps_ranking` |
| T17 | Synthetic data | Training rows | Same columns, class balance kept, binary stays 0/1, < 5% copies | | | `test_synthetic_rows_keep_shape_labels_and_binary_columns` |
| T18 | SHAP + LIME | Both models | 5 SHAP factors, LIME factors, agreement 0-1, factor types | | | `test_explanations_for_both_models` |
| T19 | No explanation on bad data | Age only | Only the prediction status returned | | | `test_insufficient_data_skips_explanations` |
| T20 | UI end to end | Presets in Streamlit | Band, summary, SHAP chart, LIME table, no errors | | | app screenshot |
| T21 | Disclaimer | Any prediction | Non-diagnostic warning always shown | | | app screenshot |
