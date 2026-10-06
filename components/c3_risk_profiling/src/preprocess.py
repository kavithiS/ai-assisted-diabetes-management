"""Step 2: clean the data and split it, without leaking test information.

Leakage rule: every statistic learned from data (scaling means, imputation values)
is fitted on the TRAINING split only, then applied to the test split.

Run:
    python -m src.preprocess
"""
import pandas as pd
from sklearn.model_selection import train_test_split
from .config import CFG, abs_path
from .data_loader import load_raw


def binarise(y: pd.Series) -> pd.Series:
    """Collapse 0/1/2 into 0 = no diabetes, 1 = prediabetes or diabetes.

    Why: the prediabetes class is a very small share of the rows, so a 3-class
    model learns it poorly. PP1 uses the binary problem; PP2 revisits 3 classes
    with class weighting. Check the real share yourself with src.data_loader.
    """
    return (y > 0).astype(int)


def build_dataset():
    cfg = CFG
    df = load_raw()
    target = cfg["dataset"]["target_column"]

    if cfg["preprocess"]["drop_exact_duplicates"]:
        before = len(df)
        df = df.drop_duplicates()
        print(f"Dropped {before - len(df)} exact duplicate rows ({before} -> {len(df)})")

    y = df[target]
    if cfg["dataset"]["binarise_target"]:
        y = binarise(y)
    X = df.drop(columns=[target])

    # stratify keeps the class balance identical in both splits.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=cfg["preprocess"]["test_size"],
        random_state=cfg["preprocess"]["random_state"],
        stratify=y,
    )
    print(f"Train: {X_train.shape}  Test: {X_test.shape}")
    print(f"Positive rate - train {y_train.mean():.4f} | test {y_test.mean():.4f}")
    return X_train, X_test, y_train, y_test


def save_processed():
    X_train, X_test, y_train, y_test = build_dataset()
    out = abs_path("data/processed")
    out.mkdir(parents=True, exist_ok=True)
    X_train.assign(target=y_train).to_csv(out / "train.csv", index=False)
    X_test.assign(target=y_test).to_csv(out / "test.csv", index=False)
    print(f"Saved processed splits to {out}")


if __name__ == "__main__":
    save_processed()
