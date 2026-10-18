"""Prepare meal-centred CGMacros samples for C2 glucose forecasting."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

TIME = "Timestamp"
MEAL_TYPE = "Meal Type"
SENSORS = ("Libre GL", "Dexcom GL")
NUTRITION = ("Calories", "Carbs", "Protein", "Fat", "Fiber", "Amount Consumed")
TARGET_MINUTES = tuple(range(0, 241, 15))
OUTPUT_FILES = (
    "cgmacros_meal_samples_all.csv",
    "cgmacros_meal_samples_clean.csv",
    "cgmacros_meal_quality_audit.csv",
    "preprocessing_summary.json",
)

# Fixed participant-level split. It is never regenerated, so assignments cannot change
# when participants are missing or excluded.
DEFAULT_MANIFEST = Path(__file__).with_name("cgmacros_participant_split.json")
SPLIT_NAMES = ("train", "validation", "test")
UNASSIGNED = "unassigned"

MINUTE_NS = 60_000_000_000
PREMEAL_MAX_MINUTES = 15
LIBRE_READING_INTERVAL_MINUTES = 15
# Slope changes within this many minutes vote on the sensor's reading phase.
PHASE_WINDOW_MINUTES = 360
SLOPE_TOLERANCE = 1e-9
LINEARITY_TOLERANCE = 0.01


def normalize_participant_id(value: object) -> str:
    """Return a participant ID as a three-digit string, for example 10 -> "010"."""
    text = str(value).strip()
    if not text.isdigit():
        raise ValueError(f"Invalid participant ID: {value!r}")
    return text.zfill(3)


def load_split_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, str]:
    """Return a mapping from participant ID to its fixed split name."""
    data = json.loads(path.read_text(encoding="utf-8"))
    splits = data.get("splits") if isinstance(data, dict) else None

    if not isinstance(splits, dict) or set(splits) != set(SPLIT_NAMES):
        raise ValueError(f"{path} must define exactly these splits: {', '.join(SPLIT_NAMES)}")

    assignment: dict[str, str] = {}
    for split_name in SPLIT_NAMES:
        for raw_id in splits[split_name]:
            participant_id = normalize_participant_id(raw_id)
            if participant_id in assignment:
                raise ValueError(f"Participant {participant_id} appears more than once in {path}")
            assignment[participant_id] = split_name

    return assignment


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
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")

    if "Amount Consumed" not in df.columns:
        df["Amount Consumed"] = np.nan

    df[TIME] = pd.to_datetime(df[TIME], errors="coerce", format="mixed").astype("datetime64[ns]")

    df = df.dropna(subset=[TIME]).sort_values(TIME).reset_index(drop=True)

    for column in (*SENSORS, *NUTRITION):
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def find_meals(df: pd.DataFrame) -> pd.DataFrame:
    """Identify rows annotated as meal events."""
    types = (
        df[MEAL_TYPE].fillna("").astype(str).str.strip().str.lower().replace({"snacks": "snack"})
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
    candidates = [i for i in (position - 1, position) if 0 <= i < len(timestamps_ns)]
    if not candidates:
        return np.nan

    best = min(candidates, key=lambda i: abs(int(timestamps_ns[i]) - target_ns))
    if abs(int(timestamps_ns[best]) - target_ns) > tolerance_ns:
        return np.nan

    value = values[best]
    return float(value) if np.isfinite(value) else np.nan


def genuine_reading_mask(
    times_ns: np.ndarray,
    values: np.ndarray,
    interval_minutes: int = LIBRE_READING_INTERVAL_MINUTES,
) -> np.ndarray:
    """Flag genuine sensor readings among CGMacros' minute-level glucose values.

    CGMacros fills the minutes between genuine Libre readings (every 15 minutes) by linear
    interpolation, so most minute values depend on the next genuine reading. A value is
    accepted as genuine only if all of these hold:

    1. It lies on the sensor's reading phase: the most common minute-of-interval among
       nearby slope changes. Interpolated values cannot change slope between readings.
    2. It is a whole number, as genuine Libre readings are.
    3. The values since the previous candidate reading are exactly linear between the two.
       The first candidate cannot be checked and is therefore rejected.

    `times_ns` must be strictly increasing and `values` finite, for one sensor.
    """
    mask = np.zeros(len(values), dtype=bool)
    if len(values) < 3:
        return mask
    if np.any(np.diff(times_ns) <= 0):
        raise ValueError("Glucose timestamps must be strictly increasing.")

    minutes = times_ns / MINUTE_NS
    slopes = np.diff(values) / np.diff(minutes)
    knots = np.flatnonzero(np.abs(np.diff(slopes)) > SLOPE_TOLERANCE) + 1
    if knots.size == 0:
        return mask

    whole_minutes = times_ns // MINUTE_NS
    knot_minutes = whole_minutes[knots]
    knot_phases = knot_minutes % interval_minutes
    window_start = np.searchsorted(knot_minutes, knot_minutes - PHASE_WINDOW_MINUTES)
    window_end = np.searchsorted(knot_minutes, knot_minutes + PHASE_WINDOW_MINUTES, side="right")
    voted_phases = np.array(
        [
            np.bincount(knot_phases[start:end], minlength=interval_minutes).argmax()
            for start, end in zip(window_start, window_end, strict=True)
        ]
    )

    # Each value takes the phase voted for at its nearest slope change.
    right = np.clip(np.searchsorted(knot_minutes, whole_minutes), 0, len(knots) - 1)
    left = np.clip(right - 1, 0, len(knots) - 1)
    nearest = np.where(
        np.abs(knot_minutes[left] - whole_minutes) <= np.abs(knot_minutes[right] - whole_minutes),
        left,
        right,
    )
    on_phase = (times_ns % MINUTE_NS == 0) & (
        whole_minutes % interval_minutes == voted_phases[nearest]
    )
    whole_number = np.abs(values - np.round(values)) < 1e-9
    candidates = np.flatnonzero(on_phase & whole_number)

    for previous, current in zip(candidates[:-1], candidates[1:], strict=True):
        between = slice(previous + 1, current)
        expected = np.interp(
            minutes[between],
            [minutes[previous], minutes[current]],
            [values[previous], values[current]],
        )
        if np.all(np.abs(values[between] - expected) <= LINEARITY_TOLERANCE):
            mask[current] = True

    return mask


def last_reading_before(
    times_ns: np.ndarray,
    values: np.ndarray,
    meal_ns: int,
    max_minutes: int = PREMEAL_MAX_MINUTES,
) -> tuple[float, float]:
    """Return the last reading strictly before the meal and how many minutes earlier it was."""
    position = int(np.searchsorted(times_ns, meal_ns, side="left"))
    if position == 0:
        return np.nan, np.nan

    minutes_before = (meal_ns - int(times_ns[position - 1])) / MINUTE_NS
    if minutes_before > max_minutes:
        return np.nan, np.nan

    return float(values[position - 1]), minutes_before


def process_participant(
    participant_id: str,
    df: pd.DataFrame,
    tolerance_minutes: int,
) -> list[dict[str, object]]:
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

    # The Libre baseline uses genuine readings only, never values interpolated towards a
    # reading taken at or after the meal. Dexcom is retained for comparison only and keeps
    # the nearest earlier value.
    libre_times, libre_values = sensor_data["Libre GL"]
    genuine = genuine_reading_mask(libre_times, libre_values)
    premeal_sources = {
        "Libre GL": (libre_times[genuine], libre_values[genuine]),
        "Dexcom GL": sensor_data["Dexcom GL"],
    }

    records = []

    for position, (_, meal) in enumerate(meals.iterrows()):
        meal_time = meal[TIME]
        meal_ns = int(meal_time.value)

        next_meal = meals.iloc[position + 1][TIME] if position + 1 < len(meals) else pd.NaT
        overlap = bool(
            pd.notna(next_meal) and meal_time < next_meal <= meal_time + pd.Timedelta(hours=4)
        )

        record = {
            "participant_id": participant_id,
            "meal_timestamp": meal_time.isoformat(),
            "meal_type": meal["_meal_type"],
            "next_meal_timestamp": (next_meal.isoformat() if pd.notna(next_meal) else None),
            "next_meal_within_4h": overlap,
        }

        for column in NUTRITION:
            name = column.lower().replace(" ", "_")
            record[name] = float(meal[column]) if pd.notna(meal[column]) else np.nan

        for sensor in SENSORS:
            sensor_name = sensor.lower().replace(" ", "_")
            times_ns, values = sensor_data[sensor]

            # Baseline must be measured strictly before the meal, never at or after it.
            premeal_value, minutes_before = last_reading_before(*premeal_sources[sensor], meal_ns)
            record[f"premeal_{sensor_name}"] = premeal_value
            record[f"premeal_{sensor_name}_minutes_before"] = minutes_before

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
        missing_nutrition = [name for name in required_nutrition if pd.isna(record.get(name))]
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

        record.update(
            {
                "libre_target_count_15min": target_count,
                "complete_4h_libre_trajectory": complete_trajectory,
                "has_premeal_libre_glucose": has_baseline,
                "missing_nutrition_fields": ",".join(missing_nutrition),
                "eligible_for_clean_dataset": not reasons,
                "exclusion_reasons": ";".join(reasons),
            }
        )
        records.append(record)

    return records


def prepare_dataset(
    data_dir: Path,
    output_dir: Path,
    tolerance_minutes: int = 5,
    split_manifest: Path = DEFAULT_MANIFEST,
    splits: Sequence[str] | None = None,
    overwrite: bool = False,
) -> dict[str, object]:
    """Process participants and write derived datasets and quality reports.

    Every sample is labelled with its participant's split from the fixed manifest. When
    `splits` is given, only participants assigned to those splits have their files opened.
    """
    if tolerance_minutes < 0:
        raise ValueError("Tolerance must be non-negative.")
    if not data_dir.is_dir():
        raise FileNotFoundError(f"CGMacros directory not found: {data_dir}")

    assignment = load_split_manifest(split_manifest)
    participant_ids = None
    if splits is not None:
        unknown_splits = set(splits) - set(SPLIT_NAMES)
        if unknown_splits:
            raise ValueError(f"Unknown split names: {sorted(unknown_splits)}")
        participant_ids = {pid for pid, split in assignment.items() if split in set(splits)}

    existing = [name for name in OUTPUT_FILES if (output_dir / name).exists()]
    if existing and not overwrite:
        raise FileExistsError(
            f"{output_dir} already contains {', '.join(existing)}. "
            "Choose a new output directory or pass --overwrite."
        )

    files = sorted(data_dir.glob("CGMacros-*/CGMacros-*.csv"))
    files = [p for p in files if p.parent.name == p.stem]
    selected_without_files: list[str] = []
    if participant_ids is not None:
        found = {p.parent.name.removeprefix("CGMacros-") for p in files}
        selected_without_files = sorted(participant_ids - found)
        files = [p for p in files if p.parent.name.removeprefix("CGMacros-") in participant_ids]
    if not files:
        raise FileNotFoundError(
            f"No participant CSVs found under {data_dir}. Expected CGMacros-###/CGMacros-###.csv."
        )

    records: list[dict[str, object]] = []
    failures = []

    for path in files:
        participant_id = path.parent.name.removeprefix("CGMacros-")
        try:
            participant = load_participant(path)
            participant_records = process_participant(
                participant_id, participant, tolerance_minutes
            )
            split = assignment.get(participant_id, UNASSIGNED)
            records.extend(
                {"participant_id": participant_id, "split": split, **record}
                for record in participant_records
            )
            LOGGER.info(
                "%s: %d rows, %d meal samples",
                participant_id,
                len(participant),
                len(participant_records),
            )
        except (ValueError, OSError, pd.errors.ParserError) as exc:
            LOGGER.exception("Could not process %s", path)
            failures.append(
                {
                    "participant_id": participant_id,
                    "file": str(path),
                    "error": str(exc),
                }
            )

    if not records:
        raise RuntimeError("No samples were generated. Check the input files.")

    output_dir.mkdir(parents=True, exist_ok=True)
    all_samples = pd.DataFrame(records)
    audit_columns = [
        "participant_id",
        "split",
        "meal_timestamp",
        "meal_type",
        "next_meal_timestamp",
        "next_meal_within_4h",
        "has_premeal_libre_glucose",
        "libre_target_count_15min",
        "complete_4h_libre_trajectory",
        "missing_nutrition_fields",
        "eligible_for_clean_dataset",
        "exclusion_reasons",
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
        "split_manifest": str(split_manifest.resolve()),
        "selected_splits": list(splits) if splits is not None else "all participant files",
        "selected_participants_without_files": selected_without_files,
        "participants_not_in_split_manifest": sorted(
            {str(r["participant_id"]) for r in records if r["split"] == UNASSIGNED}
        ),
        "participants_with_processing_failures": failures,
        "meal_samples_total": len(all_samples),
        "eligible_clean_samples": len(clean),
        "excluded_samples": len(all_samples) - len(clean),
        "overlapping_meals": int(all_samples["next_meal_within_4h"].sum()),
        "meals_without_genuine_premeal_libre_glucose": int(
            (~all_samples["has_premeal_libre_glucose"]).sum()
        ),
        "target_sensor": "Libre GL",
        "target_offsets_minutes": list(TARGET_MINUTES),
        "matching_tolerance_minutes": tolerance_minutes,
        "premeal_libre_method": (
            "Last genuine Libre reading strictly before the meal, at most "
            f"{PREMEAL_MAX_MINUTES} minutes earlier. Genuine readings are on the sensor's "
            f"{LIBRE_READING_INTERVAL_MINUTES}-minute phase, whole numbers, and linear with "
            "the previous reading; interpolated values are never used."
        ),
        "notes": [
            "Overlapping meals are excluded from the clean dataset.",
            "Target values are matched by timestamp, not row position.",
            "CGMacros glucose values between genuine sensor readings are interpolated.",
            "libre_gl_t000 is interpolated at meal time and must not be used as an input.",
            "This script does not train models or assign clinical risk labels.",
            "Split with split_dataset.py, which uses the fixed manifest's split column.",
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
    parser.add_argument("--split-manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--splits",
        nargs="+",
        choices=SPLIT_NAMES,
        help="Process only participants assigned to these splits in the manifest.",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    summary = prepare_dataset(
        args.data_dir,
        args.output_dir,
        args.tolerance_minutes,
        split_manifest=args.split_manifest,
        splits=args.splits,
        overwrite=args.overwrite,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
