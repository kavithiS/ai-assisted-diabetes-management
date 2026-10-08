"""Importer stub for the MRI Sri Lanka Food Composition Database.

TODO(c1): implement ``parse``. It must reject the corrupted export whose header is
``food_100me`` (SKILL.md section 8), with a test using a small labelled fixture.
"""

from collections.abc import Iterator
from pathlib import Path

from c1_food_nutrition.db.importers.base import ImportedFood, NutritionImporter
from c1_food_nutrition.schemas.nutrition import NutritionSourceCode


class MriSriLankaImporter(NutritionImporter):
    """MRI Sri Lanka FCDB importer (not implemented yet).

    The distribution format has not been obtained yet; implement ``parse`` once the
    source files are available and versioned with DVC under ``data/external/``.
    """

    source_code = NutritionSourceCode.MRI_SL_FCDB
    source_name = "Medical Research Institute Sri Lanka Food Composition Database"

    def parse(self, path: Path) -> Iterator[ImportedFood]:
        """Not implemented: source format pending."""
        raise NotImplementedError(
            "MRI Sri Lanka FCDB import is not implemented yet: source format pending."
        )
