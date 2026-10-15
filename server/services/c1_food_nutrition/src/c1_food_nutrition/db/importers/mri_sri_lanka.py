"""Importer for the MRI Sri Lanka Food Composition Database rows of the combined table."""

from c1_food_nutrition.db.importers.table import CompositionTableImporter
from c1_food_nutrition.schemas.nutrition import NutritionSourceCode


class MriSriLankaImporter(CompositionTableImporter):
    """Reads the ``Sri Lankan Food Composition Database`` rows (ids such as ``SL_9``)."""

    source_code = NutritionSourceCode.MRI_SL_FCDB
    source_name = "Medical Research Institute Sri Lanka Food Composition Database"
