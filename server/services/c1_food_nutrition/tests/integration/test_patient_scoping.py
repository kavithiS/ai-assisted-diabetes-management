"""Every meal belongs to one patient (ADR 0006); the gateway tells C1 who is calling (ADR 0005)."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

import c1_food_nutrition.db.models  # noqa: F401
from c1_food_nutrition.db.base import Base

ClientFactory = Callable[..., TestClient]

# Same values as the defaults in conftest.py (test values, not secrets).
TEST_INTERNAL_TOKEN = "test-internal-token"
TEST_PATIENT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_PATIENT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

BODY: dict[str, Any] = {"items": [{"name": "Tea", "grams": 100}], "meal_type": "snack"}
OTHER = {"X-Internal-Token": TEST_INTERNAL_TOKEN, "X-Patient-Id": OTHER_PATIENT_ID}


@pytest.fixture
def api(make_client: ClientFactory) -> TestClient:
    client = make_client(database_url="sqlite://")
    Base.metadata.create_all(client.app.state.engine)  # type: ignore[attr-defined]
    return client


def save(api: TestClient, headers: dict[str, str] | None = None) -> int:
    response = api.post("/v1/meals", json=BODY, headers=headers)
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def test_a_patient_sees_only_their_own_meals(api: TestClient) -> None:
    mine = save(api)
    theirs = save(api, OTHER)

    assert [m["id"] for m in api.get("/v1/meals").json()["meals"]] == [mine]
    assert [m["id"] for m in api.get("/v1/meals", headers=OTHER).json()["meals"]] == [theirs]


def test_another_patients_meal_looks_like_it_does_not_exist(api: TestClient) -> None:
    mine = save(api)

    read = api.get(f"/v1/meals/{mine}", headers=OTHER)
    assert read.status_code == 404
    assert read.json()["error"]["code"] == "NOT_FOUND"

    assert api.delete(f"/v1/meals/{mine}", headers=OTHER).status_code == 404
    assert api.get(f"/v1/meals/{mine}").status_code == 200  # still there for its owner


def test_daily_summary_counts_only_the_callers_meals(api: TestClient) -> None:
    api.post("/v1/meals", json={**BODY, "eaten_at": "2026-10-16T06:00:00+00:00"})
    api.post("/v1/meals", json={**BODY, "eaten_at": "2026-10-16T07:00:00+00:00"}, headers=OTHER)

    mine = api.get("/v1/meals/summary", params={"day": "2026-10-16"}).json()
    theirs = api.get("/v1/meals/summary", params={"day": "2026-10-16"}, headers=OTHER).json()

    assert mine["meal_count"] == 1
    assert theirs["meal_count"] == 1
    assert mine["meals"][0]["id"] != theirs["meals"][0]["id"]


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Patient-Id": TEST_PATIENT_ID},
        {"X-Internal-Token": TEST_INTERNAL_TOKEN},
        {"X-Internal-Token": "wrong", "X-Patient-Id": TEST_PATIENT_ID},
        {"X-Internal-Token": TEST_INTERNAL_TOKEN, "X-Patient-Id": "p1"},
    ],
)
def test_requests_without_the_gateways_proof_are_rejected(
    make_client: ClientFactory, headers: dict[str, str]
) -> None:
    client = make_client(database_url="sqlite://")
    client.headers.clear()

    for method, url in (
        ("GET", "/v1/meals"),
        ("POST", "/v1/meals"),
        ("GET", "/v1/meals/1"),
        ("DELETE", "/v1/meals/1"),
        ("GET", "/v1/meals/summary?day=2026-10-16"),
        ("POST", "/v1/meals/analyze"),
    ):
        response = client.request(
            method, url, headers=headers, json=BODY if method == "POST" else None
        )
        assert response.status_code == 401, (method, url, response.text)
        assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_without_a_configured_token_nothing_is_accepted(make_client: ClientFactory) -> None:
    client = make_client(database_url="sqlite://", internal_token=None)

    assert client.get("/v1/meals").status_code == 401


def test_internal_delete_removes_only_that_patients_data(api: TestClient) -> None:
    save(api)
    save(api)
    theirs = save(api, OTHER)

    gone = api.delete(f"/internal/v1/patients/{TEST_PATIENT_ID}")
    assert gone.status_code == 204
    assert api.get("/v1/meals").json() == {"meals": []}
    assert [m["id"] for m in api.get("/v1/meals", headers=OTHER).json()["meals"]] == [theirs]

    again = api.delete(f"/internal/v1/patients/{TEST_PATIENT_ID}")  # idempotent
    assert again.status_code == 204


def test_internal_delete_needs_the_token_but_not_a_patient_header(api: TestClient) -> None:
    only_token = {"X-Internal-Token": TEST_INTERNAL_TOKEN}
    assert (
        api.delete(f"/internal/v1/patients/{TEST_PATIENT_ID}", headers=only_token).status_code
        == 204
    )

    api.headers.clear()
    assert api.delete(f"/internal/v1/patients/{TEST_PATIENT_ID}").status_code == 401


def test_food_search_does_not_need_a_patient(api: TestClient) -> None:
    api.headers.clear()

    assert api.get("/v1/foods", params={"q": "rice"}).status_code == 200
