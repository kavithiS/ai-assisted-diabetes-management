import json
import logging
import uuid
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from diacare_shared.db import make_engine, make_session_factory
from diacare_shared.errors import AppError, ErrorCode, ErrorDetail, install_exception_handlers
from diacare_shared.internal_auth import (
    INTERNAL_TOKEN_HEADER,
    PATIENT_ID_HEADER,
    make_internal_token_dependency,
    make_patient_id_dependency,
)
from diacare_shared.logging import JsonFormatter
from diacare_shared.request_context import (
    BodySizeLimitMiddleware,
    RequestContextMiddleware,
    get_request_id,
)

TOKEN = "unit-test-internal-token"
PATIENT = uuid.UUID("11111111-1111-4111-8111-111111111111")


class Item(BaseModel):
    name: str


def build_app() -> FastAPI:
    app = FastAPI()
    install_exception_handlers(app)
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=100)
    app.add_middleware(RequestContextMiddleware)

    patient = make_patient_id_dependency(lambda request: TOKEN)
    internal = make_internal_token_dependency(lambda request: TOKEN)

    @app.get("/who")
    def who(patient_id: Annotated[uuid.UUID, Depends(patient)]) -> dict[str, str]:
        return {"patient_id": str(patient_id)}

    @app.delete("/internal/x")
    def internal_only(_: Annotated[None, Depends(internal)]) -> dict[str, bool]:
        return {"ok": True}

    @app.get("/app-error")
    def app_error() -> None:
        raise AppError(409, "CUSTOM_CODE", "Nope.", details=[ErrorDetail("bad", field="f")])

    @app.get("/http-error")
    def http_error() -> None:
        raise HTTPException(status_code=501, detail="Not implemented")

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    @app.get("/request-id")
    def request_id() -> dict[str, str | None]:
        return {"id": get_request_id()}

    @app.post("/items")
    def items(item: Item) -> Item:
        return item

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app(), raise_server_exceptions=False)


def headers(token: str | None = TOKEN, patient: str | None = str(PATIENT)) -> dict[str, str]:
    result: dict[str, str] = {}
    if token is not None:
        result[INTERNAL_TOKEN_HEADER] = token
    if patient is not None:
        result[PATIENT_ID_HEADER] = patient
    return result


def test_error_envelope_for_app_error(client: TestClient) -> None:
    response = client.get("/app-error")

    assert response.status_code == 409
    body = response.json()
    assert body["error"] == {
        "code": "CUSTOM_CODE",
        "message": "Nope.",
        "details": [{"field": "f", "issue": "bad"}],
    }
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_http_exception_and_validation_use_the_envelope(client: TestClient) -> None:
    http_error = client.get("/http-error")
    assert http_error.status_code == 501
    assert http_error.json()["error"]["code"] == ErrorCode.NOT_IMPLEMENTED

    missing = client.get("/no-such-path")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == ErrorCode.NOT_FOUND

    invalid = client.post("/items", json={})
    assert invalid.status_code == 422
    error = invalid.json()["error"]
    assert error["code"] == ErrorCode.VALIDATION_ERROR
    assert error["details"][0]["field"] == "name"


def test_unhandled_error_hides_the_cause(client: TestClient) -> None:
    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == ErrorCode.INTERNAL_ERROR
    assert "secret" not in response.text


def test_request_id_is_reused_when_safe_and_replaced_when_not(client: TestClient) -> None:
    reused = client.get("/request-id", headers={"X-Request-ID": "abc-123"})
    assert reused.headers["X-Request-ID"] == "abc-123"
    assert reused.json() == {"id": "abc-123"}

    replaced = client.get("/request-id", headers={"X-Request-ID": "bad id with spaces"})
    assert replaced.headers["X-Request-ID"] != "bad id with spaces"
    assert len(replaced.headers["X-Request-ID"]) == 32


def test_body_over_the_limit_gets_413(client: TestClient) -> None:
    response = client.post("/items", content=b"x" * 500, headers={"content-type": "text/plain"})

    assert response.status_code == 413
    assert response.json()["error"]["code"] == ErrorCode.PAYLOAD_TOO_LARGE


def test_patient_id_accepted_with_the_right_token(client: TestClient) -> None:
    response = client.get("/who", headers=headers())

    assert response.status_code == 200
    assert response.json() == {"patient_id": str(PATIENT)}


@pytest.mark.parametrize(
    "bad",
    [
        headers(token=None),
        headers(token="wrong-token"),
        headers(patient=None),
        headers(patient="not-a-uuid"),
    ],
)
def test_patient_id_rejected_without_token_or_with_bad_values(
    client: TestClient, bad: dict[str, str]
) -> None:
    response = client.get("/who", headers=bad)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.UNAUTHORIZED


def test_internal_endpoint_needs_only_the_token(client: TestClient) -> None:
    assert client.delete("/internal/x", headers=headers(patient=None)).status_code == 200
    assert client.delete("/internal/x", headers=headers(token="wrong")).status_code == 401


def test_service_without_a_configured_token_rejects_everything() -> None:
    app = FastAPI()
    install_exception_handlers(app)
    dependency = make_internal_token_dependency(lambda request: None)

    @app.get("/x")
    def route(_: Annotated[None, Depends(dependency)]) -> dict[str, bool]:
        return {"ok": True}

    assert TestClient(app).get("/x", headers=headers()).status_code == 401


def test_json_formatter_includes_request_id_and_extras() -> None:
    record = logging.LogRecord("name", logging.INFO, "f.py", 1, "hello %s", ("world",), None)
    record.status_code = 200

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["status_code"] == 200
    assert "request_id" in payload


def test_make_engine_maps_the_schema_away_on_sqlite() -> None:
    from sqlalchemy import Column, Integer, MetaData, Table, select

    metadata = MetaData(schema="core")
    table = Table("thing", metadata, Column("id", Integer, primary_key=True))
    engine = make_engine("sqlite://", "core")
    metadata.create_all(engine)

    with make_session_factory(engine)() as session:
        session.execute(table.insert().values(id=1))
        assert session.execute(select(table.c.id)).scalar_one() == 1
