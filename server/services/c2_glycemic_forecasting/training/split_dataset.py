"""Write C2 train/validation/test files from the fixed participant split.

Participants are never shuffled or reassigned here. Each sample's `split` column comes from
the manifest (cgmacros_participant_split.json) used by prepare_dataset.py.
"""

import argparse
from pathlib import Path

import pandas as pd

# Dataset locations
DESKTOP = Path.home() / "Desktop"
INPUT_FILE = DESKTOP / "CGMacros_C2_processed" / "cgmacros_meal_samples_clean.csv"
OUTPUT_DIR = DESKTOP / "CGMacros_C2_processed" / "splits"

SPLIT_NAMES = ("train", "validation", "test")


def partition_by_split(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Group samples by their manifest split, refusing unassigned or mixed participants."""
    for column in ("participant_id", "split"):
        if column not in df.columns:
            raise ValueError(
                f"Dataset must contain {column}. Re-run prepare_dataset.py to label each "
                "sample with its split from the participant manifest."
            )
        if df[column].isna().any():
            raise ValueError(f"Some rows have a missing {column}.")

    invalid = sorted(set(df["split"]) - set(SPLIT_NAMES))
    if invalid:
        unassigned = sorted(df.loc[~df["split"].isin(SPLIT_NAMES), "participant_id"].unique())
        raise ValueError(
            f"Invalid split labels {invalid} for participants {unassigned}. "
            "Add them to the participant manifest explicitly."
        )

    splits_per_participant = df.groupby("participant_id")["split"].nunique()
    mixed = sorted(splits_per_participant[splits_per_participant > 1].index)
    if mixed:
        raise ValueError(f"Participants appear in more than one split: {mixed}")

    return {name: df.loc[df["split"] == name].copy() for name in SPLIT_NAMES}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", type=Path, default=INPUT_FILE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.input_file.exists():
        raise FileNotFoundError(f"Dataset not found: {args.input_file}")

    df = pd.read_csv(args.input_file, dtype={"participant_id": str})
    splits = partition_by_split(df)

    outputs = {name: args.output_dir / f"cgmacros_{name}.csv" for name in SPLIT_NAMES}
    existing = [
        str(outputs[name])
        for name in SPLIT_NAMES
        if not splits[name].empty and outputs[name].exists()
    ]
    if existing and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite {existing}. Use --overwrite to replace them.")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for split_name, split_df in splits.items():
        print(f"\n{split_name.upper()}")
        print(f"Participants: {split_df['participant_id'].nunique()}")
        print(f"Meal samples: {len(split_df)}")

        if split_df.empty:
            print("No samples in this input; file not written.")
            continue

        split_df.to_csv(outputs[split_name], index=False)
        print(f"Saved to: {outputs[split_name]}")

    print("\nParticipant-level split taken from the fixed manifest.")
    print("No participant is shared between the three splits.")


if __name__ == "__main__":
    main()
