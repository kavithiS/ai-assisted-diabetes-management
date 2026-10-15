"""Meal history and food search endpoints (demo data only)."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Response, status

from c1_food_nutrition.api.deps import SessionDep
from c1_food_nutrition.schemas.common import ErrorResponse
from c1_food_nutrition.schemas.meal_history import (
    DailySummary,
    FoodList,
    MealCreate,
    MealList,
    MealOut,
)
from c1_food_nutrition.services.meal_history import MealHistoryService

router = APIRouter(prefix="/v1", tags=["meal history"])

MealId = Annotated[int, Path(ge=1, le=2_147_483_647)]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "NOT_FOUND."}
}


@router.get("/foods", summary="Search foods by name")
def search_foods(
    session: SessionDep,
    q: Annotated[str, Query(min_length=2, max_length=100, description="Part of a food name.")],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> FoodList:
    """Foods from the composition table whose name contains ``q``, with per-100 g values."""
    return MealHistoryService(session).search_foods(q, limit)


@router.post(
    "/meals",
    summary="Log a meal",
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse, "description": "VALIDATION_ERROR."}},
)
def log_meal(session: SessionDep, body: MealCreate) -> MealOut:
    """Store a meal made of stored foods (``food_id``) and/or free entries (``name``)."""
    meal = MealHistoryService(session).log_meal(body)
    session.commit()
    return meal


@router.get("/meals", summary="List logged meals, newest first")
def list_meals(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MealList:
    """Logged meals with their items and totals."""
    return MealHistoryService(session).list_meals(limit=limit, offset=offset)


@router.get("/meals/summary", summary="Intake summary for one day")
def daily_summary(
    session: SessionDep,
    day: Annotated[date, Query(description="Calendar day in the client's time zone.")],
    utc_offset_minutes: Annotated[
        int, Query(ge=-840, le=840, description="Client offset from UTC, e.g. 330 for Sri Lanka.")
    ] = 0,
) -> DailySummary:
    """Totals for one day. A total is ``null`` when any logged value for it is unknown."""
    return MealHistoryService(session).daily_summary(day, utc_offset_minutes)


@router.get("/meals/{meal_id:int}", summary="One logged meal", responses=_NOT_FOUND)
def get_meal(session: SessionDep, meal_id: MealId) -> MealOut:
    """A logged meal with its items."""
    return MealHistoryService(session).get_meal(meal_id)


@router.delete(
    "/meals/{meal_id:int}",
    summary="Delete a logged meal",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND,
)
def delete_meal(session: SessionDep, meal_id: MealId) -> Response:
    """Remove a meal and its items."""
    MealHistoryService(session).delete_meal(meal_id)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
