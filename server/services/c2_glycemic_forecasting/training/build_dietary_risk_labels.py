"""Label C2 meals with the research-defined post-meal response indicator.

Label (decided 2026-10-18): a meal is positive when at least one genuine Libre reading taken
from +15 to +240 minutes after the meal (inclusive) is above 180 mg/dL. It is a research-defined
post-meal hyperglycaemic response indicator, not a clinically validated risk category.

Labels come only from observed post-meal glucose. Rules:

- Only genuine Libre readings count. CGMacros fills the minutes between readings by linear
  interpolation, and a grid value near the window edge can borrow height from a reading outside
  the window.
- The window must be covered: no gap longer than `MAX_GAP_MINUTES` between consecutive
  readings or the window edges. CGMacros interpolates across long sensor gaps, which could hide
  a peak and create a false negative.
- A meal is "isolated" when no other logged meal is within four hours before or after it. The
  clean dataset already excludes meals followed by another meal within four hours; this script
  flags meals preceded by one, whose window overlaps the earlier meal's response.

Only train and validation participants can be processed. The test participants stay sealed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)


def _load_prepare_dataset() -> ModuleType:
    # Training scripts are standalone files, not a package, so load the sibling by path.
    path = Path(__file__).with_name("prepare_dataset.py")
    spec = importlib.util.spec_from_file_location("c2_prepare_dataset", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare_dataset = _load_prepare_dataset()

DATA_ROOT = Path.home() / "Desktop" / "CGMacros_C2_processed_premeal_fix"
CLEAN_FILE = DATA_ROOT / "cgmacros_meal_samples_clean.csv"
OUTPUT_DIR = DATA_ROOT / "dietary_risk_labels"
OUTPUT_FILES = ("dietary_risk_labels.csv", "dietary_risk_labels_summary.json")

LABEL_NAME = "above_180_within_4h"
THRESHOLD_MG_DL = 180.0
WINDOW_START_MINUTES = 15
WINDOW_END_MINUTES = 240
MAX_GAP_MINUTES = 20.0
ISOLATION_MINUTES = 240
ALLOWED_SPLITS = ("train", "validation")
MINUTE_NS = prepare_dataset.MINUTE_NS

LABEL_DEFINITION = (
    "Positive when at least one genuine Libre reading from +15 to +240 minutes after the meal "
    "(inclusive) is above 180 mg/dL. Research-defined post-meal hyperglycaemic response "
    "indicator; not a clinical diagnosis or a clinically validated risk category."
)


@dataclass(frozen=True)
class MealLabel:
    """Outcome label for one meal. `label` is None when the window cannot support one."""

    label: int | None
    readings_in_window: int
    max_gap_minutes: float
    observed_max_glucose: float
    exclusion_reason: str


def label_meal(genuine_times_ns: np.ndarray, genuine_values: np.ndarray, meal_ns: int) -> MealLabel:
    """Label one meal from genuine Libre readings (sorted times, finite values)."""
    start = meal_ns + WINDOW_START_MINUTES * MINUTE_NS
    end = meal_ns + WINDOW_END_MINUTES * MINUTE_NS
    inside = (genuine_times_ns >= start) & (genuine_times_ns <= end)
    times = genuine_times_ns[inside]
    values = genuine_values[inside]

    if times.size == 0:
        return MealLabel(
            None, 0, float(WINDOW_END_MINUTES - WINDOW_START_MINUTES), np.nan, "no_readings"
        )

    edges = np.concatenate(([start], times, [end]))
    max_gap = float(np.diff(edges).max() / MINUTE_NS)
    observed_max = float(values.max())
    if max_gap > MAX_GAP_MINUTES:
        return MealLabel(None, int(times.size), max_gap, observed_max, "reading_gap")

    return MealLabel(
        int(observed_max > THRESHOLD_MG_DL), int(times.size), max_gap, observed_max, ""
    )


def minutes_since_previous_meal(meal_times_ns: np.ndarray, meal_ns: int) -> float:
    """Minutes since the latest logged meal strictly before `meal_ns`; NaN if there is none."""
    position = int(np.searchsorted(meal_times_ns, meal_ns, side="left"))
    if position == 0:
        return np.nan
    return float((meal_ns - int(meal_times_ns[position - 1])) / MINUTE_NS)


def label_participant(raw: pd.DataFrame, meals: pd.DataFrame) -> pd.DataFrame:
    """Label one participant's clean meals using their raw minute-level data."""
    times_ns = raw[prepare_dataset.TIME].astype("int64").to_numpy()
    values = raw["Libre GL"].to_numpy(dtype=float)
    finite = np.isfinite(values)
    times_ns, values = times_ns[finite], values[finite]
    genuine = prepare_dataset.genuine_reading_mask(times_ns, values)
    genuine_times, genuine_values = times_ns[genuine], values[genuine]

    # Every logged meal counts for isolation, including meals excluded from the clean dataset.
    logged = prepare_dataset.find_meals(raw)[prepare_dataset.TIME].astype("int64").to_numpy()

    records = []
    for meal_timestamp in meals["meal_timestamp"]:
        meal_ns = int(pd.Timestamp(meal_timestamp).value)
        label = label_meal(genuine_times, genuine_values, meal_ns)
        previous_gap = minutes_since_previous_meal(logged, meal_ns)
        preceded = bool(np.isfinite(previous_gap) and previous_gap <= ISOLATION_MINUTES)
        records.append(
            {
                "meal_timestamp": meal_timestamp,
                LABEL_NAME: label.label,
                "label_valid": label.label is not None,
                "label_exclusion_reason": label.exclusion_reason,
                "genuine_readings_in_window": label.readings_in_window,
                "max_reading_gap_minutes": label.max_gap_minutes,
                "observed_max_glucose": label.observed_max_glucose,
                "minutes_since_previous_meal": previous_gap,
                "previous_meal_within_4h": preceded,
                "isolated_meal": not preceded,
            }
        )
    return pd.DataFrame(records)


def build_labels(
    data_dir: Path,
    clean_file: Path,
    output_dir: Path,
    splits: tuple[str, ...] = ALLOWED_SPLITS,
    overwrite: bool = False,
) -> dict[str, object]:
    """Write per-meal labels and a summary for the selected splits."""
    if not set(splits) <= set(ALLOWED_SPLITS):
        raise ValueError(f"Only {ALLOWED_SPLITS} can be labelled; the test split stays sealed.")
    existing = [name for name in OUTPUT_FILES if (output_dir / name).exists()]
    if existing and not overwrite:
        raise FileExistsError(f"{output_dir} already contains {', '.join(existing)}.")

    clean = pd.read_csv(clean_file, dtype={"participant_id": str})
    if clean["next_meal_within_4h"].astype(bool).any():
        raise ValueError("The clean dataset must not contain meals followed within 4 hours.")
    if clean.duplicated(["participant_id", "meal_timestamp"]).any():
        raise ValueError("The clean dataset contains duplicate meals.")
    clean = clean.loc[clean["split"].isin(splits)]
    if clean.empty:
        raise ValueError(f"No clean meals for splits {splits}.")

    frames = []
    for participant_id, meals in clean.groupby("participant_id", sort=True):
        path = data_dir / f"CGMacros-{participant_id}" / f"CGMacros-{participant_id}.csv"
        labelled = label_participant(prepare_dataset.load_participant(path), meals)
        labelled.insert(0, "split", meals["split"].iloc[0])
        labelled.insert(0, "participant_id", participant_id)
        frames.append(labelled)
        LOGGER.info("%s: %d meals labelled", participant_id, len(labelled))

    labels = pd.concat(frames, ignore_index=True)
    labels[LABEL_NAME] = labels[LABEL_NAME].astype("Int64")
    labels["primary_eligible"] = labels["label_valid"] & labels["isolated_meal"]

    summary: dict[str, object] = {
        "label_name": LABEL_NAME,
        "label_definition": LABEL_DEFINITION,
        "threshold_mg_dl": THRESHOLD_MG_DL,
        "window_minutes": [WINDOW_START_MINUTES, WINDOW_END_MINUTES],
        "max_reading_gap_minutes": MAX_GAP_MINUTES,
        "isolation_minutes": ISOLATION_MINUTES,
        "clean_file": str(clean_file.resolve()),
        "raw_data_dir": str(data_dir.resolve()),
        "splits": list(splits),
        "per_split": {},
    }
    per_split: dict[str, object] = {}
    for split, group in labels.groupby("split", sort=True):
        primary = group.loc[group["primary_eligible"]]
        per_split[str(split)] = {
            "participants": int(group["participant_id"].nunique()),
            "clean_meals": len(group),
            "invalid_label_window": group["label_exclusion_reason"]
            .value_counts()
            .drop("", errors="ignore")
            .to_dict(),
            "preceded_by_meal_within_4h": int(group["previous_meal_within_4h"].sum()),
            "primary_meals": len(primary),
            "primary_positive": int(primary[LABEL_NAME].sum()),
            "primary_participants_with_positive": int(
                primary.groupby("participant_id")[LABEL_NAME].max().sum()
            ),
        }
    summary["per_split"] = per_split

    output_dir.mkdir(parents=True, exist_ok=True)
    labels.to_csv(output_dir / OUTPUT_FILES[0], index=False)
    (output_dir / OUTPUT_FILES[1]).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--clean-file", type=Path, default=CLEAN_FILE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--splits", nargs="+", choices=ALLOWED_SPLITS, default=list(ALLOWED_SPLITS))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    summary = build_labels(
        args.data_dir, args.clean_file, args.output_dir, tuple(args.splits), args.overwrite
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
