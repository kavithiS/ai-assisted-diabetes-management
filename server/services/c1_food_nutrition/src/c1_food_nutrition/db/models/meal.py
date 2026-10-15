"""Meal-history ORM models (demo data only: no patient data, no images, no model confidence).

Each ``MealItem`` stores a snapshot of the nutrients for the portion that was logged, so a
later change to the food table never rewrites history. A nutrient the source does not report
is NULL, never 0.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from c1_food_nutrition.db.base import Base
from c1_food_nutrition.schemas.meal_analysis import MealType

_MEAL_TYPES_SQL = ", ".join(f"'{m.value}'" for m in MealType)


class Meal(Base):
    """One logged meal."""

    __tablename__ = "meal"
    __table_args__ = (
        CheckConstraint(
            f"meal_type IS NULL OR meal_type IN ({_MEAL_TYPES_SQL})", name="meal_type_known"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    eaten_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    meal_type: Mapped[str | None] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["MealItem"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan", order_by="MealItem.id"
    )


class MealItem(Base):
    """One food in a meal, with the nutrients of the logged portion."""

    __tablename__ = "meal_item"
    __table_args__ = (CheckConstraint("grams > 0", name="grams_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meal.id", ondelete="CASCADE"))
    food_id: Mapped[int | None] = mapped_column(ForeignKey("food.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(255))
    grams: Mapped[float] = mapped_column(Float)
    energy_kcal: Mapped[float | None] = mapped_column(Float)
    carbohydrate_g: Mapped[float | None] = mapped_column(Float)
    sugars_g: Mapped[float | None] = mapped_column(Float)
    dietary_fiber_g: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    sodium_mg: Mapped[float | None] = mapped_column(Float)

    meal: Mapped[Meal] = relationship(back_populates="items")
