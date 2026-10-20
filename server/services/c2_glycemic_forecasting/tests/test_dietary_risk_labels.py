"""Tests for the post-meal response label. Synthetic data only; no CGMacros files are read."""

import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd
import pytest

TRAINING_DIR = Path(__file__).resolve().parents[1] / "training"


def _load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"c2_training_{name}", TRAINING_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look up their module by name
    spec.loader.exec_module(module)
    return module


labels = _load_script("build_dietary_risk_labels")

START = pd.Timestamp("2030-01-01 08:00:00")
MINUTE_NS = 60_000_000_000
MEAL_NS = int(START.value)


def readings(offsets: Sequence[float], values: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    times = MEAL_NS + (np.asarray(offsets, dtype=np.float64) * MINUTE_NS).astype(np.int64)
    return times, np.asarray(values, dtype=np.float64)


def full_window(values: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    """Readings at +15, +30, ..., +240 minutes."""
    return readings(range(15, 241, 15), values)


# --- label_meal --------------------------------------------------------------------------


def test_reading_above_180_is_positive() -> None:
    values = [120.0] * 16
    values[5] = 181.0

    result = labels.label_meal(*full_window(values), MEAL_NS)

    assert result.label == 1
    assert result.observed_max_glucose == 181
    assert result.readings_in_window == 16
    assert result.exclusion_reason == ""


def test_reading_of_exactly_180_is_negative() -> None:
    values = [120.0] * 16
    values[5] = 180.0

    assert labels.label_meal(*full_window(values), MEAL_NS).label == 0


@pytest.mark.parametrize("outside_offset", [-5, 0, 14, 241, 250])
def test_readings_outside_the_window_are_ignored(outside_offset: float) -> None:
    offsets = [*range(15, 241, 15), outside_offset]
    values = [120.0] * 16 + [300.0]

    times, vals = readings(offsets, values)
    order = np.argsort(times)
    result = labels.label_meal(times[order], vals[order], MEAL_NS)
    assert result.label == 0
    assert result.observed_max_glucose == 120


def test_window_edges_are_inclusive() -> None:
    values = [120.0] * 16
    values[0] = 200.0  # at exactly +15 minutes
    assert labels.label_meal(*full_window(values), MEAL_NS).label == 1

    values = [120.0] * 16
    values[-1] = 200.0  # at exactly +240 minutes
    assert labels.label_meal(*full_window(values), MEAL_NS).label == 1


def test_off_phase_readings_with_jitter_are_accepted() -> None:
    # Sensor phase 7 minutes after the meal: readings at +22, +37, ..., +232 and one 16-minute step.
    offsets = [22.0 + 15 * k for k in range(15)]
    offsets[7] += 1
    result = labels.label_meal(*readings(offsets, [150.0] * 15), MEAL_NS)

    assert result.label == 0
    assert result.max_gap_minutes == pytest.approx(16)


def test_gap_in_readings_invalidates_label_even_if_observed_values_are_low() -> None:
    offsets = [o for o in range(15, 241, 15) if not 90 <= o <= 150]
    result = labels.label_meal(*readings(offsets, [120.0] * len(offsets)), MEAL_NS)

    assert result.label is None
    assert result.exclusion_reason == "reading_gap"
    assert result.max_gap_minutes == 90  # readings at +75 and +165


def test_gap_invalidates_label_even_if_a_value_is_above_threshold() -> None:
    # Both classes need full coverage, so positives are not easier to keep than negatives.
    offsets = [15.0, 30.0, 45.0, 240.0]
    result = labels.label_meal(*readings(offsets, [200.0, 120.0, 120.0, 120.0]), MEAL_NS)

    assert result.label is None


def test_missing_start_or_end_of_window_is_a_gap() -> None:
    late_start = labels.label_meal(*readings(range(45, 241, 15), [120.0] * 14), MEAL_NS)
    early_end = labels.label_meal(*readings(range(15, 211, 15), [120.0] * 14), MEAL_NS)

    assert late_start.exclusion_reason == early_end.exclusion_reason == "reading_gap"


def test_no_readings_in_window() -> None:
    result = labels.label_meal(*readings([-30.0, 300.0], [120.0, 120.0]), MEAL_NS)

    assert result.label is None
    assert result.exclusion_reason == "no_readings"


# --- isolation ---------------------------------------------------------------------------


def test_minutes_since_previous_meal_uses_strictly_earlier_meals() -> None:
    meals = np.array([MEAL_NS - 300 * MINUTE_NS, MEAL_NS - 30 * MINUTE_NS, MEAL_NS])

    assert labels.minutes_since_previous_meal(meals, MEAL_NS) == 30
    assert np.isnan(labels.minutes_since_previous_meal(meals[2:], MEAL_NS))


# --- label_participant on synthetic raw data ---------------------------------------------


def make_raw(reading_values: np.ndarray, meal_minutes: Sequence[int]) -> pd.DataFrame:
    """Minute-level data, Libre linearly interpolated between readings every 15 minutes."""
    reading_minutes = np.arange(0, 15 * len(reading_values), 15)
    minutes = np.arange(int(reading_minutes[-1]) + 1)
    libre = np.interp(minutes, reading_minutes, reading_values)
    df = pd.DataFrame(
        {
            "Timestamp": (START + pd.to_timedelta(minutes, unit="min")).astype("datetime64[ns]"),
            "Libre GL": libre,
            "Dexcom GL": libre,
            "Meal Type": pd.Series([None] * len(minutes), dtype=object),
            **{c: np.nan for c in ("Calories", "Carbs", "Protein", "Fat", "Fiber")},
            "Amount Consumed": np.nan,
        }
    )
    for minute in meal_minutes:
        df.loc[minute, "Meal Type"] = "Lunch"
        df.loc[minute, ["Calories", "Carbs", "Protein", "Fat", "Fiber"]] = 100.0
    return df


def base_values(count: int) -> np.ndarray:
    # Whole numbers whose slope changes at every reading, so readings are detectably genuine.
    return np.array([100.0 + (k % 2) * 9 + (k % 3) * 4 for k in range(count)])


def meal_frame(minutes: Sequence[int]) -> pd.DataFrame:
    stamps = [(START + pd.Timedelta(minutes=m)).isoformat() for m in minutes]
    return pd.DataFrame({"meal_timestamp": stamps})


def test_interpolated_value_borrowed_from_outside_the_window_does_not_label() -> None:
    values = base_values(60)
    # Meal at minute 307, off the sensor phase. Genuine readings at +233 (minute 540) and
    # +248 (minute 555), the second one outside the window.
    values[555 // 15] = 300.0
    raw = make_raw(values, meal_minutes=[307])

    # The +240 grid value (minute 547) is interpolated towards 300 and is above 180, so a
    # grid-based label would be positive although no genuine reading in the window is.
    assert float(raw["Libre GL"].iloc[547]) > 180

    result = labels.label_participant(raw, meal_frame([307])).iloc[0]

    assert result[labels.LABEL_NAME] == 0
    assert result["label_valid"]


def test_genuine_peak_inside_window_labels_positive() -> None:
    values = base_values(60)
    values[(300 + 90) // 15] = 230.0
    result = labels.label_participant(make_raw(values, [300]), meal_frame([300])).iloc[0]

    assert result[labels.LABEL_NAME] == 1
    assert result["observed_max_glucose"] == 230


def test_meal_preceded_within_4h_by_any_logged_meal_is_not_isolated() -> None:
    raw = make_raw(base_values(80), meal_minutes=[100, 300, 700])
    # Only minutes 300 and 700 are in the clean set; minute 100 is a logged meal outside it.
    result = labels.label_participant(raw, meal_frame([300, 700]))

    assert result["minutes_since_previous_meal"].tolist() == [200, 400]
    assert result["previous_meal_within_4h"].tolist() == [True, False]
    assert result["isolated_meal"].tolist() == [False, True]


# --- build_labels -------------------------------------------------------------------------


def write_dataset(tmp_path: Path, splits: dict[str, str]) -> tuple[Path, Path]:
    data_dir = tmp_path / "raw"
    rows = []
    for participant_id, split in splits.items():
        folder = data_dir / f"CGMacros-{participant_id}"
        folder.mkdir(parents=True)
        values = base_values(80)
        values[(300 + 60) // 15] = 220.0 if participant_id == "001" else values[24]
        make_raw(values, meal_minutes=[300]).to_csv(folder / f"{folder.name}.csv", index=False)
        rows.append(
            {
                "participant_id": participant_id,
                "split": split,
                "meal_timestamp": (START + pd.Timedelta(minutes=300)).isoformat(),
                "next_meal_within_4h": False,
            }
        )
    clean_file = tmp_path / "clean.csv"
    pd.DataFrame(rows).to_csv(clean_file, index=False)
    return data_dir, clean_file


def test_build_labels_writes_labels_and_summary(tmp_path: Path) -> None:
    data_dir, clean_file = write_dataset(tmp_path, {"001": "train", "002": "validation"})
    output = tmp_path / "out"

    summary = labels.build_labels(data_dir, clean_file, output)

    table = pd.read_csv(output / "dietary_risk_labels.csv", dtype={"participant_id": str})
    assert table.set_index("participant_id")[labels.LABEL_NAME].to_dict() == {"001": 1, "002": 0}
    assert table["primary_eligible"].all()
    per_split = summary["per_split"]
    assert isinstance(per_split, dict)
    assert per_split["train"]["primary_positive"] == 1
    saved = json.loads((output / "dietary_risk_labels_summary.json").read_text(encoding="utf-8"))
    assert saved["threshold_mg_dl"] == 180


def test_build_labels_never_opens_test_participants(tmp_path: Path) -> None:
    data_dir, clean_file = write_dataset(tmp_path, {"001": "train", "009": "test"})
    # If the test participant's file were opened, reading this would fail.
    (data_dir / "CGMacros-009" / "CGMacros-009.csv").write_text(
        "not,a,valid\nfile", encoding="utf-8"
    )

    labels.build_labels(data_dir, clean_file, tmp_path / "out")

    table = pd.read_csv(tmp_path / "out" / "dietary_risk_labels.csv", dtype={"participant_id": str})
    assert table["participant_id"].tolist() == ["001"]


def test_build_labels_refuses_test_split(tmp_path: Path) -> None:
    data_dir, clean_file = write_dataset(tmp_path, {"001": "train"})

    with pytest.raises(ValueError, match="sealed"):
        labels.build_labels(data_dir, clean_file, tmp_path / "out", splits=("train", "test"))


def test_build_labels_refuses_to_overwrite(tmp_path: Path) -> None:
    data_dir, clean_file = write_dataset(tmp_path, {"001": "train"})
    labels.build_labels(data_dir, clean_file, tmp_path / "out")

    with pytest.raises(FileExistsError):
        labels.build_labels(data_dir, clean_file, tmp_path / "out")


def test_build_labels_rejects_overlapping_or_duplicate_meals(tmp_path: Path) -> None:
    data_dir, clean_file = write_dataset(tmp_path, {"001": "train"})
    clean = pd.read_csv(clean_file, dtype={"participant_id": str})

    pd.concat([clean, clean]).to_csv(clean_file, index=False)
    with pytest.raises(ValueError, match="duplicate"):
        labels.build_labels(data_dir, clean_file, tmp_path / "a")

    clean.assign(next_meal_within_4h=True).to_csv(clean_file, index=False)
    with pytest.raises(ValueError, match="followed within 4 hours"):
        labels.build_labels(data_dir, clean_file, tmp_path / "b")
