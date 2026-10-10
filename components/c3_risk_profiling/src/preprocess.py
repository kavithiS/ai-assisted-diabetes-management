"""Step 2: split the data without leaking test information.

Leakage rule: every statistic learned from data (imputation medians, synthetic
generator, calibration, risk-band cut-offs) is fitted on the TRAINING split only,
then applied to the test split.

Run:
    python -m src.preprocess
"""

from sklearn.model_selection import train_test_split

from .config import CFG
from .data_loader import load_development


def build_dataset():
    """Stratified split of the development data, all candidate features kept.

    Missing values are left in place here; each model step fills them with
    medians learned from its own training rows.
    """
    df = load_development()
    features = CFG["feature_sets"]["with_glucose"]  # superset of every feature set
    X, y = df[features], df["target"]
    # stratify keeps the class balance identical in both splits.
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=CFG["preprocess"]["test_size"],
        random_state=CFG["preprocess"]["random_state"],
        stratify=y,
    )
    return X_train, X_test, y_train, y_test


if __name__ == "__main__":
    X_train, X_test, y_train, y_test = build_dataset()
    print(f"Train: {X_train.shape}  Test: {X_test.shape}")
    print(f"Diabetes rate - train {y_train.mean():.4f} | test {y_test.mean():.4f}")
