"""Step 3: train, compare, calibrate and save the risk models.

For each feature set (without / with glucose) and each of three models:
1. 5-fold cross-validation on the REAL training split gives out-of-fold scores.
   Inside every fold the synthetic generator and the medians are refitted on
   that fold's training rows only, so nothing leaks from the validation rows.
2. The out-of-fold scores pick the model (best PR-AUC), fit the probability
   calibration and choose the Low / Moderate / High cut-offs.
3. The model is refitted on the whole training split (real + synthetic) and
   scored ONCE on the untouched real test split.

Run from the repository root:
    uv run python server/services/c3_risk_xai/training/train.py
"""

import json

import joblib
import pandas as pd
from sklearn.metrics import brier_score_loss

from c3_risk_xai.ml.config import CFG, abs_path
from c3_risk_xai.ml.modeling import (
    apply_calibrator,
    band_table,
    choose_thresholds,
    fit_calibrator,
    fit_model,
    get_models,
    make_bundle,
    metrics_from_proba,
    out_of_fold,
)
from c3_risk_xai.ml.preprocess import build_dataset


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

    reports = abs_path(CFG["paths"]["reports_dir"])
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "model_comparison.json").write_text(json.dumps(report, indent=2))
    pd.concat(predictions).to_csv(reports / "test_predictions.csv", index=False)
    print(f"\nSaved models to {out_dir} and reports to {reports}")
    print("Record these real numbers in your RP diary. Never quote invented figures.")


if __name__ == "__main__":
    main()
