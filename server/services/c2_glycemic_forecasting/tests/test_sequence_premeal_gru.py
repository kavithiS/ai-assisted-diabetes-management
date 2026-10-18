"""Tests for the experimental sequence GRU with a direct premeal glucose input.

All data here is synthetic. No CGMacros files are read.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

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
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


premeal_gru = _load_script("train_sequence_premeal_gru")
base = premeal_gru.base


def write_sequence_csv(path: Path, split: str, participants: list[str], seed: int) -> None:
    rng = np.random.default_rng(seed)
    rows = []
    for index in range(24):
        glucose = rng.uniform(80, 160, size=8)
        rows.append(
            {
                "participant_id": participants[index % len(participants)],
                "split": split,
                "meal_timestamp": f"2030-01-01T{index:02d}:00:00",
                **dict(zip(base.GLUCOSE_COLUMNS, glucose, strict=True)),
                **dict(zip(base.MINUTES_COLUMNS, np.arange(112, 0, -15.0), strict=True)),
                **dict(zip(base.NUTRITION_COLUMNS, rng.uniform(1, 80, size=5), strict=True)),
                **dict(zip(base.TARGET_COLUMNS, glucose[-1] + rng.normal(0, 5, 16), strict=True)),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


def test_model_accepts_documented_shapes() -> None:
    model = premeal_gru.SequencePremealGRU()

    output = model(torch.zeros(5, 8, 2), torch.zeros(5, 5), torch.zeros(5, 1))

    assert output.shape == (5, 16)
    assert model.head[0].in_features == 38


def test_premeal_input_is_the_newest_history_reading(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001"], seed=1)
    frame = pd.read_csv(tmp_path / "train.csv")
    data = base.read_sequences(tmp_path / "train.csv", "train")

    premeal = premeal_gru.premeal_values(data)

    assert premeal.shape == (24, 1)
    assert np.allclose(premeal[:, 0], frame["history_glucose_8"])
    assert not np.allclose(premeal[:, 0], frame["history_glucose_1"])
    assert premeal_gru.PREMEAL_COLUMN == "history_glucose_8"


def test_prediction_depends_on_direct_premeal_value() -> None:
    torch.manual_seed(0)
    model = premeal_gru.SequencePremealGRU()
    history, nutrition = torch.randn(1, 8, 2), torch.randn(1, 5)

    low = model(history, nutrition, torch.tensor([[-1.0]]))
    high = model(history, nutrition, torch.tensor([[1.0]]))

    assert not torch.allclose(low, high)


def test_model_reads_history_in_order() -> None:
    torch.manual_seed(0)
    model = premeal_gru.SequencePremealGRU()
    history = torch.randn(1, 8, 2)

    forward = model(history, torch.zeros(1, 5), torch.zeros(1, 1))
    reversed_order = model(history.flip(1), torch.zeros(1, 5), torch.zeros(1, 1))

    assert not torch.allclose(forward, reversed_order)


def test_premeal_normalization_uses_training_data_only(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001", "002"], seed=1)
    data = base.read_sequences(tmp_path / "train.csv", "train")

    norm = premeal_gru.fit_normalization(data)

    assert np.allclose(norm["premeal_mean"], data.history[:, -1, 0].mean())
    assert np.allclose(norm["premeal_std"], data.history[:, -1, 0].std())
    assert np.allclose(norm["history_mean"], base.fit_normalization(data)["history_mean"])


def test_missing_history_reading_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "train.csv"
    write_sequence_csv(path, "train", ["001"], seed=1)
    frame = pd.read_csv(path)
    frame.loc[3, "history_glucose_5"] = np.nan
    frame.to_csv(path, index=False)

    with pytest.raises(ValueError, match="missing or non-finite"):
        premeal_gru.train(path, path, tmp_path / "out", 1)


def test_reading_at_meal_time_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "train.csv"
    write_sequence_csv(path, "train", ["001"], seed=1)
    frame = pd.read_csv(path)
    frame.loc[0, "history_minutes_before_8"] = 0
    frame.to_csv(path, index=False)

    with pytest.raises(ValueError, match="at/after the meal"):
        premeal_gru.train(path, path, tmp_path / "out", 1)


def test_participant_overlap_is_rejected(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001", "002"], seed=1)
    write_sequence_csv(tmp_path / "validation.csv", "validation", ["002"], seed=2)

    with pytest.raises(ValueError, match="leakage"):
        premeal_gru.train(tmp_path / "train.csv", tmp_path / "validation.csv", tmp_path / "o", 1)


def test_rows_from_another_split_are_rejected(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001"], seed=1)
    write_sequence_csv(tmp_path / "validation.csv", "test", ["002"], seed=2)

    with pytest.raises(ValueError, match="not in the validation split"):
        premeal_gru.train(tmp_path / "train.csv", tmp_path / "validation.csv", tmp_path / "o", 1)


def test_future_targets_do_not_affect_predictions(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001"], seed=1)
    path = tmp_path / "validation.csv"
    write_sequence_csv(path, "validation", ["002"], seed=2)
    changed_path = tmp_path / "validation_changed.csv"
    changed = pd.read_csv(path)
    changed[list(base.TARGET_COLUMNS)] = 999.0
    changed.to_csv(changed_path, index=False)
    norm = premeal_gru.fit_normalization(base.read_sequences(tmp_path / "train.csv", "train"))
    torch.manual_seed(0)
    model = premeal_gru.SequencePremealGRU()

    original = premeal_gru.predict(model, base.read_sequences(path, "validation"), norm)
    after = premeal_gru.predict(model, base.read_sequences(changed_path, "validation"), norm)

    assert np.array_equal(original, after)


def test_training_saves_per_meal_predictions_and_refuses_overwrite(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001", "002"], seed=1)
    write_sequence_csv(tmp_path / "validation.csv", "validation", ["003"], seed=2)
    out = tmp_path / "out"

    results = premeal_gru.train(tmp_path / "train.csv", tmp_path / "validation.csv", out, 2)

    assert len(results["validation_horizon_metrics"]) == 16
    predictions = pd.read_csv(out / "validation_predictions.csv")
    assert predictions.shape == (24, 18)
    for name in premeal_gru.OUTPUT_FILES:
        assert (out / name).exists()
    with pytest.raises(FileExistsError):
        premeal_gru.train(tmp_path / "train.csv", tmp_path / "validation.csv", out, 2)


def test_training_is_reproducible(tmp_path: Path) -> None:
    write_sequence_csv(tmp_path / "train.csv", "train", ["001", "002"], seed=1)
    write_sequence_csv(tmp_path / "validation.csv", "validation", ["003"], seed=2)

    first = premeal_gru.train(
        tmp_path / "train.csv", tmp_path / "validation.csv", tmp_path / "a", 3
    )
    second = premeal_gru.train(
        tmp_path / "train.csv", tmp_path / "validation.csv", tmp_path / "b", 3
    )

    assert first["validation_metrics"] == second["validation_metrics"]
