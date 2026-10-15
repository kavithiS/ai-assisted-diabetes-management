"""Data access for logged meals."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from c1_food_nutrition.db.models import Meal, MealItem


class MealRepository:
    """CRUD operations for ``Meal`` and ``MealItem`` rows. The caller owns the transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, meal: Meal, items: Sequence[MealItem]) -> Meal:
        """Insert a meal with its items."""
        meal.items = list(items)
        self._session.add(meal)
        self._session.flush()
        return meal

    def get(self, meal_id: int) -> Meal | None:
        """Return a meal with its items, if present."""
        return self._session.scalar(
            select(Meal).options(selectinload(Meal.items)).where(Meal.id == meal_id)
        )

    def list_recent(self, *, limit: int, offset: int) -> list[Meal]:
        """Newest meals first."""
        return list(
            self._session.scalars(
                select(Meal)
                .options(selectinload(Meal.items))
                .order_by(Meal.eaten_at.desc(), Meal.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )

    def between(self, start: datetime, end: datetime) -> list[Meal]:
        """Meals eaten in ``[start, end)``; both must be UTC."""
        return list(
            self._session.scalars(
                select(Meal)
                .options(selectinload(Meal.items))
                .where(Meal.eaten_at >= start, Meal.eaten_at < end)
                .order_by(Meal.eaten_at, Meal.id)
            )
        )

    def delete(self, meal: Meal) -> None:
        """Delete a meal and its items."""
        self._session.delete(meal)
        self._session.flush()
