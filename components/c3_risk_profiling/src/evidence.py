"""Step 5: build the PP1 evidence pack - figures and explanation-quality numbers.

Everything is computed from the saved models and the REAL test split:
- ROC and precision-recall curves for all three models
- calibration curves before and after calibration
- diabetes rate inside each risk band
- SHAP global importance (beeswarm)
- explanation quality over test patients: SHAP-LIME top-5 overlap, LIME local
  fidelity, and LIME stability across random seeds (proposal 3.4.1 targets)

Run (after python -m src.train):
    python -m src.evidence
"""

import json
from itertools import combinations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.metrics import precision_recall_curve, roc_curve  # noqa: E402

from .config import CFG, abs_path  # noqa: E402
from .explain import READABLE, agreement, lime_explain, shap_explain  # noqa: E402
from .predict import load_bundle  # noqa: E402
from .preprocess import build_dataset  # noqa: E402

FIG = abs_path("outputs/figures")
REPORTS = abs_path("outputs/reports")
TITLES = {"without_glucose": "Without glucose", "with_glucose": "With glucose"}


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=150)
    plt.close(fig)
    print(f"  saved outputs/figures/{name}")


def curves(preds: pd.DataFrame, comparison: dict):
    for fs, part in preds.groupby("feature_set"):
        selected = comparison["feature_sets"][fs]["selected_model"]
        fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.5))
        for model, m in part.groupby("model"):
            fpr, tpr, _ = roc_curve(m["y_true"], m["prob_raw"])
            prec, rec, _ = precision_recall_curve(m["y_true"], m["prob_raw"])
            test = comparison["feature_sets"][fs]["models"][model]["test"]
            star = " (selected)" if model == selected else ""
            a.plot(fpr, tpr, label=f"{model}{star} AUC={test['roc_auc']}")
            b.plot(rec, prec, label=f"{model}{star} AP={test['pr_auc']}")
        a.plot([0, 1], [0, 1], "k--", lw=0.8)
        b.axhline(part["y_true"].mean(), color="k", ls="--", lw=0.8, label="no-skill")
        a.set(xlabel="False positive rate", ylabel="Sensitivity", title=f"ROC - {TITLES[fs]}")
        b.set(xlabel="Recall", ylabel="Precision", title=f"Precision-recall - {TITLES[fs]}")
        a.legend(fontsize=8)
        b.legend(fontsize=8)
        save(fig, f"roc_pr_{fs}.png")


def calibration(preds: pd.DataFrame, comparison: dict):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, (fs, part) in zip(axes, preds.groupby("feature_set"), strict=True):
        selected = comparison["feature_sets"][fs]["selected_model"]
        m = part[part["model"] == selected]
        for col, label in [("prob_raw", "before"), ("prob_calibrated", "after")]:
            frac, mean = calibration_curve(m["y_true"], m[col], n_bins=8, strategy="quantile")
            ax.plot(mean, frac, "o-", label=f"{label} calibration")
        ax.plot([0, 1], [0, 1], "k--", lw=0.8, label="perfect")
        ax.set(
            xlabel="Predicted probability",
            ylabel="Observed diabetes rate",
            title=f"Calibration - {TITLES[fs]} ({selected})",
        )
        ax.legend(fontsize=8)
    save(fig, "calibration.png")


def bands(comparison: dict):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, (fs, info) in zip(axes, comparison["feature_sets"].items(), strict=True):
        rows = info["models"][info["selected_model"]]["test_bands"]
        rates = [(r["diabetes_rate"] or 0) * 100 for r in rows]
        bars = ax.bar([r["band"] for r in rows], rates, color=["#4caf50", "#ff9800", "#f44336"])
        for bar, r in zip(bars, rows, strict=True):
            ax.annotate(
                f"{r['people']} people", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                ha="center", va="bottom", fontsize=8,
            )  # fmt: skip
        ax.set(ylabel="% diabetic in band (real test set)", title=f"Risk bands - {TITLES[fs]}")
    save(fig, "risk_bands.png")


def shap_global(X_test: pd.DataFrame):
    import shap

    for fs in CFG["feature_sets"]:
        bundle = load_bundle(fs)
        X = X_test[bundle["features"]].fillna(bundle["fill_values"])
        X = X.sample(min(300, len(X)), random_state=CFG["preprocess"]["random_state"])
        if bundle["model_name"] in ("random_forest", "xgboost"):
            values = np.array(shap.TreeExplainer(bundle["model"]).shap_values(X))
            values = values[:, :, -1] if values.ndim == 3 else values
        else:
            model = bundle["model"]
            fn = lambda x, m=model, f=bundle["features"]: m.predict_proba(  # noqa: E731
                pd.DataFrame(x, columns=f)
            )[:, 1]
            values = shap.Explainer(fn, bundle["background"])(X).values
        shap.summary_plot(
            values, X.rename(columns=READABLE), show=False, plot_size=(8, 5), max_display=12
        )
        plt.title(f"SHAP global importance - {TITLES[fs]} ({bundle['model_name']})")
        save(plt.gcf(), f"shap_summary_{fs}.png")


def explanation_quality(X_test: pd.DataFrame, n: int = 30, seeds=(1, 2, 3)) -> dict:
    """Agreement, fidelity and stability over real test patients."""
    out = {}
    patients = X_test.sample(n, random_state=CFG["preprocess"]["random_state"])
    for fs in CFG["feature_sets"]:
        overlaps, fidelities, stabilities = [], [], []
        for _, row in patients.iterrows():
            patient = {k: (None if pd.isna(v) else v) for k, v in row.items()}
            if fs == "without_glucose":
                patient["glucose_mmol"] = None
            shap_rows = shap_explain(patient)
            runs = [lime_explain(patient, seed=s) for s in seeds]
            overlaps.append(agreement(shap_rows, runs[0]["factors"])["overlap_ratio"])
            fidelities.append(runs[0]["fidelity"])
            tops = [{r["feature"] for r in run["factors"]} for run in runs]
            stabilities.append(np.mean([len(a & b) / len(a | b) for a, b in combinations(tops, 2)]))
        out[fs] = {
            "patients": n,
            "median_shap_lime_top5_overlap": round(float(np.median(overlaps)), 3),
            "share_meeting_60pct_target": round(
                float(np.mean(np.array(overlaps) >= CFG["explain"]["agreement_target"])), 3
            ),
            "median_lime_fidelity_r2": round(float(np.median(fidelities)), 3),
            "median_lime_stability_jaccard": round(float(np.median(stabilities)), 3),
        }
        print(f"  {fs}: {out[fs]}")
    return out


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    comparison = json.loads((REPORTS / "model_comparison.json").read_text())
    preds = pd.read_csv(REPORTS / "test_predictions.csv")
    _, X_test, _, _ = build_dataset()

    print("Figures:")
    curves(preds, comparison)
    calibration(preds, comparison)
    bands(comparison)
    shap_global(X_test)
    print("Explanation quality on real test patients (slow - runs LIME several times):")
    quality = explanation_quality(X_test)
    (REPORTS / "explanation_quality.json").write_text(json.dumps(quality, indent=2))
    print("Saved outputs/reports/explanation_quality.json")


if __name__ == "__main__":
    main()
