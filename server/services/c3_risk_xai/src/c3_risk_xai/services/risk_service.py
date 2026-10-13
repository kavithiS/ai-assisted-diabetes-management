"""C3 orchestration: the only layer that imports ml/.

It loads the model bundles once (at app start-up), runs Function 1 (predict) and
Function 2 (explain), and shapes their output into a `risk_assessment` response.
It never recomputes, rounds or rewords anything the model layer returned.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from c3_risk_xai.ml import explain, predict
from c3_risk_xai.ml.config import CFG
from c3_risk_xai.schemas import (
    DebugInfo,
    Explanation,
    ModelStatus,
    PatientRiskProfile,
    RiskAssessment,
)

logger = logging.getLogger(__name__)

MODELS_MISSING = "Risk models are not loaded. Run training/train.py to create them."


class ModelsNotLoadedError(RuntimeError):
    """Raised when an assessment is requested before the model bundles are loaded."""


@dataclass
class _ModelState:
    loaded: bool = False
    models: dict[str, str] = field(default_factory=dict)


_state = _ModelState()


def load_models() -> ModelStatus:
    """Load every feature-set bundle once. Missing files mean `model_loaded: false`."""
    predict.load_bundle.cache_clear()
    try:
        models = {fs: str(predict.load_bundle(fs)["model_name"]) for fs in CFG["feature_sets"]}
    except FileNotFoundError:
        _state.loaded, _state.models = False, {}
        logger.warning(MODELS_MISSING)
    else:
        _state.loaded, _state.models = True, models
        logger.info("C3 models loaded: %s", models)
    return model_status()


def model_status() -> ModelStatus:
    return ModelStatus(
        model_loaded=_state.loaded,
        models=dict(_state.models),
        detail=None if _state.loaded else MODELS_MISSING,
    )


def assess(profile: PatientRiskProfile, include_debug: bool = False) -> RiskAssessment:
    """Run Function 1 and Function 2 on one profile.

    The glucose / no-glucose model is chosen by the model layer from whether
    `glucose_mmol` is present. Raw probability and cut-offs are only added when
    `include_debug` is true (research mode).
    """
    if not _state.loaded:
        raise ModelsNotLoadedError(MODELS_MISSING)

    patient: dict[str, Any] = profile.model_dump(exclude={"schema_version"})
    result = explain.explain_patient(patient)
    prediction: dict[str, Any] = result["prediction"]
    status = prediction["status"]

    if status == "insufficient_data":
        return RiskAssessment(
            status=status,
            disclaimer=prediction["disclaimer"],
            missing_critical_fields=prediction["missing_critical_fields"],
        )
    if status == "invalid_input":
        return RiskAssessment(
            status=status,
            disclaimer=prediction["disclaimer"],
            problems=prediction["problems"],
        )

    debug = (
        DebugInfo(
            risk_probability=prediction["risk_probability"],
            risk_percent=prediction["risk_percent"],
            thresholds=prediction["thresholds"],
        )
        if include_debug
        else None
    )
    return RiskAssessment(
        status="ok",
        disclaimer=prediction["disclaimer"],
        risk_category=prediction["risk_category"],
        referral=prediction["referral"],
        feature_set=prediction["feature_set"],
        model_used=prediction["model_used"],
        model_version=prediction["model_version"],
        data_complete=prediction["data_complete"],
        imputed_fields=prediction["imputed_fields"],
        explanation=Explanation(
            shap=result["shap"],
            lime=result["lime"],
            lime_fidelity=result["lime_fidelity"],
            agreement=result["agreement"],
            explanation_quality=result["explanation_quality"],
            explanation_text=result["explanation_text"],
        ),
        debug=debug,
    )
