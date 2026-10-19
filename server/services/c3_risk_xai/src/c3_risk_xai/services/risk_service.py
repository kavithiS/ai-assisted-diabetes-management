"""C3 orchestration: the only layer that imports ml/ and db/.

It loads the model bundles once (at app start-up), runs Function 1 (predict) and
Function 2 (explain), and shapes their output into a `risk_assessment` response.
It never recomputes, rounds or rewords anything the model layer returned.

Storage (FR13, FR15, FR16, NFR12) is best-effort: when a device pseudonym is sent the
assessment is saved in the c3 schema; if the database is down the answer is still
returned, with `saved: false`.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from c3_risk_xai.db.repository import (
    AssessmentStore,
    NewAssessment,
    SqlAssessmentStore,
    make_engine,
)
from c3_risk_xai.ml import dhs, explain, predict, recommend
from c3_risk_xai.ml.config import CFG
from c3_risk_xai.schemas import (
    DatabaseState,
    DebugInfo,
    DeletedRecords,
    Dhs,
    Explanation,
    History,
    HistoryItem,
    ModelStatus,
    PatientRiskProfile,
    Recommendation,
    RiskAssessment,
)

logger = logging.getLogger(__name__)

MODELS_MISSING = "Risk models are not loaded. Run training/train.py to create them."
# The v1 model only ever sees the fields it was trained on. Lifestyle answers (0.2) go
# to the DHS and the recommendations, never to the model.
MODEL_FIELDS = set(CFG["feature_sets"]["with_glucose"])


class ModelsNotLoadedError(RuntimeError):
    """Raised when an assessment is requested before the model bundles are loaded."""


class StorageUnavailableError(RuntimeError):
    """Raised by history/delete when the database cannot be used."""


@dataclass
class _ModelState:
    loaded: bool = False
    models: dict[str, str] = field(default_factory=dict)


@dataclass
class _Storage:
    store: AssessmentStore | None = None
    state: DatabaseState = "off"


_state = _ModelState()
_storage = _Storage()


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


def init_storage(enabled: bool, database_url: str) -> DatabaseState:
    """Connect once at start-up. Never raises: a missing database only disables saving."""
    if not enabled:
        use_store(None, "off")
        return _storage.state
    use_store(SqlAssessmentStore(make_engine(database_url)), "unreachable")
    state = _refresh_state()
    if state != "ok":
        logger.warning("C3 database %s: assessments will not be saved until it is.", state)
    return state


def use_store(store: AssessmentStore | None, state: DatabaseState = "ok") -> None:
    """Swap the storage (tests use the in-memory store)."""
    _storage.store, _storage.state = store, state


def _refresh_state() -> DatabaseState:
    """Re-check a database that was not usable (it may have been started since)."""
    if _storage.store is not None and _storage.state != "ok":
        try:
            _storage.state = "ok" if _storage.store.ping() else "not_set_up"
        except Exception:  # noqa: BLE001 - any driver error means "unreachable"
            _storage.state = "unreachable"
    return _storage.state


def _usable_store() -> AssessmentStore:
    if _storage.store is None or _refresh_state() != "ok":
        raise StorageUnavailableError(f"C3 database is {_storage.state}.")
    return _storage.store


def model_status() -> ModelStatus:
    return ModelStatus(
        model_loaded=_state.loaded,
        models=dict(_state.models),
        detail=None if _state.loaded else MODELS_MISSING,
        database=_refresh_state(),
    )


def _stored_explanation(answer: RiskAssessment) -> dict[str, Any] | None:
    if answer.explanation is None:
        return None
    explanation = answer.explanation.model_dump()
    # v1 factors all come from real data; synthetic-assumption factors only arrive with v2.
    for factor in [*explanation["shap"], *explanation["lime"]]:
        factor["evidence_level"] = "real_data"
    return explanation


def _save(device_id: str, profile: PatientRiskProfile, answer: RiskAssessment) -> bool:
    try:
        _usable_store().save(
            NewAssessment(
                device_id=device_id,
                schema_version=profile.schema_version,
                answers=profile.model_dump(exclude={"schema_version"}, exclude_none=True),
                status=answer.status,
                band=answer.risk_category,
                model_version=answer.model_version,
                model_used=answer.model_used,
                feature_set=answer.feature_set,
                explanation=_stored_explanation(answer),
                dhs=None if answer.dhs is None else answer.dhs.score,
                dhs_components=None if answer.dhs is None else answer.dhs.components.model_dump(),
            )
        )
    except Exception:  # noqa: BLE001 - saving is best-effort, never fails the answer
        if _storage.state == "ok":
            _storage.state = "unreachable"
        logger.warning("C3 assessment not saved (database %s).", _storage.state)
        return False
    return True


def assess(
    profile: PatientRiskProfile,
    include_debug: bool = False,
    device_id: str | None = None,
) -> RiskAssessment:
    """Run Function 1 and Function 2 on one profile; save it when a device is given.

    The raw probability and cut-offs are only added when `include_debug` is true
    (research mode). They are never stored.
    """
    previous = _previous_dhs(device_id) if device_id is not None else None
    answer = _assess(profile, include_debug, previous)
    # Saving switched off on purpose (C3_PERSISTENCE=false) is not a failure: no flag then.
    if device_id is not None and _storage.store is not None:
        answer.saved = _save(device_id, profile, answer)
    return answer


def _previous_dhs(device_id: str) -> float | None:
    """Last DHS of this device for the adaptive score; none if the database is down."""
    try:
        return _usable_store().last_dhs(device_id)
    except Exception:  # noqa: BLE001 - best-effort, like saving
        return None


def history(device_id: str, limit: int = 50) -> History:
    """FR13: this device's past assessments, newest first."""
    try:
        rows = _usable_store().history(device_id, limit)
    except StorageUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise StorageUnavailableError("C3 database error.") from exc
    return History(
        items=[
            HistoryItem.model_validate(
                {
                    "id": r.id,
                    "assessed_at": r.created_at,
                    "status": r.status,
                    "risk_category": r.band,
                    "model_version": r.model_version,
                    "schema_version": r.schema_version,
                    "dhs": r.dhs,
                }
            )
            for r in rows
        ]
    )


def delete_device_records(device_id: str) -> DeletedRecords:
    """FR16: remove this device's records; the audit log keeps the action and count."""
    try:
        count = _usable_store().delete_device(device_id)
    except StorageUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise StorageUnavailableError("C3 database error.") from exc
    return DeletedRecords(deleted_assessments=count)


def _assess(
    profile: PatientRiskProfile, include_debug: bool, previous_dhs: float | None = None
) -> RiskAssessment:
    if not _state.loaded:
        raise ModelsNotLoadedError(MODELS_MISSING)

    patient: dict[str, Any] = profile.model_dump(include=MODEL_FIELDS)
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

    answers: dict[str, Any] = profile.model_dump(exclude={"schema_version"}, exclude_none=True)
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
        dhs=Dhs.model_validate(
            dhs.compute(answers, prediction["risk_probability"], previous=previous_dhs)
        ),
        recommendations=[
            Recommendation.model_validate(item) for item in recommend.build(answers, result["shap"])
        ],
        debug=debug,
    )
