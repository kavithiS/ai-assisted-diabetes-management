"""Build the C3 South Asian dataset from two real Bangladesh sources.

Sources (both real, both CC BY 4.0):
- DiaBD: 5,288 adults with a realistic diabetes rate. Main development data.
- Narsingdi hospital (rn9m3zb7nt): 1,065 clinic patients, mostly diabetic.
  Used as a second site to test whether the model transfers.

Excluded on purpose:
- Pabna 465-row file (vxnyysk9vc): every row is already in the Narsingdi file.
- xv25yjbzkm "Bangladesh" 20,000 rows: hard-clipped ranges, uniform ages and
  8-decimal BMI look generated, not measured.
- Early-stage symptoms (UCI 529): symptoms of diabetes, not risk factors.
- CKD in diabetics (hjkzgbxgv5): every patient is diabetic, so no diabetes label.

Run (after python -m src.external_data):
    python -m src.south_asia_dataset
"""

import numpy as np
import pandas as pd

from .config import CFG, abs_path

RAW = "data/raw/external"

# feature -> (factor group from proposal Table 3.1, DiaBD source, Narsingdi source)
SCHEMA = {
    "age": ("1 Demographic", "age", "Age"),
    "sex_male": ("1 Demographic", "gender", "not recorded"),
    "bmi": ("2 Anthropometric", "bmi", "BMI"),
    "systolic_bp": ("7 Clinical", "systolic_bp", "BP(Systolic)"),
    "diastolic_bp": ("7 Clinical", "diastolic_bp", "BP(Diastolic)"),
    "pulse_rate": ("7 Clinical", "pulse_rate", "not recorded"),
    "glucose_mmol": ("7 Clinical (optional)", "glucose", "Glucose / 18"),
    "family_history_diabetes": (
        "5 Medical & family history",
        "family_diabetes",
        "DiabetesPedigreeFunction > 0",
    ),
    "family_history_hypertension": (
        "5 Medical & family history",
        "family_hypertension",
        "not recorded",
    ),
    "hypertensive": ("5 Medical & family history", "hypertensive", "not recorded"),
    "cardiovascular_disease": (
        "5 Medical & family history",
        "cardiovascular_disease",
        "not recorded",
    ),
    "stroke": ("5 Medical & family history", "stroke", "not recorded"),
}
# Features measured in BOTH sites; only these are used across sites.
COMMON = ["age", "bmi", "systolic_bp", "diastolic_bp", "family_history_diabetes", "glucose_mmol"]

# Physiologically impossible values become missing instead of being trusted.
PLAUSIBLE = {
    "bmi": (12, 70),
    "systolic_bp": (70, 260),
    "diastolic_bp": (40, 150),
    "pulse_rate": (35, 200),
    "glucose_mmol": (1.5, 40),
}


def apply_plausibility(df: pd.DataFrame) -> pd.DataFrame:
    for col, (low, high) in PLAUSIBLE.items():
        df[col] = df[col].where(df[col].between(low, high))
    return df


def load_diabd() -> pd.DataFrame:
    d = pd.read_csv(abs_path(f"{RAW}/bangladesh_diabd.csv"))
    df = pd.DataFrame(
        {
            "age": d["age"],
            "sex_male": (d["gender"] == "Male").astype(int),
            # Recomputed from height and weight; the file's own BMI has a few typos.
            "bmi": d["weight"] / d["height"] ** 2,
            "systolic_bp": d["systolic_bp"],
            "diastolic_bp": d["diastolic_bp"],
            "pulse_rate": d["pulse_rate"],
            "glucose_mmol": d["glucose"],
            "family_history_diabetes": d["family_diabetes"],
            "family_history_hypertension": d["family_hypertension"],
            "hypertensive": d["hypertensive"],
            "cardiovascular_disease": d["cardiovascular_disease"],
            "stroke": d["stroke"],
            "target": (d["diabetic"] == "Yes").astype(int),
        }
    )
    df["source"] = "diabd"
    return df


def load_narsingdi() -> pd.DataFrame:
    d = pd.read_csv(abs_path(f"{RAW}/bangladesh_t2d_clinical.csv")).drop_duplicates()
    df = pd.DataFrame(
        {
            "age": d["Age"],
            "bmi": d["BMI"],
            "systolic_bp": d["BP(Systolic)"],
            "diastolic_bp": d["BP(Diastolic)"],
            "glucose_mmol": d["Glucose"] / 18.0,  # mg/dL -> mmol/L
            # Assumption: this column holds a count of relatives with diabetes (0-8).
            "family_history_diabetes": (d["DiabetesPedigreeFunction"] > 0).astype(int),
            "target": d["Type-2 Diabetic"],
        }
    )
    for col in SCHEMA:
        if col not in df:
            df[col] = np.nan
    df["source"] = "narsingdi"
    return df[list(SCHEMA) + ["target", "source"]]


def build() -> pd.DataFrame:
    df = pd.concat([load_diabd(), load_narsingdi()], ignore_index=True)
    return apply_plausibility(df)


def main():
    df = build()
    out = abs_path(CFG["south_asia"]["processed_file"])
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    rows = []
    for k, (group, diabd, narsingdi) in SCHEMA.items():
        miss = df.groupby("source")[k].apply(lambda s: round(s.isna().mean() * 100, 1))
        rows.append((k, group, diabd, narsingdi, miss["diabd"], miss["narsingdi"]))
    schema = pd.DataFrame(
        rows,
        columns=[
            "feature",
            "factor_group",
            "diabd_source",
            "narsingdi_source",
            "diabd_missing_percent",
            "narsingdi_missing_percent",
        ],
    )
    report = abs_path("outputs/reports/south_asia_schema.csv")
    report.parent.mkdir(parents=True, exist_ok=True)
    schema.to_csv(report, index=False)

    for source, part in df.groupby("source"):
        print(f"{source}: {len(part)} rows, diabetes rate {part['target'].mean():.3f}")
    print(f"Saved {out} and {report}")


if __name__ == "__main__":
    main()
