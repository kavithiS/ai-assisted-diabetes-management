"""Meal history and food search endpoints on in-memory SQLite. All foods are TEST FIXTURES."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

import c1_food_nutrition.db.models  # noqa: F401
from c1_food_nutrition.db.base import Base
from c1_food_nutrition.db.repositories.food_repository import FoodRepository
from c1_food_nutrition.db.session import create_session_factory

ClientFactory = Callable[..., TestClient]


@pytest.fixture
def api(make_client: ClientFactory) -> TestClient:
    client = make_client(database_url="sqlite://")
    engine = client.app.state.engine  # type: ignore[attr-defined]
    Base.metadata.create_all(engine)
    with create_session_factory(engine)() as session:
        foods = FoodRepository(session)
        source = foods.get_or_create_source("FIXTURE_SOURCE", "Test fixture source")
        foods.add_food(
            source,
            source_food_id="F1",
            name="Fixture rice",
            nutrients_per_100g={"energy_kcal": 100.0, "carbohydrate_g": 20.0},
        )
        foods.add_food(
            source,
            source_food_id="F2",
            name="Fixture dhal curry",
            nutrients_per_100g={"energy_kcal": 50.0, "carbohydrate_g": 5.0},
        )
        session.commit()
    return client


def food_id(api: TestClient, text: str) -> int:
    found = api.get("/v1/foods", params={"q": text}).json()["foods"]
    assert len(found) == 1
    return int(found[0]["id"])


def log(api: TestClient, **body: Any) -> dict[str, Any]:
    response = api.post("/v1/meals", json=body)
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_search_finds_foods_with_per_100g_values(api: TestClient) -> None:
    foods = api.get("/v1/foods", params={"q": "RICE"}).json()["foods"]
    assert [f["name"] for f in foods] == ["Fixture rice"]
    assert foods[0]["source"] == "FIXTURE_SOURCE"
    assert foods[0]["per_100g"]["energy_kcal"] == 100.0
    assert foods[0]["per_100g"]["protein_g"] is None  # unknown, never 0
    assert api.get("/v1/foods", params={"q": "zzzz"}).json() == {"foods": []}


def test_search_treats_percent_as_text(api: TestClient) -> None:
    assert api.get("/v1/foods", params={"q": "%%"}).json() == {"foods": []}


def test_search_needs_two_characters(api: TestClient) -> None:
    assert api.get("/v1/foods", params={"q": "a"}).status_code == 422


def test_log_meal_scales_stored_food_and_sums_totals(api: TestClient) -> None:
    rice, dhal = food_id(api, "rice"), food_id(api, "dhal")
    meal = log(
        api,
        meal_type="lunch",
        eaten_at="2026-10-16T06:30:00+00:00",
        items=[{"food_id": rice, "grams": 150}, {"food_id": dhal, "grams": 100}],
    )
    assert meal["meal_type"] == "lunch"
    assert [i["name"] for i in meal["items"]] == ["Fixture rice", "Fixture dhal curry"]
    assert meal["items"][0]["nutrients"]["energy_kcal"] == 150.0
    assert meal["totals"]["energy_kcal"] == 200.0
    assert meal["totals"]["carbohydrate_g"] == 35.0
    assert meal["totals"]["protein_g"] is None
    assert "confidence" not in str(meal)


def test_free_entry_keeps_unknown_nutrients_null(api: TestClient) -> None:
    meal = log(
        api,
        items=[{"name": "Home-made sweet", "grams": 40, "nutrients": {"energy_kcal": 120.0}}],
    )
    assert meal["items"][0]["food_id"] is None
    assert meal["items"][0]["nutrients"]["energy_kcal"] == 120.0
    assert meal["items"][0]["nutrients"]["carbohydrate_g"] is None
    assert meal["totals"]["carbohydrate_g"] is None


def test_meal_defaults_to_now(api: TestClient) -> None:
    meal = log(api, items=[{"name": "Tea", "grams": 200}])
    eaten = datetime.fromisoformat(meal["eaten_at"])
    assert abs((datetime.now(UTC) - eaten).total_seconds()) < 60


def test_unknown_food_id_is_a_validation_error(api: TestClient) -> None:
    response = api.post("/v1/meals", json={"items": [{"food_id": 9999, "grams": 10}]})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["field"] == "items.0.food_id"


@pytest.mark.parametrize(
    "body",
    [
        {"items": []},
        {"items": [{"grams": 10}]},
        {"items": [{"name": "x", "grams": 0}]},
        {"items": [{"name": "x", "grams": 6000}]},
        {"items": [{"food_id": 1, "name": "x", "grams": 10}]},
        {"items": [{"name": "x", "grams": 10}], "meal_type": "brunch"},
        {"items": [{"name": "x", "grams": 10}], "eaten_at": "2026-10-16T06:30:00"},
        {"items": [{"name": "x", "grams": 10}], "patient_id": "p1"},
    ],
)
def test_bad_meals_are_rejected(api: TestClient, body: dict[str, Any]) -> None:
    response = api.post("/v1/meals", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_newest_first_with_paging(api: TestClient) -> None:
    for day in (14, 16, 15):
        log(api, eaten_at=f"2026-10-{day}T06:00:00+00:00", items=[{"name": "Tea", "grams": 100}])
    days = [m["eaten_at"][:10] for m in api.get("/v1/meals").json()["meals"]]
    assert days == ["2026-10-16", "2026-10-15", "2026-10-14"]
    page = api.get("/v1/meals", params={"limit": 1, "offset": 1}).json()["meals"]
    assert [m["eaten_at"][:10] for m in page] == ["2026-10-15"]


def test_get_and_delete_one_meal(api: TestClient) -> None:
    meal = log(api, items=[{"name": "Tea", "grams": 100}])
    url = f"/v1/meals/{meal['id']}"
    assert api.get(url).json()["id"] == meal["id"]
    assert api.delete(url).status_code == 204
    missing = api.get(url)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    assert api.delete(url).status_code == 404
    assert api.get("/v1/meals").json() == {"meals": []}


def test_daily_summary_uses_the_clients_time_zone(api: TestClient) -> None:
    # 21:00 UTC on the 15th is 02:30 on the 16th in Sri Lanka (UTC+5:30).
    log(
        api,
        eaten_at="2026-10-15T21:00:00+00:00",
        items=[{"name": "Late snack", "grams": 50, "nutrients": {"energy_kcal": 80.0}}],
    )
    log(
        api,
        eaten_at="2026-10-16T05:00:00+00:00",
        items=[{"name": "Lunch", "grams": 300, "nutrients": {"energy_kcal": 500.0}}],
    )
    local = api.get(
        "/v1/meals/summary", params={"day": "2026-10-16", "utc_offset_minutes": 330}
    ).json()
    assert local["meal_count"] == 2
    assert local["totals"]["energy_kcal"] == 580.0
    utc = api.get("/v1/meals/summary", params={"day": "2026-10-16"}).json()
    assert utc["meal_count"] == 1
    empty = api.get("/v1/meals/summary", params={"day": "2026-01-01"}).json()
    assert empty["meal_count"] == 0
    assert empty["totals"]["energy_kcal"] is None


def test_analyze_route_is_untouched(api: TestClient) -> None:
    response = api.get("/v1/meals/analyze")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
