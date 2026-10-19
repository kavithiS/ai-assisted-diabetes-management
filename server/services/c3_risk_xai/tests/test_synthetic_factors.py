"""Tests for the SYNTHETIC TAF factors (ml/dataprep/synthetic_factors.py).

They use generated covariates, so they run without the dataset.
"""

import math
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import pytest

from c3_risk_xai.ml.dataprep.synthetic_factors import (
    COMPARISONS,
    FACTORS,
    add_synthetic_factors,
    blank_factors,
    flag,
    load_assumptions,
    realised_effects,
)

SPEC = load_assumptions()


def real_rows(n: int, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    """Stand-in for real training rows: the covariates the generator reads, plus extras."""
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(
        {
            "age": rng.uniform(25, 80, n),
            "sex_male": rng.integers(0, 2, n).astype(float),
            "bmi": rng.normal(24.5, 3.8, n),
            "hypertensive": rng.integers(0, 2, n).astype(float),
            "systolic_bp": rng.normal(125, 15, n),
        }
    )
    X.loc[X.index[:5], "bmi"] = np.nan  # real data has gaps; they must stay gaps
    y = pd.Series((rng.uniform(size=n) < 0.3).astype(int), name="target")
    return X, y


@pytest.fixture(scope="module")
def large() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    X, y = real_rows(40_000)
    return X, y, add_synthetic_factors(X, y, SPEC)


def test_real_columns_and_labels_are_unchanged() -> None:
    X, y = real_rows(2_000)
    X_before = pd.util.hash_pandas_object(X, index=True).to_numpy().copy()
    y_before = pd.util.hash_pandas_object(y, index=True).to_numpy().copy()

    out = add_synthetic_factors(X, y, SPEC)

    assert np.array_equal(pd.util.hash_pandas_object(X, index=True).to_numpy(), X_before)
    assert np.array_equal(pd.util.hash_pandas_object(y, index=True).to_numpy(), y_before)
    assert out[list(X.columns)].equals(X)
    assert out["bmi"].isna().sum() == 5


def test_values_are_complete_and_plausible() -> None:
    X, y = real_rows(5_000)
    out = add_synthetic_factors(X, y, SPEC)
    for factor in FACTORS:
        low, high = SPEC["factors"][factor]["range"]
        assert not out[factor].isna().any()
        assert out[factor].between(low, high).all()
    assert set(out["smoking_status"].unique()) <= {0.0, 1.0, 2.0}
    assert set(out["bp_medication"].unique()) <= {0.0, 1.0}
    assert (out.loc[out["hypertensive"] == 0, "bp_medication"] == 0).all()


def test_every_generated_value_is_flagged_and_held_out_rows_stay_missing() -> None:
    X, y = real_rows(1_000)
    train = add_synthetic_factors(X, y, SPEC)
    test = blank_factors(X)
    for factor in FACTORS:
        assert train[flag(factor)].all()
        assert test[factor].isna().all()
        assert not test[flag(factor)].any()


def test_same_seed_same_values_and_another_seed_differs() -> None:
    X, y = real_rows(1_000)
    first = add_synthetic_factors(X, y, SPEC)
    assert first.equals(add_synthetic_factors(X, y, SPEC))
    assert not first.equals(add_synthetic_factors(X, y, SPEC, seed=99))


def test_realised_effects_match_the_assumptions(
    large: tuple[pd.DataFrame, pd.Series, pd.DataFrame],
) -> None:
    _, y, out = large
    realised = realised_effects(out, y)
    for key, (factor, name) in COMPARISONS.items():
        assumed = float(SPEC["factors"][factor]["parameters"][name]["value"])
        if key.startswith("odds_ratio"):
            # On the log scale, within sampling noise for n = 40,000.
            assert abs(math.log(realised[key]) - math.log(assumed)) < 0.15, key
        else:
            assert abs(realised[key] - assumed) < 0.03, key
    assert realised["share_bp_medication_if_not_hypertensive"] == 0.0


def test_assumptions_file_gives_every_value_a_source_and_status() -> None:
    for factor, entry in SPEC["factors"].items():
        assert entry["role"] in {"A", "C"}, factor
        for name, item in entry["parameters"].items():
            label = f"{factor}.{name}"
            assert {"value", "source", "status"} <= set(item), label
            assert item["status"] in {"verified", "placeholder"}, label
            if item["status"] == "verified":
                assert "[INFORMATION REQUIRED]" not in item["source"], label
    # Factors that would leak the diabetes label are never generated.
    assert not set(SPEC["not_generated"]) & set(SPEC["factors"])


def test_placeholder_effects_on_diabetes_are_conservative() -> None:
    """With no verified source, no effect on diabetes is assumed (odds ratio 1.0)."""
    effects: list[dict[str, Any]] = [
        item
        for entry in SPEC["factors"].values()
        for name, item in entry["parameters"].items()
        if name.startswith("odds_ratio")
    ]
    for item in effects:
        if item["status"] == "placeholder":
            assert float(item["value"]) == 1.0
