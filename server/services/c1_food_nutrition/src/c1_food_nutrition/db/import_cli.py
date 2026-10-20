"""Import a food-composition source into the database.

Usage::

    uv run python -m c1_food_nutrition.db.import_cli \
        --source mri_sl --path data/c1/c1_foods_combined.csv

Re-running an import updates the stored foods instead of duplicating them.
"""

import argparse
import logging
import sys
from pathlib import Path

from c1_food_nutrition.config import get_settings
from c1_food_nutrition.core.logging import configure_logging
from c1_food_nutrition.db.importers.base import NutritionImporter
from c1_food_nutrition.db.importers.mri_sri_lanka import MriSriLankaImporter
from c1_food_nutrition.db.importers.usda_fdc import UsdaFdcImporter
from c1_food_nutrition.db.repositories.food_repository import FoodRepository
from c1_food_nutrition.db.session import create_session_factory, engine_from_settings
from c1_food_nutrition.services.nutrition import CompositionTableError

IMPORTERS: dict[str, type[NutritionImporter]] = {
    "mri_sl": MriSriLankaImporter,
    "usda_fdc": UsdaFdcImporter,
}

logger = logging.getLogger("import_nutrition")


def main(argv: list[str] | None = None) -> int:
    """Run the importer selected on the command line; returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--source", choices=sorted(IMPORTERS), required=True)
    parser.add_argument("--path", type=Path, required=True)
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level)
    session_factory = create_session_factory(engine_from_settings(settings))

    importer = IMPORTERS[args.source]()
    with session_factory() as session:
        try:
            count = importer.import_into(FoodRepository(session), args.path)
        except (CompositionTableError, OSError) as exc:
            logger.error("import failed", extra={"source": args.source, "reason": str(exc)})
            return 2
        session.commit()
    logger.info("import finished", extra={"source": args.source, "foods": count})
    return 0


if __name__ == "__main__":
    sys.exit(main())
