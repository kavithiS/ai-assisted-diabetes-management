"""Importer for the USDA FoodData Central rows of the combined table."""

from c1_food_nutrition.db.importers.table import CompositionTableImporter
from c1_food_nutrition.schemas.nutrition import NutritionSourceCode


class UsdaFdcImporter(CompositionTableImporter):
    """Reads the ``USDA FoodData Central, Foundation Foods`` rows."""

    source_code = NutritionSourceCode.USDA_FDC
    source_name = "USDA FoodData Central"
