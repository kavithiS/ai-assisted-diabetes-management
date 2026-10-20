"""Features of a predicted post-meal glucose trajectory, for the C2 dietary-risk classifier.

Training and the API both build classifier inputs here, so the two cannot drift apart. Every
feature uses only information available at prediction time: the user-entered pre-meal glucose,
the meal's nutrition and the GRU forecast. Observed post-meal glucose is never an input.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np

HORIZON_MINUTES = tuple(range(15, 241, 15))

TRAJECTORY_FEATURES = (
    "predicted_peak_glucose",
    "predicted_peak_minutes",
    "peak_change_from_premeal",
    "max_rise",
    "max_rise_rate",
    "predicted_iauc",
)
NUTRITION_FEATURES = (
    "premeal_glucose",
    "calories",
    "carbs",
    "protein",
    "fat",
    "fiber",
    "carb_energy_fraction",
)
# Column order of the classifier input. Saved with the model and checked at load time.
FEATURE_NAMES = NUTRITION_FEATURES + TRAJECTORY_FEATURES

KCAL_PER_GRAM_CARBOHYDRATE = 4.0


@dataclass(frozen=True)
class TrajectoryFeatures:
    """Summary of one predicted trajectory. Glucose values are mg/dL; times are minutes."""

    predicted_peak_glucose: float
    """Highest predicted value."""

    predicted_peak_minutes: int
    """Horizon of the highest predicted value (the earliest, if several are equal)."""

    peak_change_from_premeal: float
    """Highest predicted value minus pre-meal glucose. Negative if every value is lower."""

    max_rise: float
    """Largest increase from any earlier point, pre-meal glucose included. Never negative."""

    max_rise_rate: float
    """Steepest change between consecutive points, in mg/dL per minute. Negative if the
    trajectory only falls."""

    predicted_iauc: float
    """Incremental area above pre-meal glucose (mg/dL x min); area below it counts as zero."""


def _validated(premeal_glucose: float, predictions: Sequence[float]) -> np.ndarray:
    values = np.asarray(predictions, dtype=np.float64)
    if values.shape != (len(HORIZON_MINUTES),):
        raise ValueError(f"Exactly {len(HORIZON_MINUTES)} predictions are required.")
    if not np.isfinite(values).all() or not math.isfinite(premeal_glucose):
        raise ValueError("Glucose values must be finite numbers.")
    if premeal_glucose <= 0:
        raise ValueError("Pre-meal glucose must be greater than 0 mg/dL.")
    return values


def incremental_auc(times: np.ndarray, values: np.ndarray, baseline: float) -> float:
    """Area of `values` above `baseline` by the trapezoid rule, split where a segment crosses it.

    Areas below the baseline count as zero, as in the CGMacros reference iAUC.
    """
    above = values - baseline
    total = 0.0
    for start, end, a, b in zip(times[:-1], times[1:], above[:-1], above[1:], strict=True):
        width = float(end - start)
        if a >= 0 and b >= 0:
            total += (a + b) / 2 * width
        elif a > 0 > b or b > 0 > a:
            # Only the positive triangle up to the crossing point counts.
            positive = max(a, b)
            total += positive * (positive / (abs(a) + abs(b)) * width) / 2
    return float(total)


def extract_trajectory_features(
    premeal_glucose: float, predictions: Sequence[float]
) -> TrajectoryFeatures:
    """Summarise a 16-point forecast at +15, +30, ..., +240 minutes after the meal.

    Pre-meal glucose is treated as the value at minute 0.
    """
    values = _validated(premeal_glucose, predictions)
    times = np.array((0, *HORIZON_MINUTES), dtype=np.float64)
    series = np.concatenate(([premeal_glucose], values))

    peak_index = int(np.argmax(values))
    peak = float(values[peak_index])
    running_minimum = np.minimum.accumulate(series[:-1])
    rises = series[1:] - running_minimum
    slopes = np.diff(series) / np.diff(times)

    return TrajectoryFeatures(
        predicted_peak_glucose=peak,
        predicted_peak_minutes=HORIZON_MINUTES[peak_index],
        peak_change_from_premeal=peak - premeal_glucose,
        max_rise=max(float(rises.max()), 0.0),
        max_rise_rate=float(slopes.max()),
        predicted_iauc=incremental_auc(times, series, premeal_glucose),
    )


def carb_energy_fraction(calories: float, carbs: float) -> float:
    """Share of meal energy from carbohydrate (4 kcal/g); NaN when calories are 0.

    Logged calories need not equal the macronutrient sum, so the value can exceed 1.
    """
    if calories <= 0:
        return math.nan
    return carbs * KCAL_PER_GRAM_CARBOHYDRATE / calories


def build_feature_row(
    premeal_glucose: float,
    calories: float,
    carbs: float,
    protein: float,
    fat: float,
    fiber: float,
    predictions: Sequence[float],
) -> dict[str, float]:
    """Return every classifier input by name, in `FEATURE_NAMES` order."""
    trajectory = extract_trajectory_features(premeal_glucose, predictions)
    row: dict[str, float] = {
        "premeal_glucose": float(premeal_glucose),
        "calories": float(calories),
        "carbs": float(carbs),
        "protein": float(protein),
        "fat": float(fat),
        "fiber": float(fiber),
        "carb_energy_fraction": carb_energy_fraction(calories, carbs),
    }
    row.update({name: float(value) for name, value in asdict(trajectory).items()})
    assert tuple(row) == FEATURE_NAMES
    return row
