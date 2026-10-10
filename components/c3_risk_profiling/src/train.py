"""Step 3: train, compare, calibrate and save the risk models.

For each feature set (without / with glucose) and each of three models:
1. 5-fold cross-validation on the REAL training split gives out-of-fold scores.
   Inside every fold the synthetic generator and the medians are refitted on
   that fold's training rows only, so nothing leaks from the validation rows.
2. The out-of-fold scores pick the model (best PR-AUC), fit the probability
   calibration and choose the Low / Moderate / High cut-offs.
3. The model is refitted on the whole training split (real + synthetic) and
   scored ONCE on the untouched real test split.

Run:
    python -m src.train
"""

import json
from datetime import date

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import CFG, abs_path
from .preprocess import build_dataset
from .synthetic import GaussianCopulaSynthesizer

BAND_ORDER = ["Low", "Moderate", "High"]


def get_models(pos_weight: float = 1.0):
    """Three models, deliberately chosen - be ready to justify each one.

    - Logistic regression: interpretable baseline. If a complex model cannot
      beat it, the extra complexity is not earning its place.
    - Random forest: captures non-linear effects and interactions, still
      explainable with TreeSHAP.
    - XGBoost: strong tabular performance.

    class_weight="balanced" matters because the positive class is a minority.
    XGBoost has no class_weight, so pos_weight (negatives / positives in the
    training split) gives it the same balancing through scale_pos_weight.
    """
    seed = CFG["preprocess"]["random_state"]
    models = {
        # Scaling is inside the pipeline, so it is fitted on train folds only.
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=5,
            class_weight="balanced",
            n_jobs=-1,
            random_state=seed,
        ),
    }
    try:
        from xgboost import XGBClassifier

        models["xgboost"] = XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            scale_pos_weight=pos_weight,
            random_state=seed,
            n_jobs=-1,
        )
    except ImportError:
        print("xgboost not installed - skipping it")
    return models


def metrics_from_proba(name, y_true, proba, threshold: float = 0.5) -> dict:
    """Healthcare note: recall (sensitivity) is the metric that matters most.
    A false negative means telling an at-risk person they are fine."""
    y_true = np.asarray(y_true)
    pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "model": name,
        "accuracy": round((tp + tn) / len(y_true), 4),
        "roc_auc": round(roc_auc_score(y_true, proba), 4),
        "pr_auc": round(average_precision_score(y_true, proba), 4),
        "recall_sensitivity": round(recall_score(y_true, pred, zero_division=0), 4),
        "precision": round(precision_score(y_true, pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, pred, zero_division=0), 4),
        "specificity": round(tn / (tn + fp), 4) if (tn + fp) else 0.0,
        "brier": round(brier_score_loss(y_true, proba), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def evaluate(name, model, X_test, y_test) -> dict:
    return metrics_from_proba(name, y_test, model.predict_proba(X_test)[:, 1])


def augment(X_filled: pd.DataFrame, y: pd.Series, seed: int) -> tuple[pd.DataFrame, pd.Series]:
    """Real rows plus synthetic rows generated from those same real rows."""
    if not CFG["synthetic"]["augment_training"]:
        return X_filled, y
    synth = GaussianCopulaSynthesizer(seed).fit(X_filled, y)
    X_syn, y_syn = synth.sample(int(len(X_filled) * CFG["synthetic"]["ratio"]))
    return (
        pd.concat([X_filled, X_syn], ignore_index=True),
        pd.concat([y.reset_index(drop=True), y_syn], ignore_index=True),
    )


def fit_model(name: str, X: pd.DataFrame, y: pd.Series, seed: int):
    """Fill gaps with this split's medians, augment, fit. Returns (model, medians)."""
    fill = X.median()
    X_fit, y_fit = augment(X.fillna(fill), y, seed)
    pos_weight = (y_fit == 0).sum() / (y_fit == 1).sum()
    model = get_models(pos_weight)[name]
    model.fit(X_fit, y_fit)
    return model, fill


def out_of_fold(name: str, X: pd.DataFrame, y: pd.Series) -> np.ndarray:
    folds = StratifiedKFold(
        CFG["preprocess"]["cv_folds"], shuffle=True, random_state=CFG["preprocess"]["random_state"]
    )
    oof = np.zeros(len(X))
    for k, (tr, va) in enumerate(folds.split(X, y)):
        model, fill = fit_model(name, X.iloc[tr], y.iloc[tr], CFG["synthetic"]["random_state"] + k)
        oof[va] = model.predict_proba(X.iloc[va].fillna(fill))[:, 1]
    return oof


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def fit_calibrator(scores, y) -> dict:
    """Platt scaling on out-of-fold scores.

    class_weight="balanced" inflates raw scores; this maps them back to
    probabilities that match how often diabetes really occurred. The mapping
    is monotonic, so it never changes which patient ranks higher.
    """
    lr = LogisticRegression(C=1e6).fit(_logit(scores).reshape(-1, 1), y)
    return {"coef": float(lr.coef_[0, 0]), "intercept": float(lr.intercept_[0])}


def apply_calibrator(cal: dict, scores) -> np.ndarray:
    z = cal["coef"] * _logit(scores) + cal["intercept"]
    return 1 / (1 + np.exp(-z))


def choose_thresholds(cal_scores, y) -> dict:
    """Cut-offs from training data only (proposal 3.2.4: no arbitrary equal thirds)."""
    cal_scores, y = np.asarray(cal_scores), np.asarray(y)
    low = float(np.quantile(cal_scores[y == 1], 1 - CFG["risk_bands"]["low_band_sensitivity"]))
    high = float(np.quantile(cal_scores[y == 0], CFG["risk_bands"]["high_band_specificity"]))
    return {"low_max": round(low, 4), "high_min": round(max(high, low), 4)}


def categorise(probability: float, thresholds: dict) -> str:
    if probability < thresholds["low_max"]:
        return "Low"
    if probability < thresholds["high_min"]:
        return "Moderate"
    return "High"


def band_table(cal_probs, y, thresholds) -> list[dict]:
    """How well the bands separate people: diabetes rate inside each band."""
    bands = pd.Series([categorise(p, thresholds) for p in cal_probs])
    y = pd.Series(np.asarray(y))
    rows = []
    for band in BAND_ORDER:
        mask = bands == band
        rows.append(
            {
                "band": band,
                "people": int(mask.sum()),
                "share_of_people": round(float(mask.mean()), 4),
                "diabetic_people": int(y[mask].sum()),
                "diabetes_rate": round(float(y[mask].mean()), 4) if mask.any() else None,
                "share_of_all_diabetic": round(float(y[mask].sum() / y.sum()), 4),
            }
        )
    return rows


def make_bundle(model, name, feature_set, features, fill, calibrator, thresholds, X_ref, metrics):
    """Everything predict.py and explain.py need, so they never touch raw data."""
    seed = CFG["preprocess"]["random_state"]
    ref = X_ref.fillna(fill)
    return {
        "model": model,
        "model_name": name,
        "feature_set": feature_set,
        "features": features,
        "fill_values": {k: float(v) for k, v in fill.items()},
        "calibrator": calibrator,
        "thresholds": thresholds,
        "background": ref.sample(
            min(CFG["explain"]["background_samples"], len(ref)), random_state=seed
        ),
        "lime_background": ref.sample(
            min(CFG["explain"]["lime_background_samples"], len(ref)), random_state=seed
        ),
        "metrics": metrics,
        "trained_on": f"{CFG['dataset']['name']}; synthetic augmentation "
        f"{'on' if CFG['synthetic']['augment_training'] else 'off'}",
        "version": date.today().isoformat(),
    }


def main():
    X_train_all, X_test_all, y_train, y_test = build_dataset()
    out_dir = abs_path(CFG["model"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Real train: {len(X_train_all)}  Real test: {len(X_test_all)}")

    report, predictions = {"dataset": CFG["dataset"]["name"], "feature_sets": {}}, []
    for feature_set, features in CFG["feature_sets"].items():
        X_train, X_test = X_train_all[features], X_test_all[features]
        print(f"\n=== Feature set: {feature_set} ({len(features)} features) ===")

        cv, oofs = {}, {}
        for name in get_models():
            oofs[name] = out_of_fold(name, X_train, y_train)
            cv[name] = metrics_from_proba(name, y_train, oofs[name])
            print(f"  CV  {name}: ROC-AUC {cv[name]['roc_auc']}  PR-AUC {cv[name]['pr_auc']}")

        active = CFG["model"]["active"]
        selected = max(cv, key=lambda n: cv[n]["pr_auc"]) if active == "auto" else active
        print(f"  Selected by cross-validated PR-AUC: {selected}")

        results = {}
        for name in get_models():
            calibrator = fit_calibrator(oofs[name], y_train)
            thresholds = choose_thresholds(apply_calibrator(calibrator, oofs[name]), y_train)
            model, fill = fit_model(name, X_train, y_train, CFG["synthetic"]["random_state"])
            raw = model.predict_proba(X_test.fillna(fill))[:, 1]
            cal = apply_calibrator(calibrator, raw)
            test = metrics_from_proba(name, y_test, raw)
            test["brier_calibrated"] = round(brier_score_loss(y_test, cal), 4)
            results[name] = {
                "cross_validation": cv[name],
                "test": test,
                "thresholds": thresholds,
                "test_bands": band_table(cal, y_test, thresholds),
            }
            print(
                f"  TEST {name}: ROC-AUC {test['roc_auc']}  PR-AUC {test['pr_auc']}  "
                f"recall {test['recall_sensitivity']}  Brier {test['brier']} -> "
                f"{test['brier_calibrated']} calibrated"
            )
            bundle = make_bundle(
                model, name, feature_set, features, fill, calibrator, thresholds, X_train,
                results[name],
            )  # fmt: skip
            joblib.dump(bundle, out_dir / f"c3_{feature_set}_{name}.joblib")
            if name == selected:
                joblib.dump(bundle, out_dir / f"c3_{feature_set}.joblib")
            predictions.append(
                pd.DataFrame(
                    {
                        "feature_set": feature_set,
                        "model": name,
                        "y_true": y_test.to_numpy(),
                        "prob_raw": raw,
                        "prob_calibrated": cal,
                    }
                )
            )

        report["feature_sets"][feature_set] = {"selected_model": selected, "models": results}
        bands = results[selected]["test_bands"]
        print("  Test bands (selected model): " + "; ".join(
            f"{b['band']} {b['people']} people, {b['diabetes_rate']} diabetic" for b in bands
        ))  # fmt: skip

    reports = abs_path("outputs/reports")
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "model_comparison.json").write_text(json.dumps(report, indent=2))
    pd.concat(predictions).to_csv(reports / "test_predictions.csv", index=False)
    print(f"\nSaved models to {out_dir} and reports to {reports}")
    print("Record these real numbers in your RP diary. Never quote invented figures.")


if __name__ == "__main__":
    main()
