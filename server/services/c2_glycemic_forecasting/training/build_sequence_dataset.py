"""Build 120-minute glucose-history sequences for C2 sequence forecasting.

For each meal in the corrected (leak-free) split files, this takes the eight most recent
genuine Libre readings strictly before the meal. Genuine readings are identified with
prepare_dataset.genuine_reading_mask, the same method used for premeal_libre_gl, so the
newest reading in every sequence is the corrected pre-meal glucose. Interpolated values and
readings at or after the meal are never used as inputs.

Only the participants of the requested splits have their raw files opened.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
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

HISTORY_LENGTH = 8
HISTORY_WINDOW_MINUTES = 120
MINUTE_NS = 60_000_000_000
NUTRITION_COLUMNS = ("calories", "carbs", "protein", "fat", "fiber")
TARGET_COLUMNS = tuple(f"libre_gl_t{minutes:03d}" for minutes in range(15, 241, 15))
GLUCOSE_COLUMNS = tuple(f"history_glucose_{step}" for step in range(1, HISTORY_LENGTH + 1))
MINUTES_COLUMNS = tuple(f"history_minutes_before_{step}" for step in range(1, HISTORY_LENGTH + 1))
DEFAULT_SPLITS = ("train", "validation")


def history_before_meal(
    times_ns: np.ndarray,
    values: np.ndarray,
    meal_ns: int,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Return the most recent genuine readings strictly before a meal, oldest first.

    `times_ns` and `values` must hold genuine readings only, sorted by time. Returns the
    glucose values, their minutes before the meal, and an empty reason when the history is
    complete; otherwise empty arrays and the exclusion reason.
    """
    empty = np.array([], dtype=float)
    position = int(np.searchsorted(times_ns, meal_ns, side="left"))
    if position < HISTORY_LENGTH:
        return empty, empty, "fewer_than_8_readings_before_meal"

    window = slice(position - HISTORY_LENGTH, position)
    minutes_before = (meal_ns - times_ns[window].astype(np.int64)) / MINUTE_NS
    if minutes_before[-1] > prepare_dataset.PREMEAL_MAX_MINUTES:
        return empty, empty, "no_reading_within_15_minutes"
    if minutes_before[0] > HISTORY_WINDOW_MINUTES:
        return empty, empty, "missing_reading_in_120_minute_window"

    return values[window].astype(float), minutes_before, ""


def participant_sequences(
    raw: pd.DataFrame,
    meals: pd.DataFrame,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Build sequences for one participant's meals from that participant's raw data only."""
    times_ns = raw[prepare_dataset.TIME].astype("int64").to_numpy()
    libre = raw["Libre GL"].to_numpy(dtype=float)
    finite = np.isfinite(libre)
    times_ns, libre = times_ns[finite], libre[finite]
    genuine = prepare_dataset.genuine_reading_mask(times_ns, libre)
    genuine_times, genuine_values = times_ns[genuine], libre[genuine]

    rows: list[dict[str, object]] = []
    exclusions: list[dict[str, object]] = []
    for _, meal in meals.iterrows():
        meal_ns = int(pd.Timestamp(meal["meal_timestamp"]).value)
        glucose, minutes_before, reason = history_before_meal(
            genuine_times, genuine_values, meal_ns
        )
        identity = {
            "participant_id": meal["participant_id"],
            "split": meal["split"],
            "meal_timestamp": meal["meal_timestamp"],
        }
        if reason:
            exclusions.append({**identity, "reason": reason})
            continue

        if glucose[-1] != meal["premeal_libre_gl"] or (
            minutes_before[-1] != meal["premeal_libre_gl_minutes_before"]
        ):
            raise ValueError(
                f"Newest history reading does not match premeal_libre_gl for participant "
                f"{meal['participant_id']} at {meal['meal_timestamp']}."
            )

        rows.append(
            {
                **identity,
                **dict(zip(GLUCOSE_COLUMNS, glucose.tolist(), strict=True)),
                **dict(zip(MINUTES_COLUMNS, minutes_before.tolist(), strict=True)),
                **{column: meal[column] for column in NUTRITION_COLUMNS},
                **{column: meal[column] for column in TARGET_COLUMNS},
            }
        )

    return rows, exclusions


def build_sequence_dataset(
    data_dir: Path,
    samples_dir: Path,
    output_dir: Path,
    splits: tuple[str, ...] = DEFAULT_SPLITS,
    split_manifest: Path | None = None,
    overwrite: bool = False,
) -> dict[str, object]:
    """Write cgmacros_sequence_<split>.csv files and an exclusion report."""
    manifest_path = split_manifest or prepare_dataset.DEFAULT_MANIFEST
    assignment: dict[str, str] = prepare_dataset.load_split_manifest(manifest_path)

    outputs = [output_dir / f"cgmacros_sequence_{split}.csv" for split in splits]
    outputs += [output_dir / "sequence_exclusions.csv", output_dir / "sequence_summary.json"]
    existing = [path.name for path in outputs if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(f"{output_dir} already contains {existing}. Use --overwrite.")

    rows: list[dict[str, object]] = []
    exclusions: list[dict[str, object]] = []
    for split in splits:
        meals = pd.read_csv(samples_dir / f"cgmacros_{split}.csv", dtype={"participant_id": str})
        meals["participant_id"] = meals["participant_id"].map(
            prepare_dataset.normalize_participant_id
        )
        wrong = sorted(
            pid for pid in meals["participant_id"].unique() if assignment.get(pid) != split
        )
        if wrong or (meals["split"] != split).any():
            raise ValueError(f"cgmacros_{split}.csv has participants not assigned to {split}.")

        for participant_id, participant_meals in meals.groupby("participant_id"):
            path = data_dir / f"CGMacros-{participant_id}" / f"CGMacros-{participant_id}.csv"
            raw = prepare_dataset.load_participant(path)
            participant_rows, participant_exclusions = participant_sequences(raw, participant_meals)
            rows.extend(participant_rows)
            exclusions.extend(participant_exclusions)

    output_dir.mkdir(parents=True, exist_ok=True)
    sequences = pd.DataFrame(rows)
    excluded = pd.DataFrame(
        exclusions, columns=["participant_id", "split", "meal_timestamp", "reason"]
    )
    for split in splits:
        sequences.loc[sequences["split"] == split].to_csv(
            output_dir / f"cgmacros_sequence_{split}.csv", index=False
        )
    excluded.to_csv(output_dir / "sequence_exclusions.csv", index=False)

    summary: dict[str, object] = {
        "samples_directory": str(samples_dir.resolve()),
        "split_manifest": str(manifest_path.resolve()),
        "splits": list(splits),
        "history_length": HISTORY_LENGTH,
        "history_window_minutes": HISTORY_WINDOW_MINUTES,
        "sequences_by_split": {
            split: {
                "meals": int((sequences["split"] == split).sum()),
                "participants": int(
                    sequences.loc[sequences["split"] == split, "participant_id"].nunique()
                ),
            }
            for split in splits
        },
        "excluded_by_reason": excluded["reason"].value_counts().to_dict(),
        "notes": [
            "history_*_1 is the oldest reading and history_*_8 the newest.",
            "All readings are genuine Libre readings strictly before the meal.",
            "history_glucose_8 equals premeal_libre_gl from the corrected dataset.",
        ],
    }
    (output_dir / "sequence_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--samples-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--splits", nargs="+", default=list(DEFAULT_SPLITS))
    parser.add_argument("--split-manifest", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    summary = build_sequence_dataset(
        args.data_dir,
        args.samples_dir,
        args.output_dir,
        tuple(args.splits),
        args.split_manifest,
        args.overwrite,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
