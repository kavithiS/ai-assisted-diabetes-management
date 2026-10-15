"""Map each model class to a food concept and, where there is an honest match, a table entry.

``data/class_concepts.csv`` was made from the image-curation class map (``keep`` and ``merge``
rows with a concept) and then reviewed class by class against the Sri Lankan food composition
table (2026-10-16). Per class:

* ``concept_id``: the broad food concept;
* ``food_id`` and ``match``: the table entry whose nutrient values are used. ``match`` is
  ``exact`` (same dish), ``close`` (same dish, a variety may differ), ``partial`` (the nearest
  entry, noticeably different) or ``none`` (no honest match: the nutrients stay unknown);
* ``note``: what to know about the match.

A class that has not been reviewed (empty ``match``) cannot be used by a model: loading fails
instead of silently returning a food with no values. Nutrient values are never guessed.
"""

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "data" / "class_concepts.csv"
MATCH_LEVELS = ("exact", "close", "partial", "none")


class UnmappedClassError(ValueError):
    """A model class has no entry in the class map."""


class UnreviewedClassError(ValueError):
    """A model class is in the class map but its food match has not been reviewed."""


@dataclass(frozen=True, slots=True)
class ClassFood:
    """What a class is matched to in the composition table."""

    concept_id: str
    food_id: str | None
    match: str
    note: str

    @property
    def is_approximate(self) -> bool:
        """True when the table entry is only close or partial."""
        return self.food_id is not None and self.match in ("close", "partial")


def load_class_foods(path: Path = DEFAULT_PATH) -> dict[str, ClassFood]:
    """Read ``{class: ClassFood}``; rejects duplicates, empty concepts and bad match levels."""
    table: dict[str, ClassFood] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            name, concept = row["class"].strip(), row["concept_id"].strip()
            food = (row.get("food_id") or "").strip() or None
            match = (row.get("match") or "").strip()
            if not name or not concept:
                raise ValueError(f"{path}: empty class or concept id in row {row!r}")
            if name in table:
                raise ValueError(f"{path}: class {name!r} listed twice")
            if match and match not in MATCH_LEVELS:
                raise ValueError(f"{path}: class {name!r} has unknown match {match!r}")
            if (food is None) != (match in ("", "none")):
                raise ValueError(f"{path}: class {name!r} needs a food_id exactly when it matches")
            table[name] = ClassFood(concept, food, match, (row.get("note") or "").strip())
    return table


def load_class_concepts(path: Path = DEFAULT_PATH) -> dict[str, str]:
    """``{class: concept_id}`` for every class in the file."""
    return {name: entry.concept_id for name, entry in load_class_foods(path).items()}


def concepts_for(classes: Iterable[str], mapping: dict[str, str]) -> dict[str, str]:
    """``{class: concept_id}`` for ``classes``; raises if any class is unmapped."""
    wanted = list(classes)
    missing = sorted(c for c in wanted if c not in mapping)
    if missing:
        raise UnmappedClassError(f"model classes without a concept id: {missing}")
    return {c: mapping[c] for c in wanted}


def foods_for(classes: Iterable[str], table: dict[str, ClassFood]) -> dict[str, ClassFood]:
    """``{class: ClassFood}`` for ``classes``; raises if a class is unmapped or unreviewed."""
    wanted = list(classes)
    missing = sorted(c for c in wanted if c not in table)
    if missing:
        raise UnmappedClassError(f"model classes without an entry in the class map: {missing}")
    unreviewed = sorted(c for c in wanted if not table[c].match)
    if unreviewed:
        raise UnreviewedClassError(
            f"model classes whose food match has not been reviewed: {unreviewed}"
        )
    return {c: table[c] for c in wanted}
