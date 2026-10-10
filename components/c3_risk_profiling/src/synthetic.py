"""Synthetic patient records from a Gaussian copula fitted on REAL training rows.

How it works, per class (so the label relationship is kept):
1. Turn every column into normal scores using its ranks.
2. Learn the correlation between those scores.
3. Sample new correlated normal scores and map them back through each column's
   real quantiles, so binary columns stay 0/1 and ranges stay realistic.

Rules (proposal section 3.2.3):
- The generator only ever sees the training split. The test set stays 100% real,
  so every reported metric is measured on real people.
- Synthetic rows are training augmentation, never evidence on their own.
"""

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata


class GaussianCopulaSynthesizer:
    def __init__(self, random_state: int = 0):
        self.rng = np.random.default_rng(random_state)
        self.classes = {}

    @staticmethod
    def _nearest_correlation(c: np.ndarray) -> np.ndarray:
        """Clip negative eigenvalues so the matrix is a valid correlation matrix."""
        vals, vecs = np.linalg.eigh(c)
        c = vecs @ np.diag(np.clip(vals, 1e-6, None)) @ vecs.T
        d = np.sqrt(np.diag(c))
        return c / np.outer(d, d)

    def fit(self, X: pd.DataFrame, y: pd.Series):
        """X must have no missing values (impute with training statistics first)."""
        self.columns = list(X.columns)
        for label in sorted(y.unique()):
            part = X[y == label].to_numpy(dtype=float)
            n = len(part)
            scores = norm.ppf(rankdata(part, axis=0) / (n + 1))
            corr = np.nan_to_num(np.corrcoef(scores, rowvar=False))  # constant column -> 0
            np.fill_diagonal(corr, 1.0)
            self.classes[label] = {
                "sorted": np.sort(part, axis=0),
                "corr": self._nearest_correlation(corr),
                "share": n / len(X),
            }
        return self

    def _sample_class(self, label, n: int) -> np.ndarray:
        c = self.classes[label]
        z = self.rng.multivariate_normal(np.zeros(len(self.columns)), c["corr"], size=n)
        u = norm.cdf(z)
        real = c["sorted"]
        # Inverse empirical CDF: always returns a value seen in real data.
        idx = np.minimum((u * len(real)).astype(int), len(real) - 1)
        return np.take_along_axis(real, idx, axis=0)

    def sample(self, n: int) -> tuple[pd.DataFrame, pd.Series]:
        """Draw n rows with the same class balance as the training data."""
        parts, labels = [], []
        for label, c in self.classes.items():
            k = int(round(n * c["share"]))
            parts.append(self._sample_class(label, k))
            labels.append(np.full(k, label))
        X = pd.DataFrame(np.vstack(parts), columns=self.columns)
        y = pd.Series(np.concatenate(labels), name="target")
        order = self.rng.permutation(len(X))
        return X.iloc[order].reset_index(drop=True), y.iloc[order].reset_index(drop=True)


def exact_copy_rate(real: pd.DataFrame, synthetic: pd.DataFrame) -> float:
    """Share of synthetic rows identical to a real training row (privacy check)."""
    real_rows = set(map(tuple, real.round(4).to_numpy()))
    hits = sum(tuple(row) in real_rows for row in synthetic.round(4).to_numpy())
    return hits / len(synthetic)
