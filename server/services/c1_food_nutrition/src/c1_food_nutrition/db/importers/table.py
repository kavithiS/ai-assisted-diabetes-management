"""Importer for the combined food-composition CSV (``data/c1/c1_foods_combined.csv``).

It reuses :class:`CompositionTableLookup`, so the same checks apply as when the table is
used in memory: the header is verified (a ``food_100me`` export is rejected), blank cells stay
unknown (never 0), values must be numbers of 0 or more, and only allowed sources are read.
"""

from collections.abc import Iterator
from pathlib import Path

from c1_food_nutrition.db.importers.base import ImportedFood, NutritionImporter
from c1_food_nutrition.schemas.nutrition import NUTRIENT_FIELDS
from c1_food_nutrition.services.nutrition import CompositionTableLookup


class CompositionTableImporter(NutritionImporter):
    """Imports the rows of one source from the combined table."""

    def parse(self, path: Path) -> Iterator[ImportedFood]:
        """Yield the table rows that belong to this importer's source."""
        lookup = CompositionTableLookup.from_csv(path)
        for food_id, profile, ref, name in lookup.items():
            if ref.source != self.source_code:
                continue
            values = profile.model_dump()
            yield ImportedFood(
                source_food_id=food_id,
                name=name,
                nutrients_per_100g={
                    nutrient: values[nutrient]
                    for nutrient in NUTRIENT_FIELDS
                    if values[nutrient] is not None
                },
            )
