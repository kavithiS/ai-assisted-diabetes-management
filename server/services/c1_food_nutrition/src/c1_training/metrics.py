"""Multi-label metrics in numpy, matching scikit-learn's definitions.

``average_precision`` follows ``sklearn.metrics.average_precision_score`` (step-wise, no
interpolation; tied scores form one threshold). ``micro_f1`` follows ``f1_score(...,
average="micro", zero_division=0)``.
"""

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.floating]


def average_precision(y_true: NDArray[np.generic], scores: FloatArray) -> float:
    """Average precision of one class. ``y_true`` is 0/1; it must contain a positive."""
    y = np.asarray(y_true, dtype=np.float64).ravel()
    s = np.asarray(scores, dtype=np.float64).ravel()
    if y.shape != s.shape:
        raise ValueError("y_true and scores must have the same length")
    if y.sum() <= 0:
        raise ValueError("average precision needs at least one positive")
    order = np.argsort(s, kind="mergesort")[::-1]
    s, y = s[order], y[order]
    last_of_tie = np.r_[np.flatnonzero(np.diff(s)), y.size - 1]
    tps = np.cumsum(y)[last_of_tie]
    fps = 1 + last_of_tie - tps
    precision = tps / (tps + fps)
    recall = tps / tps[-1]
    steps = np.diff(np.r_[0.0, recall])
    return float(np.sum(steps * precision))


def mean_average_precision(y_true: NDArray[np.generic], scores: FloatArray) -> float:
    """Mean of the per-class average precision over classes with at least one positive.

    Returns 0.0 when no class has a positive.
    """
    y = np.asarray(y_true)
    present = np.flatnonzero(y.sum(axis=0) > 0)
    if present.size == 0:
        return 0.0
    return float(np.mean([average_precision(y[:, j], scores[:, j]) for j in present]))


def micro_f1(y_true: NDArray[np.generic], y_pred: NDArray[np.generic]) -> float:
    """Micro-averaged F1 over all labels; 0.0 when there are no positives at all."""
    t = np.asarray(y_true).astype(bool)
    p = np.asarray(y_pred).astype(bool)
    tp = int((t & p).sum())
    fp = int((~t & p).sum())
    fn = int((t & ~p).sum())
    denominator = 2 * tp + fp + fn
    return 2 * tp / denominator if denominator else 0.0
