"""Meal history logic: build meals from requests and turn stored rows into responses."""

from datetime import UTC, date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from c1_food_nutrition.core.errors import ErrorDetailItem, InvalidRequestError, NotFoundError
from c1_food_nutrition.db.models import Food, Meal, MealItem
from c1_food_nutrition.db.repositories.food_repository import FoodRepository
from c1_food_nutrition.db.repositories.meal_repository import MealRepository
from c1_food_nutrition.schemas.meal_analysis import MealType
from c1_food_nutrition.schemas.meal_history import (
    DailySummary,
    FoodList,
    FoodOut,
    MealCreate,
    MealItemOut,
    MealList,
    MealOut,
)
from c1_food_nutrition.schemas.nutrition import NUTRIENT_FIELDS, NutrientProfile
from c1_food_nutrition.services.nutrition import scale_profile, sum_profiles


def as_utc(moment: datetime) -> datetime:
    """UTC-aware ``moment``; a naive value (SQLite returns these) is taken to be UTC."""
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


def food_profile(food: Food) -> NutrientProfile:
    """Per-100 g profile of a stored food; unreported nutrients stay ``None``."""
    return NutrientProfile(**{n.nutrient: n.amount_per_100g for n in food.nutrients})


def food_to_out(food: Food) -> FoodOut:
    """Response form of a food."""
    return FoodOut(
        id=food.id,
        name=food.name,
        name_si=food.name_si,
        name_ta=food.name_ta,
        category=food.category,
        source=food.source.code,
        per_100g=food_profile(food),
    )


def _item_profile(item: MealItem) -> NutrientProfile:
    return NutrientProfile(**{name: getattr(item, name) for name in NUTRIENT_FIELDS})


def meal_to_out(meal: Meal) -> MealOut:
    """Response form of a meal, with totals."""
    items = [
        MealItemOut(
            id=i.id,
            food_id=i.food_id,
            name=i.name,
            grams=i.grams,
            nutrients=_item_profile(i),
        )
        for i in meal.items
    ]
    return MealOut(
        id=meal.id,
        eaten_at=as_utc(meal.eaten_at),
        meal_type=MealType(meal.meal_type) if meal.meal_type else None,
        note=meal.note,
        items=items,
        totals=sum_profiles(i.nutrients for i in items),
    )


class MealHistoryService:
    """Log, read and delete meals; search foods. The caller commits."""

    def __init__(self, session: Session, now: datetime | None = None) -> None:
        self._foods = FoodRepository(session)
        self._meals = MealRepository(session)
        self._now = now

    def _clock(self) -> datetime:
        return self._now or datetime.now(UTC)

    def log_meal(self, request: MealCreate) -> MealOut:
        """Store a meal. Nutrients of a stored food are scaled from its per-100 g values."""
        items: list[MealItem] = []
        for index, entry in enumerate(request.items):
            if entry.food_id is not None:
                food = self._foods.get_by_id(entry.food_id)
                if food is None:
                    raise InvalidRequestError(
                        "A food in the meal does not exist.",
                        [
                            ErrorDetailItem(
                                field=f"items.{index}.food_id",
                                issue=f"no food with id {entry.food_id}",
                            )
                        ],
                    )
                name, food_id = food.name, food.id
                portion = scale_profile(food_profile(food), entry.grams)
            else:
                assert entry.name is not None  # noqa: S101 - guaranteed by MealItemIn
                name, food_id = entry.name.strip(), None
                portion = entry.nutrients or NutrientProfile()
            items.append(
                MealItem(
                    food_id=food_id,
                    name=name,
                    grams=entry.grams,
                    **portion.model_dump(),
                )
            )
        now = self._clock()
        meal = Meal(
            eaten_at=as_utc(request.eaten_at or now),
            meal_type=request.meal_type.value if request.meal_type else None,
            note=request.note,
            created_at=now,
        )
        return meal_to_out(self._meals.add(meal, items))

    def get_meal(self, meal_id: int) -> MealOut:
        """One meal, or ``NotFoundError``."""
        meal = self._meals.get(meal_id)
        if meal is None:
            raise NotFoundError(f"No meal with id {meal_id}.")
        return meal_to_out(meal)

    def list_meals(self, *, limit: int, offset: int) -> MealList:
        """Newest meals first."""
        return MealList(
            meals=[meal_to_out(m) for m in self._meals.list_recent(limit=limit, offset=offset)]
        )

    def delete_meal(self, meal_id: int) -> None:
        """Delete a meal, or raise ``NotFoundError``."""
        meal = self._meals.get(meal_id)
        if meal is None:
            raise NotFoundError(f"No meal with id {meal_id}.")
        self._meals.delete(meal)

    def daily_summary(self, day: date, utc_offset_minutes: int = 0) -> DailySummary:
        """Meals and totals for ``day`` in the client's time zone (``utc_offset_minutes``)."""
        zone = timezone(timedelta(minutes=utc_offset_minutes))
        start = datetime(day.year, day.month, day.day, tzinfo=zone).astimezone(UTC)
        meals = [meal_to_out(m) for m in self._meals.between(start, start + timedelta(days=1))]
        return DailySummary(
            day=day,
            meal_count=len(meals),
            totals=sum_profiles(m.totals for m in meals) if meals else NutrientProfile(),
            meals=meals,
        )

    def search_foods(self, text: str, limit: int) -> FoodList:
        """Foods whose name contains ``text``."""
        return FoodList(foods=[food_to_out(f) for f in self._foods.search(text, limit=limit)])
