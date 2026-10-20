"""Turns a model result into the risk band shown to the patient.

Kept apart from the models, so the mock and the trained model use the same rule.
"""

from c4_foot_monitoring.ml.interfaces import FootClassification
from c4_foot_monitoring.schemas import RiskBand


def risk_band_for(result: FootClassification, low_risk_min_normal_probability: float) -> RiskBand:
    """Ulcer → High; normal with a high score → Low; any other normal → Medium."""
    if result.label == "ulcer":
        return "High"
    if result.confidence >= low_risk_min_normal_probability:
        return "Low"
    return "Medium"
