"""Step 3: train and compare three models, then save them.

Run:
    python -m src.train
"""

import json

import joblib
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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import CFG, abs_path
from .preprocess import build_dataset


def get_models():
    """Three models, deliberately chosen - be ready to justify each one.

    - Logistic regression: interpretable baseline. If a complex model cannot
      beat it, the extra complexity is not earning its place.
    - Random forest: captures non-linear effects and interactions, still
      explainable with TreeSHAP.
    - XGBoost: strong tabular performance; optional for PP1.

    class_weight="balanced" matters because the positive class is a minority.
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
            max_depth=5,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=seed,
            n_jobs=-1,
        )
    except ImportError:
        print("xgboost not installed - skipping it")
    return models


def evaluate(name, model, X_test, y_test) -> dict:
    """Healthcare note: recall (sensitivity) is the metric that matters most.
    A false negative means telling an at-risk person they are fine."""
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    return {
        "model": name,
        "roc_auc": round(roc_auc_score(y_test, proba), 4),
        "pr_auc": round(average_precision_score(y_test, proba), 4),
        "recall_sensitivity": round(recall_score(y_test, pred), 4),
        "precision": round(precision_score(y_test, pred), 4),
        "f1": round(f1_score(y_test, pred), 4),
        "specificity": round(tn / (tn + fp), 4),
        "brier": round(brier_score_loss(y_test, proba), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def main():
    X_train, X_test, y_train, y_test = build_dataset()
    out_dir = abs_path(CFG["model"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for name, model in get_models().items():
        print(f"\nTraining {name} ...")
        model.fit(X_train, y_train)
        joblib.dump({"model": model, "features": list(X_train.columns)}, out_dir / f"{name}.joblib")
        metrics = evaluate(name, model, X_test, y_test)
        results.append(metrics)
        for k, v in metrics.items():
            if k != "model":
                print(f"  {k}: {v}")

    report = abs_path("outputs/reports/model_comparison.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(results, indent=2))
    print(f"\nSaved comparison to {report}")
    print("Record these real numbers in your RP diary. Never quote invented figures.")


if __name__ == "__main__":
    main()
