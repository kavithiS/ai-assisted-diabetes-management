"""Tests for the 120-minute sequence dataset and the sequence GRU.

All data here is synthetic. No CGMacros files are read.
"""

import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pandas as pd
import pytest
import torch

TRAINING_DIR = Path(__file__).resolve().parents[1] / "training"


def _load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"c2_training_{name}", TRAINING_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look up their defining module
    spec.loader.exec_module(module)
    return module


builder = _load_script("build_sequence_dataset")
trainer = _load_script("train_sequence_gru")

START = pd.Timestamp("2030-01-01 08:00:00")
MINUTE_NS = 60_000_000_000
READING_MINUTES = np.arange(0, 601, 15)
MEAL = 307  # 7 minutes after the genuine reading at minute 300
NUTRITION = {"Calories": 550.0, "Carbs": 65.0, "Protein": 25.0, "Fat": 18.0, "Fiber": 8.0}


def reading_values(count: int, offset: float = 100.0) -> np.ndarray:
    """Whole-number readings whose slope changes at most readings."""
    return np.array([offset + k + (k % 3) * 7 for k in range(count)])


def make_raw(values: np.ndarray, libre_gaps: Sequence[tuple[int, int]] = ()) -> pd.DataFrame:
    """Minute-level data with Libre linearly interpolated between genuine readings."""
    minutes = np.arange(int(READING_MINUTES[-1]) + 1)
    libre = np.interp(minutes, READING_MINUTES, values)
    for start, end in libre_gaps:
        libre[(minutes >= start) & (minutes < end)] = np.nan
    return pd.DataFrame(
        {
            "Timestamp": (START + pd.to_timedelta(minutes, unit="min")).astype("datetime64[ns]"),
            "Libre GL": libre,
            "Dexcom GL": libre,
            "Meal Type": pd.Series([None] * len(minutes), dtype=object),
            **{column: np.nan for column in NUTRITION},
        }
    )


def meal_row(participant: str, split: str, minute: int, values: np.ndarray) -> dict[str, Any]:
    """A corrected-dataset meal row whose premeal is the last genuine reading before it."""
    last = int(np.searchsorted(READING_MINUTES, minute, side="left")) - 1
    targets = np.interp(minute + np.arange(15, 241, 15), READING_MINUTES, values)
    return {
        "participant_id": participant,
        "split": split,
        "meal_timestamp": (START + pd.Timedelta(minutes=minute)).isoformat(),
        "premeal_libre_gl": float(values[last]),
        "premeal_libre_gl_minutes_before": float(minute - READING_MINUTES[last]),
        **{column.lower(): value for column, value in NUTRITION.items()},
        **dict(zip(builder.TARGET_COLUMNS, targets.tolist(), strict=True)),
    }


def sequences_for(raw: pd.DataFrame, meals: list[dict[str, Any]]) -> tuple[list[Any], list[Any]]:
    rows, exclusions = builder.participant_sequences(raw, pd.DataFrame(meals))
    return rows, exclusions


# --- Sequence construction ---------------------------------------------------------------


def test_history_is_oldest_first_and_strictly_before_meal() -> None:
    values = reading_values(len(READING_MINUTES))

    (row,), exclusions = sequences_for(make_raw(values), [meal_row("001", "train", MEAL, values)])

    assert exclusions == []
    glucose = [row[column] for column in builder.GLUCOSE_COLUMNS]
    minutes = [row[column] for column in builder.MINUTES_COLUMNS]
    assert minutes == [112.0, 97.0, 82.0, 67.0, 52.0, 37.0, 22.0, 7.0]
    assert glucose == values[13:21].tolist()  # readings at minutes 195 ... 300


def test_reading_at_meal_time_is_excluded_and_120_minutes_is_included() -> None:
    values = reading_values(len(READING_MINUTES))

    (row,), _ = sequences_for(make_raw(values), [meal_row("001", "train", 300, values)])

    minutes = [row[column] for column in builder.MINUTES_COLUMNS]
    assert minutes[-1] == 15.0  # the reading at minute 300 itself is not used
    assert minutes[0] == 120.0


def test_future_readings_do_not_change_the_history() -> None:
    values = reading_values(len(READING_MINUTES))
    changed = values.copy()
    changed[21:] = 400.0  # every genuine reading after the meal at minute 307

    (original,), _ = sequences_for(make_raw(values), [meal_row("001", "train", MEAL, values)])
    (after_change,), _ = sequences_for(make_raw(changed), [meal_row("001", "train", MEAL, changed)])

    history = [*builder.GLUCOSE_COLUMNS, *builder.MINUTES_COLUMNS]
    assert [original[c] for c in history] == [after_change[c] for c in history]


def test_missing_reading_inside_window_excludes_meal() -> None:
    values = reading_values(len(READING_MINUTES))
    raw = make_raw(values, libre_gaps=[(236, 245)])  # removes the reading at minute 240

    rows, exclusions = sequences_for(raw, [meal_row("001", "train", MEAL, values)])

    assert rows == []
    assert [e["reason"] for e in exclusions] == ["missing_reading_in_120_minute_window"]


def test_too_little_history_excludes_meal() -> None:
    values = reading_values(len(READING_MINUTES))

    rows, exclusions = sequences_for(make_raw(values), [meal_row("001", "train", 97, values)])

    assert rows == []
    assert [e["reason"] for e in exclusions] == ["fewer_than_8_readings_before_meal"]


def test_newest_reading_must_match_corrected_premeal() -> None:
    values = reading_values(len(READING_MINUTES))
    meal = meal_row("001", "train", MEAL, values)
    meal["premeal_libre_gl"] += 1.0

    with pytest.raises(ValueError, match="premeal_libre_gl"):
        sequences_for(make_raw(values), [meal])


def test_build_uses_each_participants_own_data_and_skips_other_splits(tmp_path: Path) -> None:
    raw_dir, samples_dir = tmp_path / "raw", tmp_path / "samples"
    samples_dir.mkdir()
    levels = {"001": ("train", 100.0), "002": ("validation", 200.0)}
    for pid, (split, level) in levels.items():
        values = reading_values(len(READING_MINUTES), level)
        folder = raw_dir / f"CGMacros-{pid}"
        folder.mkdir(parents=True)
        make_raw(values).to_csv(folder / f"CGMacros-{pid}.csv", index=False)
        pd.DataFrame([meal_row(pid, split, MEAL, values)]).to_csv(
            samples_dir / f"cgmacros_{split}.csv", index=False
        )
    # A test participant whose raw file would fail to parse if it were opened.
    test_folder = raw_dir / "CGMacros-003"
    test_folder.mkdir()
    (test_folder / "CGMacros-003.csv").write_text("must not be opened\n", encoding="utf-8")
    manifest = tmp_path / "split.json"
    manifest.write_text(
        json.dumps({"splits": {"train": ["001"], "validation": ["002"], "test": ["003"]}}),
        encoding="utf-8",
    )

    summary = builder.build_sequence_dataset(
        raw_dir, samples_dir, tmp_path / "out", split_manifest=manifest
    )

    assert summary["sequences_by_split"] == {
        "train": {"meals": 1, "participants": 1},
        "validation": {"meals": 1, "participants": 1},
    }
    for split, (lowest, highest) in (("train", (100, 200)), ("validation", (200, 300))):
        out = pd.read_csv(tmp_path / "out" / f"cgmacros_sequence_{split}.csv", dtype=str)
        glucose = out[list(builder.GLUCOSE_COLUMNS)].astype(float).to_numpy()
        assert lowest <= glucose.min() and glucose.max() < highest
    assert not (tmp_path / "out" / "cgmacros_sequence_test.csv").exists()


def test_build_refuses_participants_from_another_split(tmp_path: Path) -> None:
    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    values = reading_values(len(READING_MINUTES))
    pd.DataFrame([meal_row("003", "train", MEAL, values)]).to_csv(
        samples_dir / "cgmacros_train.csv", index=False
    )
    manifest = tmp_path / "split.json"
    manifest.write_text(
        json.dumps({"splits": {"train": ["001"], "validation": [], "test": ["003"]}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not assigned to train"):
        builder.build_sequence_dataset(
            tmp_path / "raw", samples_dir, tmp_path / "out", ("train",), manifest
        )


# --- Sequence GRU ------------------------------------------------------------------------


def write_sequence_csv(path: Path, split: str, participants: list[str], seed: int) -> None:
    rng = np.random.default_rng(seed)
    rows = []
    for index in range(24):
        glucose = rng.uniform(80, 160, size=8)
        rows.append(
            {
                "participant_id": participants[index % len(participants)],
                "split": split,
                **dict(zip(trainer.GLUCOSE_COLUMNS, glucose, strict=True)),
                **dict(zip(trainer.MINUTES_COLUMNS, np.arange(112, 0, -15.0), strict=True)),
                **dict(zip(trainer.NUTRITION_COLUMNS, rng.uniform(1, 80, size=5), strict=True)),
                **dict(
                    zip(trainer.TARGET_COLUMNS, glucose[-1] + rng.normal(0, 5, 16), strict=True)
                ),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


def test_model_output_shape() -> None:
    model = trainer.SequenceGlucoseGRU()

    output = model(torch.zeros(5, 8, 2), torch.zeros(5, 5))

    assert output.shape == (5, 16)


def test_model_reads_history_in_order() -> None:
    torch.manual_seed(0)
    model = trainer.SequenceGlucoseGRU()
    history = torch.randn(1, 8, 2)

    forward = model(history, torch.zeros(1, 5))
    reversed_order = model(history.flip(1), torch.zeros(1, 5))

    assert not torch.allclose(forward, reversed_order)


def test_normalization_uses_training_data_only(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001", "002"], seed=1)
    data = trainer.read_sequences(tmp_path / "train.csv", "train")

    norm = trainer.fit_normalization(data)

    assert np.allclose(norm["history_mean"], data.history.reshape(-1, 2).mean(axis=0))
    assert np.allclose(norm["target_mean"], data.targets.mean(axis=0))


def test_rows_from_another_split_are_rejected(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "test", ["001"], seed=1)

    with pytest.raises(ValueError, match="not in the train split"):
        trainer.read_sequences(tmp_path / "train.csv", "train")


def test_history_at_or_after_meal_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "train.csv"
    write_sequence_csv(path, "train", ["001"], seed=1)
    df = pd.read_csv(path)
    df.loc[0, "history_minutes_before_8"] = 0
    df.to_csv(path, index=False)

    with pytest.raises(ValueError, match="at/after the meal"):
        trainer.read_sequences(path, "train")


def test_participant_overlap_is_rejected(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001", "002"], seed=1)
    write_sequence_csv(tmp_path / "validation.csv", "validation", ["002"], seed=2)

    with pytest.raises(ValueError, match="leakage"):
        trainer.train(tmp_path / "train.csv", tmp_path / "validation.csv", tmp_path / "out", 1)


def test_inputs_never_include_targets() -> None:
    inputs = {*trainer.GLUCOSE_COLUMNS, *trainer.MINUTES_COLUMNS, *trainer.NUTRITION_COLUMNS}

    assert not any(column.startswith("libre_gl_t") for column in inputs)


def test_training_writes_results_and_refuses_to_overwrite(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001", "002"], seed=1)
    write_sequence_csv(tmp_path / "validation.csv", "validation", ["003"], seed=2)
    output_dir = tmp_path / "out"

    results = trainer.train(tmp_path / "train.csv", tmp_path / "validation.csv", output_dir, 2)

    assert results["validation_rows"] == 24
    assert len(results["validation_horizon_metrics"]) == 16
    assert np.isfinite(results["validation_metrics"]["mae_mg_dl"])
    for name in trainer.OUTPUT_FILES:
        assert (output_dir / name).exists()
    with pytest.raises(FileExistsError):
        trainer.train(tmp_path / "train.csv", tmp_path / "validation.csv", output_dir, 2)


def test_training_is_reproducible(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001", "002"], seed=1)
    write_sequence_csv(tmp_path / "validation.csv", "validation", ["003"], seed=2)

    first = trainer.train(tmp_path / "train.csv", tmp_path / "validation.csv", tmp_path / "a", 3)
    second = trainer.train(tmp_path / "train.csv", tmp_path / "validation.csv", tmp_path / "b", 3)

    assert first["validation_metrics"] == second["validation_metrics"]
