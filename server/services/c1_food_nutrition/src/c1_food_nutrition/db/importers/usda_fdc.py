"""Importer stub for USDA FoodData Central.

TODO(c1): implement ``parse`` for ``sri_lankan_food_converted.csv`` (SKILL.md section 8).
"""

from collections.abc import Iterator
from pathlib import Path

from c1_food_nutrition.db.importers.base import ImportedFood, NutritionImporter
from c1_food_nutrition.schemas.nutrition import NutritionSourceCode


class UsdaFdcImporter(NutritionImporter):
    """USDA FoodData Central importer (not implemented yet).

    Implement ``parse`` against a specific downloaded FDC release once one has been
    chosen and versioned with DVC under ``data/external/``.
    """

    source_code = NutritionSourceCode.USDA_FDC
    source_name = "USDA FoodData Central"

    def parse(self, path: Path) -> Iterator[ImportedFood]:
        """Not implemented: release and file format not selected yet."""
        raise NotImplementedError(
            "USDA FoodData Central import is not implemented yet: release not selected."
        )
