
"""Prepare meal-centred CGMacros samples for C2 glucose forecasting."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

TIME = "Timestamp"
MEAL_TYPE = "Meal Type"
SENSORS = ("Libre GL", "Dexcom GL")
NUTRITION = ("Calories", "Carbs", "Protein", "Fat", "Fiber", "Amount Consumed")
TARGET_MINUTES = tuple(range(0, 241, 15))



def load_participant(path: Path) -> pd.DataFrame:
    """Load and validate one participant's CSV."""
    df = pd.read_csv(path)

    required = {
        TIME,
        MEAL_TYPE,
        *SENSORS,
        "Calories",
        "Carbs",
        "Protein",
        "Fat",
        "Fiber",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"{path.name} is missing columns: {sorted(missing)}"
        )

    if "Amount Consumed" not in df.columns:
        df["Amount Consumed"] = np.nan

    df[TIME] = pd.to_datetime(
        df[TIME], errors="coerce", format="mixed"
    ).astype("datetime64[ns]")

    df = (
        df.dropna(subset=[TIME])
        .sort_values(TIME)
        .reset_index(drop=True)
    )

    for column in (*SENSORS, *NUTRITION):
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    return df



def find_meals(df: pd.DataFrame) -> pd.DataFrame:
    """Identify rows annotated as meal events."""
    types = (
    df[MEAL_TYPE]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
    .replace({"snacks": "snack"})
)
    has_type = types.ne("")
    has_nutrition = df[list(NUTRITION)].notna().any(axis=1)

    meals = df.loc[has_type | has_nutrition].copy()
    meals["_meal_type"] = types.loc[meals.index].replace("", "Unspecified")

    # Duplicate event timestamps must not create duplicate samples.
    return meals.drop_duplicates(subset=[TIME]).reset_index(drop=True)


def nearest_reading(
    timestamps_ns: np.ndarray,
    values: np.ndarray,
    target_ns: int,
    tolerance_ns: int,
) -> float:
    """Find a finite glucose value near a target timestamp."""
    if len(timestamps_ns) == 0:
        return np.nan

    position = int(np.searchsorted(timestamps_ns, target_ns))
    candidates = [i for i in (position - 1, position)
                  if 0 <= i < len(timestamps_ns)]
    if not candidates:
        return np.nan

    best = min(candidates, key=lambda i: abs(int(timestamps_ns[i]) - target_ns))
    if abs(int(timestamps_ns[best]) - target_ns) > tolerance_ns:
        return np.nan

    value = values[best]
    return float(value) if np.isfinite(value) else np.nan


def process_participant(
    participant_id: str,
    df: pd.DataFrame,
    tolerance_minutes: int,
) -> list[dict]:
    """Create meal-centred four-hour trajectory samples."""
    meals = find_meals(df)
    if meals.empty:
        return []

    all_times_ns = df[TIME].astype("int64").to_numpy()
    tolerance_ns = tolerance_minutes * 60_000_000_000
    sensor_data = {}

    for sensor in SENSORS:
        values = df[sensor].to_numpy(dtype=float)
        valid = np.isfinite(values)
        sensor_data[sensor] = (
            all_times_ns[valid],
            values[valid],
        )

    records = []

    for i, meal in meals.iterrows():
        meal_time = meal[TIME]
        meal_ns = int(meal_time.value)

        next_meal = (
            meals.iloc[i + 1][TIME]
            if i + 1 < len(meals)
            else pd.NaT
        )
        overlap = bool(
            pd.notna(next_meal)
            and meal_time < next_meal <= meal_time + pd.Timedelta(hours=4)
        )

        record = {
            "participant_id": participant_id,
            "meal_timestamp": meal_time.isoformat(),
            "meal_type": meal["_meal_type"],
            "next_meal_timestamp": (
                next_meal.isoformat() if pd.notna(next_meal) else None
            ),
            "next_meal_within_4h": overlap,
        }

        for column in NUTRITION:
            name = column.lower().replace(" ", "_")
            record[name] = (
                float(meal[column]) if pd.notna(meal[column]) else np.nan
            )

        for sensor in SENSORS:
            sensor_name = sensor.lower().replace(" ", "_")
            times_ns, values = sensor_data[sensor]

            # Baseline must be measured at or before the meal, never after it.
            before = (times_ns < meal_ns) & (
    times_ns >= meal_ns - 15 * 60_000_000_000
)
            if before.any():
                previous_time = times_ns[before][-1]
                previous_value = values[before][-1]
                record[f"premeal_{sensor_name}"] = float(previous_value)
                record[f"premeal_{sensor_name}_minutes_before"] = (
                    meal_ns - int(previous_time)
                ) / 60_000_000_000
            else:
                record[f"premeal_{sensor_name}"] = np.nan
                record[f"premeal_{sensor_name}_minutes_before"] = np.nan

            for minute in TARGET_MINUTES:
                target_ns = meal_ns + minute * 60_000_000_000
                record[f"{sensor_name}_t{minute:03d}"] = nearest_reading(
                    times_ns, values, target_ns, tolerance_ns
                )

        # Use Libre as the initial target sensor; Dexcom is retained for
        # comparison and later sensitivity analysis.
        target_names = [f"libre_gl_t{minute:03d}" for minute in TARGET_MINUTES]
        target_count = sum(pd.notna(record[name]) for name in target_names)
        required_nutrition = ("carbs", "protein", "fat", "fiber")
        missing_nutrition = [
            name for name in required_nutrition
            if pd.isna(record.get(name))
        ]
        has_baseline = pd.notna(record["premeal_libre_gl"])
        complete_trajectory = target_count == len(TARGET_MINUTES)

        reasons = []
        if overlap:
            reasons.append("overlapping_meal")
        if not has_baseline:
            reasons.append("missing_premeal_glucose")
        if not complete_trajectory:
            reasons.append("incomplete_4h_trajectory")
        if missing_nutrition:
            reasons.append("missing_required_nutrition")

        record.update({
            "libre_target_count_15min": target_count,
            "complete_4h_libre_trajectory": complete_trajectory,
            "has_premeal_libre_glucose": has_baseline,
            "missing_nutrition_fields": ",".join(missing_nutrition),
            "eligible_for_clean_dataset": not reasons,
            "exclusion_reasons": ";".join(reasons),
        })
        records.append(record)

    return records


def prepare_dataset(
    data_dir: Path,
    output_dir: Path,
    tolerance_minutes: int = 5,
) -> dict:
    """Process participants and write derived datasets and quality reports."""
    if tolerance_minutes < 0:
        raise ValueError("Tolerance must be non-negative.")
    if not data_dir.is_dir():
        raise FileNotFoundError(f"CGMacros directory not found: {data_dir}")

    files = sorted(data_dir.glob("CGMacros-*/CGMacros-*.csv"))
    files = [p for p in files if p.parent.name == p.stem]
    if not files:
        raise FileNotFoundError(
            f"No participant CSVs found under {data_dir}. "
            "Expected CGMacros-###/CGMacros-###.csv."
        )

    records = []
    failures = []

    for path in files:
        participant_id = path.parent.name.removeprefix("CGMacros-")
        try:
            participant = load_participant(path)
            participant_records = process_participant(
                participant_id, participant, tolerance_minutes
            )
            records.extend(participant_records)
            LOGGER.info(
                "%s: %d rows, %d meal samples",
                participant_id, len(participant), len(participant_records),
            )
        except (ValueError, OSError, pd.errors.ParserError) as exc:
            LOGGER.exception("Could not process %s", path)
            failures.append({
                "participant_id": participant_id,
                "file": str(path),
                "error": str(exc),
            })

    if not records:
        raise RuntimeError("No samples were generated. Check the input files.")

    output_dir.mkdir(parents=True, exist_ok=True)
    all_samples = pd.DataFrame(records)
    audit_columns = [
        "participant_id", "meal_timestamp", "meal_type",
        "next_meal_timestamp", "next_meal_within_4h",
        "has_premeal_libre_glucose", "libre_target_count_15min",
        "complete_4h_libre_trajectory", "missing_nutrition_fields",
        "eligible_for_clean_dataset", "exclusion_reasons",
    ]
    audit = all_samples[audit_columns].copy()
    clean = all_samples.loc[all_samples["eligible_for_clean_dataset"]].copy()

    all_samples.to_csv(output_dir / "cgmacros_meal_samples_all.csv", index=False)
    clean.to_csv(output_dir / "cgmacros_meal_samples_clean.csv", index=False)
    audit.to_csv(output_dir / "cgmacros_meal_quality_audit.csv", index=False)

    summary = {
        "source_directory": str(data_dir.resolve()),
        "output_directory": str(output_dir.resolve()),
        "participant_files_found": len(files),
        "participants_with_processing_failures": failures,
        "meal_samples_total": len(all_samples),
        "eligible_clean_samples": len(clean),
        "excluded_samples": len(all_samples) - len(clean),
        "overlapping_meals": int(all_samples["next_meal_within_4h"].sum()),
        "target_sensor": "Libre GL",
        "target_offsets_minutes": list(TARGET_MINUTES),
        "matching_tolerance_minutes": tolerance_minutes,
        "notes": [
            "Overlapping meals are excluded from the clean dataset.",
            "Target values are matched by timestamp, not row position.",
            "Some CGMacros glucose values may be interpolated.",
            "This script does not train models or assign clinical risk labels.",
            "Split participants before fitting or evaluating any model.",
        ],
    }
    (output_dir / "preprocessing_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    LOGGER.info("Total meal samples: %d", len(all_samples))
    LOGGER.info("Eligible clean samples: %d", len(clean))
    LOGGER.info("Excluded samples: %d", len(all_samples) - len(clean))
    LOGGER.info("Output directory: %s", output_dir.resolve())
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/c2"),
    )
    parser.add_argument("--tolerance-minutes", type=int, default=5)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    summary = prepare_dataset(
        args.data_dir, args.output_dir, args.tolerance_minutes
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
