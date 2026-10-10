"""South Asian experiment: real vs real + synthetic vs synthetic only.

Design (so the numbers are defensible):
- Main data is DiaBD (Bangladesh). One stratified 80/20 split; the 20% test set
  is REAL and never touched by the synthetic generator.
- Missing values are filled with TRAINING medians only.
- 5-fold stratified cross-validation on the real training split.
- Every result is reported without and with glucose, because glucose is a
  blood test result that a questionnaire-only user would not have.
- Second site: a model trained on DiaBD is tested on the Narsingdi hospital
  patients, using only the features both sites recorded.
- Pooled: both sites together on the shared features, with per-site results.

Run (after python -m src.south_asia_dataset):
    python -m src.experiment_south_asia
"""

import json

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

from .config import CFG, abs_path
from .south_asia_dataset import COMMON, SCHEMA
from .synthetic import GaussianCopulaSynthesizer, exact_copy_rate
from .train import evaluate, get_models

ALL_FEATURES = list(SCHEMA)


def feature_sets(features: list[str]) -> dict:
    return {
        "without_glucose": [f for f in features if f != "glucose_mmol"],
        "with_glucose": list(features),
    }


def pos_weight(y) -> float:
    return (y == 0).sum() / (y == 1).sum()


def split(X, y, stratify=None):
    return train_test_split(
        X,
        y,
        test_size=CFG["preprocess"]["test_size"],
        random_state=CFG["preprocess"]["random_state"],
        stratify=y if stratify is None else stratify,
    )


def cross_validate(X, y) -> dict:
    """Imputation sits inside the pipeline, so each fold learns its own medians."""
    folds = StratifiedKFold(
        CFG["south_asia"]["cv_folds"], shuffle=True, random_state=CFG["preprocess"]["random_state"]
    )
    out = {}
    for name, model in get_models(pos_weight(y)).items():
        pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("model", model)])
        scores = cross_val_score(pipe, X, y, cv=folds, scoring="roc_auc")
        out[name] = {"roc_auc_mean": round(scores.mean(), 4), "roc_auc_std": round(scores.std(), 4)}
    return out


def fit_and_score(X_fit, y_fit, X_test, y_test, weight, label: dict) -> list:
    """Research comparison only; the deployable models come from src.train."""
    rows = []
    for name, model in get_models(weight).items():
        model.fit(X_fit, y_fit)
        metrics = {**label, **evaluate(name, model, X_test, y_test)}
        rows.append(metrics)
        print(
            f"  {label} {name}: acc {metrics['accuracy']}  ROC-AUC {metrics['roc_auc']}  "
            f"PR-AUC {metrics['pr_auc']}  recall {metrics['recall_sensitivity']}"
        )
    return rows


def fidelity(real: pd.DataFrame, synthetic: pd.DataFrame) -> dict:
    std = real.std().replace(0, 1)
    mean_gap = ((real.mean() - synthetic.mean()).abs() / std).mean()
    corr_gap = (real.corr() - synthetic.corr()).abs().to_numpy()
    return {
        "mean_standardised_mean_difference": round(float(mean_gap), 4),
        "mean_abs_correlation_difference": round(float(pd.DataFrame(corr_gap).stack().mean()), 4),
        "exact_copy_rate": round(exact_copy_rate(real, synthetic), 4),
    }


def main_experiment(diabd: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    X, y = diabd[ALL_FEATURES], diabd["target"]
    X_train, X_test, y_train, y_test = split(X, y)
    fill = X_train.median()
    X_train_f, X_test_f = X_train.fillna(fill), X_test.fillna(fill)
    w = pos_weight(y_train)

    synth = GaussianCopulaSynthesizer(CFG["synthetic"]["random_state"]).fit(X_train_f, y_train)
    X_syn, y_syn = synth.sample(int(len(X_train_f) * CFG["synthetic"]["ratio"]))
    print(f"DiaBD train {len(X_train)} | test {len(X_test)} | synthetic {len(X_syn)}")

    results, cv = [], {}
    for fs_name, cols in feature_sets(ALL_FEATURES).items():
        cv[fs_name] = cross_validate(X_train[cols], y_train)
        scenarios = {
            "real_only": (X_train_f[cols], y_train),
            "real_plus_synthetic": (
                pd.concat([X_train_f[cols], X_syn[cols]], ignore_index=True),
                pd.concat([y_train, y_syn], ignore_index=True),
            ),
            "synthetic_only": (X_syn[cols], y_syn),
        }
        for scenario, (X_fit, y_fit) in scenarios.items():
            label = {"scenario": scenario, "features": fs_name}
            results += fit_and_score(X_fit, y_fit, X_test_f[cols], y_test, w, label)

    combined = pd.concat(
        [
            X_train_f.assign(target=y_train.to_numpy(), source="diabd_real_train"),
            X_test_f.assign(target=y_test.to_numpy(), source="diabd_real_test"),
            X_syn.assign(target=y_syn.to_numpy(), source="synthetic"),
        ],
        ignore_index=True,
    )
    report = {
        "rows": {"train_real": len(X_train), "test_real": len(X_test), "synthetic": len(X_syn)},
        "diabetes_rate": round(float(y.mean()), 4),
        "cross_validation_real_train": cv,
        "test_results": results,
        "synthetic_fidelity": fidelity(X_train_f, X_syn),
    }
    return report, combined


def second_site(diabd: pd.DataFrame, narsingdi: pd.DataFrame) -> list:
    """Train on all of DiaBD, test on the Narsingdi hospital patients."""
    results = []
    for fs_name, cols in feature_sets(COMMON).items():
        fill = diabd[cols].median()
        X_fit, y_fit = diabd[cols].fillna(fill), diabd["target"]
        X_test = narsingdi[cols].fillna(fill)
        label = {"scenario": "train_diabd_test_narsingdi", "features": fs_name}
        results += fit_and_score(
            X_fit, y_fit, X_test, narsingdi["target"], pos_weight(y_fit), label
        )
    return results


def pooled(df: pd.DataFrame) -> list:
    """Both sites together on shared features, split by site and label."""
    results = []
    strata = df["source"] + "_" + df["target"].astype(str)
    train, test = train_test_split(
        df,
        test_size=CFG["preprocess"]["test_size"],
        random_state=CFG["preprocess"]["random_state"],
        stratify=strata,
    )
    for fs_name, cols in feature_sets(COMMON).items():
        fill = train[cols].median()
        X_fit, y_fit = train[cols].fillna(fill), train["target"]
        for site in ["all", "diabd", "narsingdi"]:
            part = test if site == "all" else test[test["source"] == site]
            label = {"scenario": f"pooled_test_{site}", "features": fs_name}
            results += fit_and_score(
                X_fit, y_fit, part[cols].fillna(fill), part["target"], pos_weight(y_fit), label
            )
    return results


def main():
    df = pd.read_csv(abs_path(CFG["south_asia"]["processed_file"]))
    diabd, narsingdi = df[df["source"] == "diabd"], df[df["source"] == "narsingdi"]

    print("\n== Main: DiaBD real / real+synthetic / synthetic ==")
    report, combined = main_experiment(diabd)
    print("\n== Second site: DiaBD -> Narsingdi ==")
    report["second_site"] = second_site(diabd, narsingdi)
    print("\n== Pooled sites ==")
    report["pooled"] = pooled(df)
    report["dataset"] = "DiaBD (main) + Narsingdi hospital (second site), Bangladesh"

    narsingdi_rows = narsingdi[ALL_FEATURES + ["target"]].assign(source="narsingdi_real")
    combined = pd.concat([combined, narsingdi_rows], ignore_index=True)
    data_path = abs_path("data/processed/c3_south_asia_real_plus_synthetic.csv")
    combined.to_csv(data_path, index=False)

    path = abs_path("outputs/reports/south_asia_experiment.json")
    path.write_text(json.dumps(report, indent=2))
    print(f"\nSynthetic fidelity: {report['synthetic_fidelity']}")
    print(f"Saved {data_path} and {path}")
    print("Record these real numbers in your RP diary. Never quote invented figures.")


if __name__ == "__main__":
    main()
