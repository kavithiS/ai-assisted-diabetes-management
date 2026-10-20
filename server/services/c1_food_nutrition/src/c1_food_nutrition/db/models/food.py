"""Food-composition ORM models.

The schema is source-agnostic so that MRI Sri Lanka FCDB and USDA FoodData Central rows can
coexist. No rows are created by the application; data enters only through ``importers/``.

TODO(c1): put these tables in the ``c1`` Postgres schema, and align them with the planned
``foods`` / ``label_map`` / ``meals`` / ``meal_items`` tables in SKILL.md section 8.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from c1_food_nutrition.db.base import Base
from c1_food_nutrition.schemas.nutrition import NUTRIENT_FIELDS

_NUTRIENT_NAMES_SQL = ", ".join(f"'{name}'" for name in NUTRIENT_FIELDS)


class NutritionSource(Base):
    """A food-composition database (e.g. MRI_SL_FCDB, USDA_FDC) and the imported release."""

    __tablename__ = "nutrition_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    release: Mapped[str | None] = mapped_column(String(64))
    citation: Mapped[str | None] = mapped_column(Text)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    foods: Mapped[list["Food"]] = relationship(back_populates="source")


class Food(Base):
    """A food entry as defined by its source database."""

    __tablename__ = "food"
    __table_args__ = (UniqueConstraint("source_id", "source_food_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("nutrition_source.id", ondelete="CASCADE"))
    source_food_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    name_si: Mapped[str | None] = mapped_column(String(255))  # Sinhala name, if provided
    name_ta: Mapped[str | None] = mapped_column(String(255))  # Tamil name, if provided
    category: Mapped[str | None] = mapped_column(String(128))

    source: Mapped[NutritionSource] = relationship(back_populates="foods")
    nutrients: Mapped[list["FoodNutrient"]] = relationship(
        back_populates="food", cascade="all, delete-orphan"
    )


class FoodNutrient(Base):
    """Amount of one nutrient per 100 g edible portion, as reported by the source."""

    __tablename__ = "food_nutrient"
    __table_args__ = (
        UniqueConstraint("food_id", "nutrient"),
        CheckConstraint("amount_per_100g >= 0", name="amount_non_negative"),
        CheckConstraint(f"nutrient IN ({_NUTRIENT_NAMES_SQL})", name="known_nutrient"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("food.id", ondelete="CASCADE"))
    nutrient: Mapped[str] = mapped_column(String(32))
    amount_per_100g: Mapped[float] = mapped_column(Float)

    food: Mapped[Food] = relationship(back_populates="nutrients")
