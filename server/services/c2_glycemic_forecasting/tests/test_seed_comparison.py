"""Tests for the multi-seed comparison runner. All data here is synthetic."""

import importlib.util
import sys
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
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = _load_script("run_seed_comparison")


def meals(ids: list[tuple[str, str]], **extra: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"participant_id": [i[0] for i in ids], "meal_timestamp": [i[1] for i in ids], **extra}
    )


def test_evaluation_meals_follow_sequence_order() -> None:
    sequence = meals([("002", "t2"), ("001", "t1"), ("001", "t3")])
    validation = meals(
        [("001", "t1"), ("001", "t3"), ("002", "t2"), ("003", "t4")],
        premeal_libre_gl=[100.0, 110.0, 120.0, 130.0],
    )

    aligned = runner.evaluation_meals(sequence, validation)

    assert list(zip(aligned["participant_id"], aligned["meal_timestamp"], strict=True)) == [
        ("002", "t2"),
        ("001", "t1"),
        ("001", "t3"),
    ]
    assert aligned["premeal_libre_gl"].tolist() == [120.0, 100.0, 110.0]


def test_meal_missing_from_validation_stops_the_comparison() -> None:
    sequence = meals([("001", "t1"), ("001", "t9")])
    validation = meals([("001", "t1")], premeal_libre_gl=[100.0])

    with pytest.raises(ValueError, match="Cannot evaluate every meal"):
        runner.evaluation_meals(sequence, validation)


def test_score_reports_overall_and_per_horizon_errors() -> None:
    actual = np.zeros((2, 16))
    predictions = np.vstack([np.full(16, 3.0), np.full(16, -1.0)])

    result = runner.score(predictions, actual)

    assert result["mae_mg_dl"] == 2.0
    assert result["rmse_mg_dl"] == pytest.approx(np.sqrt(5.0))
    assert len(result["horizon_mae_mg_dl"]) == len(result["horizon_rmse_mg_dl"]) == 16


def test_summary_uses_mean_and_sample_standard_deviation() -> None:
    runs = pd.DataFrame(
        {
            "model": ["a", "a", "a"],
            "mae_mg_dl": [1.0, 2.0, 3.0],
            "rmse_mg_dl": [2.0, 2.0, 2.0],
            "horizon_mae_mg_dl": [[1.0] * 16, [2.0] * 16, [3.0] * 16],
            "horizon_rmse_mg_dl": [[2.0] * 16] * 3,
        }
    )

    summary = runner.summarize(runs)["a"]

    assert summary["mae_mean"] == 2.0
    assert summary["mae_std"] == 1.0
    assert summary["rmse_std"] == 0.0
    assert summary["horizon_mae_std"] == [1.0] * 16


def test_existing_output_directory_is_refused(tmp_path: Path) -> None:
    with pytest.raises(FileExistsError):
        runner.run_comparison(tmp_path, tmp_path, (42,))


def test_seed_42_is_required(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="42"):
        runner.run_comparison(tmp_path, tmp_path / "new", (1, 2))
