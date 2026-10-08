"""Nutrition schemas.

No nutrient values are defined in this module. Real values must come from the MRI Sri Lanka
Food Composition Database or USDA FoodData Central via ``importers/``.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat


class NutritionSourceCode(StrEnum):
    """Origin of a nutrient profile."""

    MRI_SL_FCDB = "MRI_SL_FCDB"  # Medical Research Institute Sri Lanka Food Composition DB
    USDA_FDC = "USDA_FDC"  # USDA FoodData Central
    MOCK = "MOCK"  # Synthetic placeholder; never real nutrition data


class NutrientProfile(BaseModel):
    """Nutrient amounts for a given quantity of food.

    ``None`` means "not available": either the source does not report the nutrient
    or it could not be computed. It never means zero.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    energy_kcal: NonNegativeFloat | None = Field(default=None, description="Energy (kcal).")
    carbohydrate_g: NonNegativeFloat | None = Field(
        default=None, description="Total carbohydrate (g)."
    )
    sugars_g: NonNegativeFloat | None = Field(default=None, description="Total sugars (g).")
    dietary_fiber_g: NonNegativeFloat | None = Field(default=None, description="Dietary fibre (g).")
    protein_g: NonNegativeFloat | None = Field(default=None, description="Protein (g).")
    fat_g: NonNegativeFloat | None = Field(default=None, description="Total fat (g).")
    sodium_mg: NonNegativeFloat | None = Field(default=None, description="Sodium (mg).")


#: Ordered names of the nutrient fields, shared by calculation code and the DB layer.
NUTRIENT_FIELDS: tuple[str, ...] = tuple(NutrientProfile.model_fields)


class NutritionSourceRef(BaseModel):
    """Which composition table entry a nutrient profile was derived from."""

    model_config = ConfigDict(frozen=True)

    source: NutritionSourceCode
    source_food_id: str | None = Field(
        default=None, description="Identifier of the food in the source database."
    )
