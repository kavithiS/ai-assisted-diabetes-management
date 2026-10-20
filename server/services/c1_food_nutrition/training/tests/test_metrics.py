import numpy as np
import pytest
from c1_training.metrics import average_precision, mean_average_precision, micro_f1


def test_perfect_ranking_is_one() -> None:
    assert average_precision(np.array([0, 1, 1]), np.array([0.1, 0.8, 0.9])) == 1.0


def test_known_value() -> None:
    # Worked example from the scikit-learn documentation: 0.8333...
    ap = average_precision(np.array([0, 0, 1, 1]), np.array([0.1, 0.4, 0.35, 0.8]))
    assert ap == pytest.approx(5 / 6)


def test_ties_form_one_threshold() -> None:
    # All scores tied: one threshold with precision 2/4 at recall 1.
    assert average_precision(np.array([1, 0, 1, 0]), np.full(4, 0.5)) == pytest.approx(0.5)


def test_no_positive_is_an_error() -> None:
    with pytest.raises(ValueError, match="positive"):
        average_precision(np.array([0, 0]), np.array([0.1, 0.2]))


def test_map_skips_classes_without_positives() -> None:
    y = np.array([[1, 0], [0, 0], [1, 0]])
    p = np.array([[0.9, 0.1], [0.2, 0.9], [0.8, 0.3]])
    assert mean_average_precision(y, p) == 1.0
    assert mean_average_precision(np.zeros((2, 2)), p[:2]) == 0.0


def test_micro_f1() -> None:
    y = np.array([[1, 0], [1, 1]])
    pred = np.array([[1, 1], [0, 1]])  # tp 2, fp 1, fn 1
    assert micro_f1(y, pred) == pytest.approx(2 * 2 / (2 * 2 + 1 + 1))
    assert micro_f1(np.zeros((1, 2)), np.zeros((1, 2))) == 0.0


def test_matches_scikit_learn_on_random_data() -> None:
    sk = pytest.importorskip("sklearn.metrics")
    rng = np.random.default_rng(0)
    for _ in range(50):
        y = rng.integers(0, 2, size=40)
        y[0] = 1
        s = rng.integers(0, 6, size=40) / 5  # many ties
        assert average_precision(y, s) == pytest.approx(sk.average_precision_score(y, s))
    y2 = rng.integers(0, 2, size=(30, 5))
    p2 = rng.random((30, 5)) > 0.5
    assert micro_f1(y2, p2) == pytest.approx(sk.f1_score(y2, p2, average="micro"))
