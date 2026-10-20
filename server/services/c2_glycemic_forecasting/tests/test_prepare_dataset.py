"""Tests for C2 preprocessing: genuine pre-meal readings and the fixed participant split.

All data here is synthetic. No CGMacros files are read.
"""

import importlib.util
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

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
    spec.loader.exec_module(module)
    return module


prepare = _load_script("prepare_dataset")
splitter = _load_script("split_dataset")

START = pd.Timestamp("2030-01-01 08:00:00")
MINUTE_NS = 60_000_000_000
MEAL_NUTRITION = {
    "Calories": 550.0,
    "Carbs": 65.0,
    "Protein": 25.0,
    "Fat": 18.0,
    "Fiber": 8.0,
    "Amount Consumed": 100.0,
}
READING_MINUTES = np.arange(0, 601, 15)


def reading_values(count: int) -> np.ndarray:
    """Whole-number readings whose slope changes at most, but not all, readings."""
    return np.array([100.0 + k + (k % 3) * 7 for k in range(count)])


def to_ns(minutes: np.ndarray) -> np.ndarray:
    return np.int64(START.value) + minutes.astype(np.int64) * MINUTE_NS


def make_raw(
    values: np.ndarray,
    meal_minutes: Sequence[int] = (157,),
    libre_gaps: Sequence[tuple[int, int]] = (),
    reading_minutes: np.ndarray = READING_MINUTES,
) -> pd.DataFrame:
    """Minute-level data where Libre is linearly interpolated between genuine readings."""
    minutes = np.arange(int(reading_minutes[-1]) + 1)
    libre = np.interp(minutes, reading_minutes, values)
    for start, end in libre_gaps:
        libre[(minutes >= start) & (minutes < end)] = np.nan

    df = pd.DataFrame(
        {
            "Timestamp": (START + pd.to_timedelta(minutes, unit="min")).astype("datetime64[ns]"),
            "Libre GL": libre,
            "Dexcom GL": libre,
            "Meal Type": pd.Series([None] * len(minutes), dtype=object),
            **{column: np.nan for column in MEAL_NUTRITION},
        }
    )
    for minute in meal_minutes:
        df.loc[minute, "Meal Type"] = "Lunch"
        for column, value in MEAL_NUTRITION.items():
            df.loc[minute, column] = value
    return df


def only_record(raw: pd.DataFrame) -> dict[str, Any]:
    records = prepare.process_participant("001", raw, tolerance_minutes=5)
    assert len(records) == 1
    record: dict[str, Any] = records[0]
    return record


# --- Genuine pre-meal reading -------------------------------------------------------------


def test_premeal_uses_last_genuine_reading_strictly_before_meal() -> None:
    values = reading_values(len(READING_MINUTES))
    raw = make_raw(values, meal_minutes=[157])

    record = only_record(raw)

    # The genuine reading at minute 150, not the interpolated value at minute 156.
    assert record["premeal_libre_gl"] == values[10]
    assert record["premeal_libre_gl_minutes_before"] == 7.0
    assert raw.loc[156, "Libre GL"] != values[10]


@pytest.mark.parametrize("after_meal_value", [40.0, 400.0])
def test_premeal_ignores_readings_after_the_meal(after_meal_value: float) -> None:
    values = reading_values(len(READING_MINUTES))
    changed = values.copy()
    changed[11] = after_meal_value  # genuine reading at minute 165, after the meal at 157

    original_record = only_record(make_raw(values, meal_minutes=[157]))
    changed_raw = make_raw(changed, meal_minutes=[157])
    changed_record = only_record(changed_raw)

    assert changed_record["premeal_libre_gl"] == original_record["premeal_libre_gl"] == values[10]
    # The interpolated minute before the meal does move with the later reading.
    assert changed_raw.loc[156, "Libre GL"] != make_raw(values).loc[156, "Libre GL"]


def test_reading_at_meal_time_is_not_used() -> None:
    values = reading_values(len(READING_MINUTES))

    record = only_record(make_raw(values, meal_minutes=[165]))

    assert record["premeal_libre_gl"] == values[10]
    assert record["premeal_libre_gl_minutes_before"] == 15.0


@pytest.mark.parametrize("offset", [1, 8, 14])
def test_elapsed_minutes_since_genuine_reading(offset: int) -> None:
    values = reading_values(len(READING_MINUTES))

    record = only_record(make_raw(values, meal_minutes=[150 + offset]))

    assert record["premeal_libre_gl"] == values[10]
    assert record["premeal_libre_gl_minutes_before"] == float(offset)


def test_missing_earlier_reading_leaves_premeal_missing() -> None:
    values = reading_values(len(READING_MINUTES))
    # Removes the genuine reading at minute 150; minutes 155-156 remain interpolated.
    raw = make_raw(values, meal_minutes=[157], libre_gaps=[(146, 155)])

    record = only_record(raw)

    assert np.isfinite(raw["Libre GL"].to_numpy(dtype=float)[156])
    assert pd.isna(record["premeal_libre_gl"])
    assert pd.isna(record["premeal_libre_gl_minutes_before"])
    assert record["eligible_for_clean_dataset"] is False
    assert "missing_premeal_glucose" in str(record["exclusion_reasons"])


def test_nutrition_and_targets_are_unchanged() -> None:
    values = reading_values(len(READING_MINUTES))
    raw = make_raw(values, meal_minutes=[157])

    record = only_record(raw)

    assert record["carbs"] == MEAL_NUTRITION["Carbs"]
    assert record["fiber"] == MEAL_NUTRITION["Fiber"]
    for minute in range(15, 241, 15):
        assert record[f"libre_gl_t{minute:03d}"] == raw.loc[157 + minute, "Libre GL"]
    assert record["eligible_for_clean_dataset"] is True


def test_whole_number_interpolated_values_are_not_genuine() -> None:
    reading_minutes = np.arange(0, 301, 15)
    # A slope of 1 mg/dL per minute makes every interpolated value a whole number.
    reading_glucose = np.where(np.arange(len(reading_minutes)) % 2 == 0, 100.0, 115.0)
    minutes = np.arange(301)
    values = np.interp(minutes, reading_minutes, reading_glucose)

    mask = prepare.genuine_reading_mask(to_ns(minutes), values)

    # The first reading has no earlier reading to verify against, so it is rejected.
    assert set(minutes[mask].tolist()) == set(reading_minutes[1:].tolist())


def test_sensor_phase_change_accepts_no_interpolated_values() -> None:
    reading_minutes = np.concatenate([np.arange(0, 721, 15), np.arange(727, 1441, 15)])
    minutes = np.arange(1441)
    values = np.interp(minutes, reading_minutes, reading_values(len(reading_minutes)))

    detected = set(minutes[prepare.genuine_reading_mask(to_ns(minutes), values)].tolist())

    assert detected <= set(reading_minutes.tolist())
    far_from_change = {m for m in reading_minutes[1:].tolist() if abs(m - 724) > 360}
    assert far_from_change <= detected


def test_reading_after_inconsistent_values_is_rejected() -> None:
    minutes = np.arange(int(READING_MINUTES[-1]) + 1)
    values = np.interp(minutes, READING_MINUTES, reading_values(len(READING_MINUTES)))
    values[140] += 0.5  # breaks the straight line between the readings at 135 and 150

    mask = prepare.genuine_reading_mask(to_ns(minutes), values)

    assert not mask[150]
    assert mask[135]
    assert mask[165]


def test_non_increasing_timestamps_are_rejected() -> None:
    minutes = np.array([0, 1, 1, 2])

    with pytest.raises(ValueError, match="strictly increasing"):
        prepare.genuine_reading_mask(to_ns(minutes), np.array([100.0, 101.0, 102.0, 103.0]))


# --- Fixed participant split ---------------------------------------------------------------


def write_manifest(path: Path, splits: dict[str, list[str]]) -> Path:
    path.write_text(json.dumps({"splits": splits}), encoding="utf-8")
    return path


def test_repository_manifest_matches_original_seeded_split() -> None:
    assignment = prepare.load_split_manifest()

    assert Counter(assignment.values()) == {"train": 31, "validation": 7, "test": 7}

    # The original split_dataset.py: sorted integer IDs, default_rng(42) shuffle, 70/15/15.
    participants = np.array(sorted(int(pid) for pid in assignment))
    np.random.default_rng(42).shuffle(participants)
    original = {
        "train": participants[:31],
        "validation": participants[31:38],
        "test": participants[38:],
    }
    for split_name, ids in original.items():
        assert {f"{pid:03d}" for pid in ids} == {
            pid for pid, split in assignment.items() if split == split_name
        }


@pytest.mark.parametrize(("raw_id", "expected"), [(10, "010"), ("7", "007"), (" 045 ", "045")])
def test_participant_ids_are_zero_padded(raw_id: object, expected: str) -> None:
    assert prepare.normalize_participant_id(raw_id) == expected


def test_invalid_participant_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid participant ID"):
        prepare.normalize_participant_id("10.0")


def test_manifest_with_duplicate_participant_is_rejected(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path / "split.json", {"train": ["001"], "validation": ["1"], "test": []}
    )

    with pytest.raises(ValueError, match="more than once"):
        prepare.load_split_manifest(manifest)


def test_only_selected_splits_are_opened_and_assignments_are_kept(tmp_path: Path) -> None:
    data_dir = tmp_path / "raw"
    values = reading_values(len(READING_MINUTES))
    for pid in ("001", "002"):
        folder = data_dir / f"CGMacros-{pid}"
        folder.mkdir(parents=True)
        make_raw(values).to_csv(folder / f"CGMacros-{pid}.csv", index=False)

    # A test participant whose file would be reported as a failure if it were opened.
    test_folder = data_dir / "CGMacros-003"
    test_folder.mkdir()
    (test_folder / "CGMacros-003.csv").write_text("must not be opened\n", encoding="utf-8")

    # Participant 004 has no folder; the others must keep their assignments.
    manifest = write_manifest(
        tmp_path / "split.json",
        {"train": ["001", "004"], "validation": ["002"], "test": ["003"]},
    )

    output_dir = tmp_path / "processed"
    summary = prepare.prepare_dataset(
        data_dir, output_dir, split_manifest=manifest, splits=["train", "validation"]
    )

    assert summary["participant_files_found"] == 2
    assert summary["participants_with_processing_failures"] == []
    assert summary["selected_participants_without_files"] == ["004"]
    clean = pd.read_csv(output_dir / "cgmacros_meal_samples_clean.csv", dtype=str)
    assert dict(zip(clean["participant_id"], clean["split"], strict=True)) == {
        "001": "train",
        "002": "validation",
    }


def test_existing_outputs_are_not_overwritten(tmp_path: Path) -> None:
    data_dir = tmp_path / "raw"
    folder = data_dir / "CGMacros-001"
    folder.mkdir(parents=True)
    make_raw(reading_values(len(READING_MINUTES))).to_csv(folder / "CGMacros-001.csv", index=False)
    output_dir = tmp_path / "processed"
    output_dir.mkdir()
    existing = output_dir / "cgmacros_meal_samples_clean.csv"
    existing.write_text("previous results\n", encoding="utf-8")
    manifest = write_manifest(
        tmp_path / "split.json", {"train": ["001"], "validation": [], "test": []}
    )

    with pytest.raises(FileExistsError):
        prepare.prepare_dataset(data_dir, output_dir, split_manifest=manifest)

    assert existing.read_text(encoding="utf-8") == "previous results\n"


def test_split_files_follow_manifest_labels_without_shared_participants() -> None:
    samples = pd.DataFrame(
        {
            "participant_id": ["001", "001", "002", "003"],
            "split": ["train", "train", "validation", "test"],
        }
    )

    parts = splitter.partition_by_split(samples)

    members = {name: set(part["participant_id"]) for name, part in parts.items()}
    assert members == {"train": {"001"}, "validation": {"002"}, "test": {"003"}}
    assert len(parts["train"]) == 2


def test_unassigned_participant_is_rejected() -> None:
    samples = pd.DataFrame({"participant_id": ["001", "050"], "split": ["train", "unassigned"]})

    with pytest.raises(ValueError, match="050"):
        splitter.partition_by_split(samples)


def test_participant_in_two_splits_is_rejected() -> None:
    samples = pd.DataFrame({"participant_id": ["001", "001"], "split": ["train", "test"]})

    with pytest.raises(ValueError, match="more than one split"):
        splitter.partition_by_split(samples)


def test_samples_without_split_labels_are_rejected() -> None:
    samples = pd.DataFrame({"participant_id": ["001"]})

    with pytest.raises(ValueError, match="prepare_dataset.py"):
        splitter.partition_by_split(samples)
