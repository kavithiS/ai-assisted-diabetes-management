"""Test fixtures that do not need the real dataset.

`fake_models` trains small models on generated numbers and saves them in the
same bundle format src.train produces, so the tests exercise the real
predict / explain code on any machine, including CI.
"""

import numpy as np
import pandas as pd
import pytest
from src import predict
from src.config import CFG
from src.train import apply_calibrator, choose_thresholds, fit_calibrator, get_models, make_bundle


def fake_patients(n: int = 600, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(
        {
            "age": rng.uniform(20, 80, n),
            "sex_male": rng.integers(0, 2, n),
            "bmi": rng.normal(23, 4, n),
            "systolic_bp": rng.normal(128, 20, n),
            "diastolic_bp": rng.normal(80, 12, n),
            "pulse_rate": rng.normal(76, 12, n),
            "glucose_mmol": rng.normal(7, 2.5, n),
            "family_history_diabetes": rng.integers(0, 2, n),
            "family_history_hypertension": rng.integers(0, 2, n),
            "hypertensive": rng.integers(0, 2, n),
            "cardiovascular_disease": rng.integers(0, 2, n),
            "stroke": rng.integers(0, 2, n),
        }
    )
    # A known, simple risk rule so directional tests have a right answer.
    z = (
        0.05 * (X["age"] - 50)
        + 0.15 * (X["bmi"] - 23)
        + 0.6 * (X["glucose_mmol"] - 7)
        + 1.0 * X["hypertensive"]
        - 1.5
    )
    y = pd.Series((rng.uniform(size=n) < 1 / (1 + np.exp(-z))).astype(int))
    return X, y


@pytest.fixture(scope="session")
def fake_models(tmp_path_factory):
    model_dir = tmp_path_factory.mktemp("models")
    X_all, y = fake_patients()
    # Logistic regression and random forest cover both SHAP code paths.
    choice = {"without_glucose": "logistic_regression", "with_glucose": "random_forest"}
    for feature_set, features in CFG["feature_sets"].items():
        X = X_all[features]
        name = choice[feature_set]
        model = get_models()[name].fit(X, y)
        scores = model.predict_proba(X)[:, 1]
        calibrator = fit_calibrator(scores, y)
        thresholds = choose_thresholds(apply_calibrator(calibrator, scores), y)
        bundle = make_bundle(
            model, name, feature_set, features, X.median(), calibrator, thresholds, X, {}
        )
        pd.to_pickle(bundle, model_dir / f"c3_{feature_set}.joblib")

    patch = pytest.MonkeyPatch()
    patch.setattr(predict, "MODEL_DIR", model_dir)
    predict.load_bundle.cache_clear()
    yield model_dir
    patch.undo()
    predict.load_bundle.cache_clear()
