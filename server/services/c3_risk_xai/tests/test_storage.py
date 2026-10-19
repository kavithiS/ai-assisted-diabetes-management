"""Storage tests (FR13 history, FR15 versions, FR16 deletion, NFR12 audit).

Unit and API tests use the in-memory store. The Postgres test runs only when the real
database is reachable and migrated; otherwise it is skipped with the reason.
"""

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from c3_risk_xai.db.repository import (
    InMemoryAssessmentStore,
    NewAssessment,
    SqlAssessmentStore,
    make_engine,
    sqlalchemy_url,
)
from c3_risk_xai.main import app
from c3_risk_xai.ml.predict import EXAMPLE_PATIENT
from c3_risk_xai.schemas import PatientRiskProfile
from c3_risk_xai.services import risk_service
from c3_risk_xai.settings import C3Settings

DEVICE = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
OTHER_DEVICE = "ffffffffffffffffffffffffffffffff"


@pytest.fixture
def memory_store(fake_models: Path) -> Iterator[InMemoryAssessmentStore]:
    assert risk_service.load_models().model_loaded
    store = InMemoryAssessmentStore()
    risk_service.use_store(store)
    yield store
    risk_service.use_store(None, "off")


@pytest.fixture
def api(memory_store: InMemoryAssessmentStore) -> Iterator[TestClient]:
    with TestClient(app) as client:
        risk_service.use_store(memory_store)  # the app start-up switched saving off
        yield client


def test_assessment_with_device_is_saved_with_versions(
    memory_store: InMemoryAssessmentStore,
) -> None:
    out = risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT), device_id=DEVICE)

    assert out.saved is True
    _, saved, _ = memory_store.rows[0]
    assert saved.device_id == DEVICE
    assert saved.schema_version == "0.2"  # FR15 (default when the client sends none)
    assert saved.model_version == out.model_version  # FR15
    assert saved.band == out.risk_category
    assert saved.explanation is not None
    assert {f["evidence_level"] for f in saved.explanation["shap"]} == {"real_data"}
    assert memory_store.audit == [(DEVICE, "assess", "ok")]  # NFR12: action, no answers


def test_no_device_means_nothing_is_saved(memory_store: InMemoryAssessmentStore) -> None:
    out = risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT))
    assert out.saved is None
    assert memory_store.rows == []


def test_database_down_still_answers_and_flags_not_saved(
    memory_store: InMemoryAssessmentStore,
) -> None:
    memory_store.available = False
    risk_service.use_store(memory_store, "unreachable")

    out = risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT), device_id=DEVICE)

    assert out.status == "ok"
    assert out.risk_category is not None
    assert out.saved is False
    assert risk_service.model_status().database == "unreachable"


def test_history_is_per_device_newest_first(memory_store: InMemoryAssessmentStore) -> None:
    risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT), device_id=DEVICE)
    risk_service.assess(PatientRiskProfile(age=50, bmi=30), device_id=DEVICE)  # insufficient
    risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT), device_id=OTHER_DEVICE)

    items = risk_service.history(DEVICE).items

    assert [i.status for i in items] == ["insufficient_data", "ok"]
    assert items[1].risk_category is not None


def test_delete_removes_only_that_device_and_is_audited(
    memory_store: InMemoryAssessmentStore,
) -> None:
    risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT), device_id=DEVICE)
    risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT), device_id=OTHER_DEVICE)

    assert risk_service.delete_device_records(DEVICE).deleted_assessments == 1
    assert risk_service.history(DEVICE).items == []
    assert len(risk_service.history(OTHER_DEVICE).items) == 1
    assert (DEVICE, "delete_device_records", "1") in memory_store.audit


@pytest.mark.slow
def test_api_saves_lists_and_deletes(api: TestClient) -> None:
    headers = {"X-Device-Id": DEVICE}

    first = api.post("/v1/risk/assess", json=EXAMPLE_PATIENT, headers=headers).json()
    history = api.get("/v1/risk/history", headers=headers).json()
    deleted = api.delete("/v1/risk/history", headers=headers).json()

    assert first["saved"] is True
    assert history["items"][0]["risk_category"] == first["risk_category"]
    assert deleted == {"deleted_assessments": 1}
    assert api.get("/v1/risk/history", headers=headers).json() == {"items": []}
    assert api.get("/v1/risk/status").json()["database"] == "ok"


def test_api_rejects_a_device_id_that_is_not_a_pseudonym(api: TestClient) -> None:
    bad = {"X-Device-Id": "Lochana Rajapaksha"}
    assert api.get("/v1/risk/history", headers=bad).status_code == 422
    assert api.get("/v1/risk/history").status_code == 422  # history needs a device


def test_api_history_is_503_when_the_database_is_down(
    api: TestClient, memory_store: InMemoryAssessmentStore
) -> None:
    memory_store.available = False
    risk_service.use_store(memory_store, "unreachable")
    response = api.get("/v1/risk/history", headers={"X-Device-Id": DEVICE})
    assert response.status_code == 503


def test_database_url_uses_the_psycopg_driver() -> None:
    assert sqlalchemy_url("postgresql://u@h:5433/db") == "postgresql+psycopg://u@h:5433/db"
    assert sqlalchemy_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"


def _real_store() -> SqlAssessmentStore:
    # DATABASE_URL from the environment / .env; never printed.
    store = SqlAssessmentStore(make_engine(C3Settings().database_url))
    try:
        ready = store.ping()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"No reachable Postgres for C3 ({type(exc).__name__}).")
    if not ready:
        pytest.skip("C3 tables missing: run alembic upgrade head.")
    return store


def test_postgres_round_trip_with_a_throwaway_device() -> None:
    store = _real_store()
    device = uuid.uuid4().hex  # a fresh pseudonym; removed again below
    try:
        store.save(
            NewAssessment(
                device_id=device,
                schema_version="0.1",
                answers={"age": 58.0},
                status="insufficient_data",
                band=None,
                model_version=None,
                model_used=None,
                feature_set=None,
                explanation=None,
            )
        )
        items = store.history(device)
        assert [i.status for i in items] == ["insufficient_data"]
        assert items[0].schema_version == "0.1"
    finally:
        assert store.delete_device(device) == 1
    assert store.history(device) == []
