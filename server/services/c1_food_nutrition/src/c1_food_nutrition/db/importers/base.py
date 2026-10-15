"""Interface for food-composition importers.

Concrete importers parse a source's distribution files into ``ImportedFood`` records.
Values must come verbatim from the source; importers never fill in or estimate values.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from c1_food_nutrition.db.repositories.food_repository import FoodRepository
from c1_food_nutrition.schemas.nutrition import NutritionSourceCode


@dataclass(frozen=True, slots=True)
class ImportedFood:
    """One food parsed from a source file.

    ``nutrients_per_100g`` holds only nutrients the source actually reports.
    """

    source_food_id: str
    name: str
    nutrients_per_100g: Mapping[str, float] = field(default_factory=dict)
    name_si: str | None = None
    name_ta: str | None = None
    category: str | None = None


class NutritionImporter(ABC):
    """Parses one food-composition source."""

    source_code: ClassVar[NutritionSourceCode]
    source_name: ClassVar[str]

    @abstractmethod
    def parse(self, path: Path) -> Iterator[ImportedFood]:
        """Yield foods parsed from the source file(s) at ``path``."""

    def import_into(self, repository: FoodRepository, path: Path) -> int:
        """Parse ``path`` and store every food; returns the number of foods stored.

        Foods already stored are updated, so running an import twice is safe.
        The caller owns the transaction (commit/rollback).
        """
        source = repository.get_or_create_source(self.source_code.value, self.source_name)
        count = 0
        for food in self.parse(path):
            repository.upsert_food(
                source,
                source_food_id=food.source_food_id,
                name=food.name,
                nutrients_per_100g=food.nutrients_per_100g,
                name_si=food.name_si,
                name_ta=food.name_ta,
                category=food.category,
            )
            count += 1
        return count
