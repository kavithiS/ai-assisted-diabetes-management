"""Data access for logged meals."""

import uuid
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

    def get(self, patient_id: uuid.UUID, meal_id: int) -> Meal | None:
        """Return the patient's meal with its items, if present (never another patient's)."""
        return self._session.scalar(
            select(Meal)
            .options(selectinload(Meal.items))
            .where(Meal.id == meal_id, Meal.patient_id == patient_id)
        )

    def list_recent(self, patient_id: uuid.UUID, *, limit: int, offset: int) -> list[Meal]:
        """The patient's newest meals first."""
        return list(
            self._session.scalars(
                select(Meal)
                .options(selectinload(Meal.items))
                .where(Meal.patient_id == patient_id)
                .order_by(Meal.eaten_at.desc(), Meal.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )

    def between(self, patient_id: uuid.UUID, start: datetime, end: datetime) -> list[Meal]:
        """The patient's meals eaten in ``[start, end)``; both must be UTC."""
        return list(
            self._session.scalars(
                select(Meal)
                .options(selectinload(Meal.items))
                .where(Meal.patient_id == patient_id, Meal.eaten_at >= start, Meal.eaten_at < end)
                .order_by(Meal.eaten_at, Meal.id)
            )
        )

    def delete(self, meal: Meal) -> None:
        """Delete a meal and its items."""
        self._session.delete(meal)
        self._session.flush()

    def delete_all_for(self, patient_id: uuid.UUID) -> int:
        """Delete every meal (and its items) of one patient; returns how many meals."""
        meals = list(self._session.scalars(select(Meal).where(Meal.patient_id == patient_id)))
        for meal in meals:
            self._session.delete(meal)
        self._session.flush()
        return len(meals)
