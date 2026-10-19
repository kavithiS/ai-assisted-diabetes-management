"""Diabetic Health Score (DHS, 0-100, higher is better) - TAF task 4, proposal 3.4.4.

Pure Python. Settings and the formula are in config/dhs.yaml; every weight is
PROVISIONAL (pending clinician review). The DHS is a communication score for
self-management, not a validated clinical index.

Inputs: the patient's answers, the model's estimated risk (0-1) and, for the adaptive
part, the previous DHS of the same device. Kidney disease, liver disease and medication
adherence are used here (and in recommendations) but never by the risk model.
"""

from functools import cache
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .config import SERVICE_ROOT

DHS_FILE = SERVICE_ROOT / "config" / "dhs.yaml"
NOTE = (
    "Provisional Diabetic Health Score: weights pending clinician review. "
    "A communication score, not a clinical index or a diagnosis."
)
BEHAVIOUR = ("physical_activity", "smoker", "medication_adherence", "weight_change_kg")
MARKERS = ("cholesterol_level", "kidney_disease", "liver_disease")
LABELS = {
    "physical_activity": "Physical activity",
    "smoker": "Smoking",
    "medication_adherence": "Medication adherence",
    "weight_change_kg": "Body-weight change (3 months)",
    "cholesterol_level": "Cholesterol",
    "kidney_disease": "Kidney condition",
    "liver_disease": "Liver condition",
}


@cache
def settings(path: Path = DHS_FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        loaded: dict[str, Any] = yaml.safe_load(f)
    return loaded


def _item_score(factor: str, value: Any, cfg: dict[str, Any]) -> float:
    if factor == "weight_change_kg":
        change = abs(float(value))
        limits = cfg["weight_change"]
        if change <= limits["stable_kg"]:
            return 1.0
        return 0.5 if change <= limits["moderate_kg"] else 0.0
    table = cfg["behaviour_items"].get(factor) or cfg["clinical_markers"][factor]
    return float(table[value])


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def compute(
    answers: dict[str, Any],
    risk_probability: float,
    previous: float | None = None,
    glycemic: float | None = None,
) -> dict[str, Any]:
    """DHS for one assessment. Unanswered items are left out and counted in U."""
    cfg = settings()
    weights = cfg["weights"]

    items = []
    for factor in (*BEHAVIOUR, *MARKERS):
        value = answers.get(factor)
        if value is None:
            continue
        items.append(
            {
                "factor": factor,
                "label": LABELS[factor],
                "value": value,
                "item_score": _item_score(factor, value, cfg),
                "group": "behaviour" if factor in BEHAVIOUR else "clinical marker",
            }
        )

    behaviour = _mean([i["item_score"] for i in items if i["group"] == "behaviour"])
    markers = _mean([i["item_score"] for i in items if i["group"] == "clinical marker"])
    share = cfg["stable"]["model_share"]
    model_part = 1.0 - risk_probability
    stable = model_part if markers is None else share * model_part + (1 - share) * markers
    uncertainty = 1 - len(items) / (len(BEHAVIOUR) + len(MARKERS))

    parts = [(weights["stable"], stable)]
    if behaviour is not None:
        parts.append((weights["behaviour"], behaviour))
    if glycemic is not None:
        parts.append((weights["glycemic"], glycemic))
    weighted = sum(w * s for w, s in parts) / sum(w for w, _ in parts)
    today = round(100 * min(max(weighted - weights["uncertainty"] * uncertainty, 0.0), 1.0), 1)

    alpha = cfg["smoothing_alpha"]
    score = today if previous is None else round(alpha * today + (1 - alpha) * previous, 1)
    return {
        "score": score,
        "today_score": today,
        "previous_score": previous,
        "components": {
            "stable": round(stable, 4),
            "behaviour": None if behaviour is None else round(behaviour, 4),
            "glycemic": glycemic,
            "uncertainty": round(uncertainty, 4),
        },
        "items": items,
        "provisional": True,
        "note": NOTE,
    }
