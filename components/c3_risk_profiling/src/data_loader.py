"""Step 1 of the pipeline: load the harmonised South Asian data and check it.

Run it on its own to inspect the data:
    python -m src.data_loader
"""

import pandas as pd

from .config import CFG, abs_path


def load_all() -> pd.DataFrame:
    """Both Bangladesh sources, as built by src.south_asia_dataset."""
    path = abs_path(CFG["south_asia"]["processed_file"])
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: python -m src.external_data, "
            "then python -m src.south_asia_dataset"
        )
    return pd.read_csv(path)


def load_development() -> pd.DataFrame:
    """The rows used to train and test the models (DiaBD)."""
    df = load_all()
    return df[df["source"] == CFG["dataset"]["development_source"]].reset_index(drop=True)


def inspect(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "by_source": df["source"].value_counts().to_dict(),
        "diabetes_rate_by_source": df.groupby("source")["target"].mean().round(4).to_dict(),
        "missing_percent": (df.isna().mean() * 100).round(1)[lambda s: s > 0].to_dict(),
    }


if __name__ == "__main__":
    import json

    print(f"Dataset: {CFG['dataset']['name']}")
    print(json.dumps(inspect(load_all()), indent=2))
    print("Bangladesh data, not Sri Lankan. Never describe it as Sri Lankan findings.")
