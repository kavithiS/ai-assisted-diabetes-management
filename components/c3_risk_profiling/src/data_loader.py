"""Step 1 of the pipeline: load the raw CSV and run basic integrity checks.

Run it on its own to inspect the data:
    python -m src.data_loader
"""
import pandas as pd
from .config import CFG, abs_path


def load_raw() -> pd.DataFrame:
    path = abs_path(CFG["dataset"]["raw_file"])
    if not path.exists():
        raise FileNotFoundError(
            f"Raw data not found at {path}.\n"
            "Download it first - see data/README.md for the source and steps."
        )
    return pd.read_csv(path)


def inspect(df: pd.DataFrame) -> dict:
    """Return the facts you must be able to quote at PP1."""
    target = CFG["dataset"]["target_column"]
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "class_counts": df[target].value_counts().sort_index().to_dict(),
    }


if __name__ == "__main__":
    df = load_raw()
    for key, value in inspect(df).items():
        print(f"{key}: {value}")
