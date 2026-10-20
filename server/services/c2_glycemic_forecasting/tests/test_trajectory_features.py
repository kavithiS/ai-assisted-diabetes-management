"""Tests for trajectory feature extraction. Synthetic trajectories with hand-computed values."""

import math

import numpy as np
import pytest

from c2_glycemic_forecasting.trajectory_features import (
    FEATURE_NAMES,
    HORIZON_MINUTES,
    build_feature_row,
    carb_energy_fraction,
    extract_trajectory_features,
    incremental_auc,
)


def _flat(value: float) -> list[float]:
    return [value] * len(HORIZON_MINUTES)


def test_single_peak_trajectory() -> None:
    # Rises 10 mg/dL per step to 160 at +60 min, then falls back by 10 per step.
    predictions = [110, 120, 130, 160, 150, 140, 130, 120, 110, 100, 100, 100, 100, 100, 100, 100]

    features = extract_trajectory_features(100.0, predictions)

    assert features.predicted_peak_glucose == 160
    assert features.predicted_peak_minutes == 60
    assert features.peak_change_from_premeal == 60
    assert features.max_rise == 60
    assert features.max_rise_rate == pytest.approx(30 / 15)  # 130 -> 160 in 15 minutes


def test_peak_ties_use_earliest_horizon() -> None:
    predictions = [100.0, 150.0, 150.0, *([100.0] * 13)]

    assert extract_trajectory_features(100.0, predictions).predicted_peak_minutes == 30


def test_max_rise_counts_from_a_later_dip_not_only_from_premeal() -> None:
    # Falls from 150 to 90 at +30 min, then climbs to 140: rise 50 from the dip, peak change 0.
    predictions = [120.0, 90.0, 140.0, *([100.0] * 13)]

    features = extract_trajectory_features(150.0, predictions)

    assert features.predicted_peak_glucose == 140
    assert features.peak_change_from_premeal == -10
    assert features.max_rise == 50


def test_falling_trajectory_has_zero_rise_and_negative_rate() -> None:
    predictions = [200.0 - 5 * step for step in range(1, 17)]

    features = extract_trajectory_features(200.0, predictions)

    assert features.max_rise == 0
    assert features.peak_change_from_premeal == -5
    assert features.max_rise_rate == pytest.approx(-5 / 15)
    assert features.predicted_iauc == 0


def test_iauc_of_flat_trajectory_is_zero() -> None:
    assert extract_trajectory_features(120.0, _flat(120.0)).predicted_iauc == 0


def test_iauc_of_constant_offset_is_offset_times_duration() -> None:
    # Premeal 100 then 120 throughout: the first segment is a trapezoid 0 -> 20 over 15 min.
    features = extract_trajectory_features(100.0, _flat(120.0))

    assert features.predicted_iauc == pytest.approx(20 * 15 / 2 + 20 * 225)


def test_iauc_counts_only_positive_triangle_at_crossings() -> None:
    times = np.array([0.0, 10.0])
    # +10 down to -30: crosses at 2.5 minutes, positive triangle 10 * 2.5 / 2.
    assert incremental_auc(times, np.array([110.0, 70.0]), 100.0) == pytest.approx(12.5)
    # -30 up to +10: the mirror image.
    assert incremental_auc(times, np.array([70.0, 110.0]), 100.0) == pytest.approx(12.5)
    assert incremental_auc(times, np.array([70.0, 80.0]), 100.0) == 0


@pytest.mark.parametrize(
    ("premeal", "predictions", "message"),
    [
        (100.0, [100.0] * 15, "Exactly 16"),
        (100.0, [100.0] * 15 + [math.nan], "finite"),
        (math.inf, [100.0] * 16, "finite"),
        (0.0, [100.0] * 16, "greater than 0"),
    ],
)
def test_invalid_inputs_are_rejected(
    premeal: float, predictions: list[float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        extract_trajectory_features(premeal, predictions)


def test_carb_energy_fraction() -> None:
    assert carb_energy_fraction(400.0, 50.0) == pytest.approx(0.5)
    assert math.isnan(carb_energy_fraction(0.0, 10.0))


def test_feature_row_has_fixed_names_and_order() -> None:
    row = build_feature_row(100.0, 400.0, 50.0, 20.0, 10.0, 5.0, _flat(130.0))

    assert tuple(row) == FEATURE_NAMES
    assert row["premeal_glucose"] == 100
    assert row["carb_energy_fraction"] == pytest.approx(0.5)
    assert row["predicted_peak_glucose"] == 130
    assert all(isinstance(value, float) for value in row.values())
