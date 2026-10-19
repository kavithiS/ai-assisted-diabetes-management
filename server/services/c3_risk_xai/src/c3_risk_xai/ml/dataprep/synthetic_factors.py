"""SYNTHETIC TAF factors added to REAL training rows (C3 model v2, PP1).

The real South Asian data (DiaBD) has no smoking, physical activity, cholesterol,
weight change or BP-medication column. TAF task 1 needs them, so they are generated
for each real TRAINING row from the assumptions in config/synthetic_assumptions.yaml
(every value there has a source and a verified/placeholder status).

Rules:
- Input is real training rows only. The real columns and the real label are never
  changed: the factors are NEW columns, each with an `is_synthetic_<factor>` flag.
- Held-out test rows never get synthetic values (`blank_factors` leaves them missing),
  so every real-data metric stays real.
- A factor's link to diabetes is generated from the real label using the assumed odds
  ratio. A model trained on it will learn that assumed value back, so its importance
  is an assumption, not evidence (circularity, see the v2 model card).
- Seeded: the same seed gives the same values.

How each factor is generated (conditional on the real covariates and label):
- binary / categorical: logistic (multinomial for smoking) with the assumed odds
  ratio on the label; intercepts are solved so the prevalence matches the source.
- continuous: normal, shifted by d = sd^2 * log(OR per unit) for diabetic rows, which
  gives exactly that odds ratio per unit (equal-variance normal model).

Offline code: not imported by services/ or api/ (tests/test_architecture.py).

Run from the repository root:
    uv run python -m c3_risk_xai.ml.dataprep.synthetic_factors
"""

import math
from pathlib import Path
from typing import Any

import numpy as np

# No type stubs for these yet; see docs/ci_pr_note.md (ignore_missing_imports override).
import pandas as pd  # type: ignore[import-untyped]
import yaml  # type: ignore[import-untyped]
from numpy.typing import NDArray
from scipy.stats import norm  # type: ignore[import-untyped]

from ..config import SERVICE_ROOT

ASSUMPTIONS_FILE = SERVICE_ROOT / "config" / "synthetic_assumptions.yaml"
FACTORS = (
    "smoking_status",
    "physical_activity_min_week",
    "total_cholesterol_mmol",
    "weight_change_kg_12m",
    "bp_medication",
)
# Real columns the generator reads (never writes).
COVARIATES = ("age", "sex_male", "bmi", "hypertensive")

Array = NDArray[np.float64]


def load_assumptions(path: Path = ASSUMPTIONS_FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        spec: dict[str, Any] = yaml.safe_load(f)
    return spec


def flag(factor: str) -> str:
    return f"is_synthetic_{factor}"


def param(spec: dict[str, Any], factor: str, name: str) -> float:
    return float(spec["factors"][factor]["parameters"][name]["value"])


def _sigmoid(z: Array) -> Array:
    return 1.0 / (1.0 + np.exp(-z))


def _solve_intercept(linear: Array, target: float) -> float:
    """Intercept b0 so that mean(sigmoid(b0 + linear)) equals `target` (bisection)."""
    low, high = -30.0, 30.0
    for _ in range(100):
        mid = (low + high) / 2
        if _sigmoid(mid + linear).mean() < target:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def _covariates(X: pd.DataFrame) -> dict[str, Array]:
    """Real covariates with gaps filled by the training median, for generation only."""
    return {c: X[c].fillna(X[c].median()).to_numpy(dtype=float) for c in COVARIATES}


def _smoking(
    z: dict[str, Array], y: Array, spec: dict[str, Any], rng: np.random.Generator
) -> Array:
    f = "smoking_status"
    linear = {
        1: param(spec, f, "log_odds_male_former") * z["sex_male"]
        + math.log(param(spec, f, "odds_ratio_diabetes_former")) * y,
        2: param(spec, f, "log_odds_male_current") * z["sex_male"]
        + math.log(param(spec, f, "odds_ratio_diabetes_current")) * y,
    }
    target = {1: param(spec, f, "prevalence_former"), 2: param(spec, f, "prevalence_current")}
    intercept = {1: 0.0, 2: 0.0}
    for _ in range(500):  # multinomial logit, "never" is the reference category
        expo = {k: np.exp(intercept[k] + linear[k]) for k in (1, 2)}
        total = 1.0 + expo[1] + expo[2]
        for k in (1, 2):
            intercept[k] += math.log(target[k] / float((expo[k] / total).mean()))
    expo = {k: np.exp(intercept[k] + linear[k]) for k in (1, 2)}
    total = 1.0 + expo[1] + expo[2]
    p_former, p_current = expo[1] / total, expo[2] / total
    u = rng.random(len(y))
    return np.where(u < p_current, 2.0, np.where(u < p_current + p_former, 1.0, 0.0))


def _activity(
    z: dict[str, Array], y: Array, spec: dict[str, Any], rng: np.random.Generator
) -> Array:
    f = "physical_activity_min_week"
    linear = param(spec, f, "log_odds_meets_per_10y_age") * (z["age"] - z["age"].mean()) / 10
    linear = linear + math.log(param(spec, f, "odds_ratio_diabetes_meets_150")) * y
    b0 = _solve_intercept(linear, 1.0 - param(spec, f, "prevalence_insufficient"))
    meets = rng.random(len(y)) < _sigmoid(b0 + linear)
    cutoff = param(spec, f, "insufficient_minutes_max")
    extra = rng.lognormal(
        math.log(param(spec, f, "extra_minutes_median")),
        param(spec, f, "extra_minutes_log_sd"),
        len(y),
    )
    below = rng.uniform(0.0, cutoff, len(y))
    return np.round(np.where(meets, cutoff + extra, below))


def _normal_factor(
    mean: float,
    sd: float,
    shifts: Array,
    odds_ratio_per_unit: float,
    y: Array,
    rng: np.random.Generator,
) -> Array:
    """Normal values whose odds ratio with the label is `odds_ratio_per_unit` per unit.

    Covariate shifts and the label shift are centred, so the overall mean stays `mean`.
    """
    delta = sd**2 * math.log(odds_ratio_per_unit)
    noise = rng.normal(0.0, sd, len(y))
    return np.asarray(mean + shifts + delta * (y - y.mean()) + noise, dtype=np.float64)


def _cholesterol(
    z: dict[str, Array], y: Array, spec: dict[str, Any], rng: np.random.Generator
) -> Array:
    f = "total_cholesterol_mmol"
    sd = param(spec, f, "sd_mmol")
    # Mean chosen so the share above the cut-off matches the published prevalence.
    mean = param(spec, f, "high_cutoff_mmol") - sd * float(
        norm.ppf(1.0 - param(spec, f, "prevalence_high"))
    )
    shifts = param(spec, f, "per_10y_age_mmol") * (z["age"] - z["age"].mean()) / 10 + param(
        spec, f, "per_bmi_unit_mmol"
    ) * (z["bmi"] - z["bmi"].mean())
    return np.round(
        _normal_factor(mean, sd, shifts, param(spec, f, "odds_ratio_diabetes_per_mmol"), y, rng), 2
    )


def _weight_change(
    z: dict[str, Array], y: Array, spec: dict[str, Any], rng: np.random.Generator
) -> Array:
    f = "weight_change_kg_12m"
    values = _normal_factor(
        param(spec, f, "mean_kg"),
        param(spec, f, "sd_kg"),
        np.zeros(len(y)),
        param(spec, f, "odds_ratio_diabetes_per_kg"),
        y,
        rng,
    )
    return np.round(values, 1)


def _bp_medication(
    z: dict[str, Array], y: Array, spec: dict[str, Any], rng: np.random.Generator
) -> Array:
    f = "bp_medication"
    hypertensive = z["hypertensive"] == 1
    linear = math.log(param(spec, f, "odds_ratio_diabetes")) * y[hypertensive]
    b0 = _solve_intercept(linear, param(spec, f, "share_treated_if_hypertensive"))
    treated = np.zeros(len(y))
    treated[hypertensive] = rng.random(int(hypertensive.sum())) < _sigmoid(b0 + linear)
    return treated


GENERATORS = {
    "smoking_status": _smoking,
    "physical_activity_min_week": _activity,
    "total_cholesterol_mmol": _cholesterol,
    "weight_change_kg_12m": _weight_change,
    "bp_medication": _bp_medication,
}


def add_synthetic_factors(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    spec: dict[str, Any] | None = None,
    seed: int | None = None,
) -> pd.DataFrame:
    """Real TRAINING rows plus the synthetic factors and their flags (a new frame).

    The real columns are returned unchanged; nothing is written back to X_train or y_train.
    """
    spec = spec or load_assumptions()
    rng = np.random.default_rng(spec["seed"] if seed is None else seed)
    z = _covariates(X_train)
    y = y_train.to_numpy(dtype=float)
    out = X_train.copy()
    for factor in FACTORS:
        low, high = spec["factors"][factor]["range"]
        out[factor] = np.clip(GENERATORS[factor](z, y, spec, rng), low, high)
        out[flag(factor)] = True
    return out


def blank_factors(X: pd.DataFrame) -> pd.DataFrame:
    """Real held-out rows: these factors were not measured, so they stay missing."""
    out = X.copy()
    for factor in FACTORS:
        out[factor] = np.nan
        out[flag(factor)] = False
    return out


def _logit_coefficient(target: Array, features: Array) -> float:
    """Coefficient of the first feature in an unpenalised logistic regression."""
    from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]

    model = LogisticRegression(penalty=None, max_iter=2000).fit(features, target)
    return float(model.coef_[0][0])


def realised_effects(df: pd.DataFrame, y_train: pd.Series) -> dict[str, float]:
    """Odds ratios and shares measured in the generated data, to compare with the assumptions.

    Each odds ratio is conditional on the covariates the factor was generated from.
    """
    y = y_train.to_numpy(dtype=float)
    z = _covariates(df)
    smoking = df["smoking_status"].to_numpy()
    out: dict[str, float] = {
        "share_current_smokers": float((smoking == 2).mean()),
        "share_former_smokers": float((smoking == 1).mean()),
    }
    for code, name in ((2, "current"), (1, "former")):
        keep = (smoking == code) | (smoking == 0)
        features = np.column_stack([y[keep], z["sex_male"][keep]])
        out[f"odds_ratio_smoking_{name}"] = math.exp(
            _logit_coefficient((smoking[keep] == code).astype(float), features)
        )

    minutes = df["physical_activity_min_week"].to_numpy(dtype=float)
    meets = (minutes >= 150).astype(float)
    out["share_insufficient_activity"] = float(1.0 - meets.mean())
    out["odds_ratio_activity_meets_150"] = math.exp(
        _logit_coefficient(meets, np.column_stack([y, z["age"]]))
    )

    cholesterol = df["total_cholesterol_mmol"].to_numpy(dtype=float)
    out["share_high_cholesterol"] = float((cholesterol >= 4.91).mean())
    for column, name, covariates in (
        ("total_cholesterol_mmol", "cholesterol_per_mmol", [z["age"], z["bmi"]]),
        ("weight_change_kg_12m", "weight_change_per_kg", []),
    ):
        values = df[column].to_numpy(dtype=float)
        design = np.column_stack([np.ones(len(y)), y, *covariates])
        coef, *_ = np.linalg.lstsq(design, values, rcond=None)
        residual_var = float(np.var(values - design @ coef))
        out[f"odds_ratio_{name}"] = math.exp(float(coef[1]) / residual_var)

    treated = df["bp_medication"].to_numpy(dtype=float)
    hypertensive = z["hypertensive"] == 1
    out["share_bp_medication_if_hypertensive"] = float(treated[hypertensive].mean())
    out["share_bp_medication_if_not_hypertensive"] = float(treated[~hypertensive].mean())
    return out


# realised key -> (factor, parameter in the assumptions file)
COMPARISONS = {
    "share_current_smokers": ("smoking_status", "prevalence_current"),
    "share_former_smokers": ("smoking_status", "prevalence_former"),
    "odds_ratio_smoking_current": ("smoking_status", "odds_ratio_diabetes_current"),
    "odds_ratio_smoking_former": ("smoking_status", "odds_ratio_diabetes_former"),
    "share_insufficient_activity": ("physical_activity_min_week", "prevalence_insufficient"),
    "odds_ratio_activity_meets_150": (
        "physical_activity_min_week",
        "odds_ratio_diabetes_meets_150",
    ),
    "share_high_cholesterol": ("total_cholesterol_mmol", "prevalence_high"),
    "odds_ratio_cholesterol_per_mmol": ("total_cholesterol_mmol", "odds_ratio_diabetes_per_mmol"),
    "odds_ratio_weight_change_per_kg": ("weight_change_kg_12m", "odds_ratio_diabetes_per_kg"),
    "share_bp_medication_if_hypertensive": ("bp_medication", "share_treated_if_hypertensive"),
}


def sanity_table(df: pd.DataFrame, y_train: pd.Series, spec: dict[str, Any]) -> pd.DataFrame:
    realised = realised_effects(df, y_train)
    rows = []
    for key, (factor, name) in COMPARISONS.items():
        item = spec["factors"][factor]["parameters"][name]
        rows.append(
            {
                "factor": factor,
                "quantity": name,
                "assumed": item["value"],
                "realised_in_synthetic_data": round(realised[key], 3),
                "status": item["status"],
            }
        )
    return pd.DataFrame(rows)


def save_plot(df: pd.DataFrame, y_train: pd.Series, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(FACTORS), figsize=(4 * len(FACTORS), 3.6))
    y = y_train.to_numpy()
    for ax, factor in zip(axes, FACTORS, strict=True):
        for label, name in ((0, "not diabetic"), (1, "diabetic")):
            values = df.loc[y == label, factor]
            ax.hist(values, bins=30, density=True, alpha=0.55, label=name)
        ax.set_title(factor, fontsize=9)
    axes[0].legend(fontsize=8)
    fig.suptitle(
        "SYNTHETIC factors on real training rows - generated from assumptions, NOT evidence",
        fontsize=11,
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main() -> None:
    from ..config import CFG, abs_path
    from ..preprocess import build_dataset

    spec = load_assumptions()
    X_train, X_test, y_train, _ = build_dataset()  # type: ignore[no-untyped-call]
    train = add_synthetic_factors(X_train, y_train, spec)
    test = blank_factors(X_test)
    assert train[list(X_train.columns)].equals(X_train), "real training columns changed"
    assert test[list(FACTORS)].isna().all().all(), "a held-out row got a synthetic value"

    table = sanity_table(train, y_train, spec)
    print("SYNTHETIC factor sanity check (real training rows, n =", len(train), ")")
    print(table.to_string(index=False))
    report = abs_path(CFG["paths"]["reports_dir"]) / "synthetic_factors_sanity.csv"
    report.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(report, index=False)
    figure = abs_path(CFG["paths"]["figures_dir"]) / "synthetic_factors.png"
    save_plot(train, y_train, figure)
    print(f"Saved {report} and {figure}")


if __name__ == "__main__":
    main()
