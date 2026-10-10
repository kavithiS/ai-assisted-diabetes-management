from pathlib import Path

import numpy as np
import pandas as pd

# Dataset locations
DESKTOP = Path.home() / "Desktop"
INPUT_FILE = DESKTOP / "CGMacros_C2_processed" / "cgmacros_meal_samples_clean.csv"
OUTPUT_DIR = DESKTOP / "CGMacros_C2_processed" / "splits"

RANDOM_SEED = 42


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    if "participant_id" not in df.columns:
        raise ValueError("Dataset must contain participant_id.")

    if df["participant_id"].isna().any():
        raise ValueError("Some rows have a missing participant_id.")

    participants = np.array(sorted(df["participant_id"].unique()))
    rng = np.random.default_rng(RANDOM_SEED)
    rng.shuffle(participants)

    # 45 participants -> 31 training, 7 validation, 7 test
    train_end = int(round(len(participants) * 0.70))
    validation_end = train_end + int(round(len(participants) * 0.15))

    train_ids = participants[:train_end]
    validation_ids = participants[train_end:validation_end]
    test_ids = participants[validation_end:]

    splits = {
        "train": train_ids,
        "validation": validation_ids,
        "test": test_ids,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    used_ids: set[str] = set()

    for split_name, participant_ids in splits.items():
        participant_set = set(participant_ids.tolist())

        if used_ids.intersection(participant_set):
            raise ValueError("A participant appears in more than one split.")

        used_ids.update(participant_set)

        split_df = df[df["participant_id"].isin(participant_set)].copy()
        output_file = OUTPUT_DIR / f"cgmacros_{split_name}.csv"
        split_df.to_csv(output_file, index=False)

        print(f"\n{split_name.upper()}")
        print(f"Participants: {len(participant_set)}")
        print(f"Meal samples: {len(split_df)}")
        print(f"Saved to: {output_file}")

    if used_ids != set(participants.tolist()):
        raise ValueError("Some participants were not assigned to a split.")

    print("\nParticipant-level split completed successfully.")
    print("No participant is shared between the three splits.")


if __name__ == "__main__":
    main()
