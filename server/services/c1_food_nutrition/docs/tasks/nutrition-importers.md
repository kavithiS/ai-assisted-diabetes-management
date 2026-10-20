# Implement the nutrition importers

**Goal:** the MRI Sri Lanka and USDA importers load real composition data into the `c1` database, so nutrition lookups stop being placeholders.

**Update (2026-10-16):** the service now reads nutrient values straight from the combined CSV (`CompositionTableLookup`, `NUTRITION_TABLE_PATH`), Sri Lankan and USDA rows only; see `CHANGELOG.md`. The importers below are still stubs and the database is not used for nutrition. Decide whether they are still wanted.

**State (2026-10-15):** both are stubs that raise `NotImplementedError`:
`db/importers/mri_sri_lanka.py` (`MriSriLankaImporter`) and `db/importers/usda_fdc.py` (`UsdaFdcImporter`). Both extend `NutritionImporter` in `db/importers/base.py`, which yields `ImportedFood` records (per 100 g; only nutrients the source reports). Run with `db/import_cli.py` (`--source mri_sl|usda_fdc --path <file>`). The lookup used by the API is `PlaceholderNutritionLookup` in `services/nutrition.py`.

## Before you start (decisions)

- Which file each importer reads. The repaired combined table `data/c1/c1_foods_combined.csv` (2,716 foods, gitignored) mixes the Sri Lankan table with 8 regional tables; `AGENTS.md` section 4 allows only the Sri Lankan table and USDA until the supervisors decide (`OPEN_ITEMS.md` A1).
- B12 and vitamin D stay blank until the publisher confirms them (A2).
- The source codes in the code are `MRI_SL_FCDB`, `USDA_FDC` and `MOCK` (`schemas/nutrition.py`); `SKILL.md` writes `SL_FCDB`. Follow the code until `SKILL.md` is fixed.

## Rules (from SKILL.md section 8 and AGENTS.md)

- Reject the corrupted export whose header is `food_100me`, with a clear error naming the file.
- Validate header, column count, units and number types; name the file and row on error.
- An unknown value stays null, never 0 and never an estimate.
- Running an importer twice gives the same table.
- `carbohydrate_g` in the combined table is available carbohydrate (fibre excluded). There is no sugars column.

## Steps

1. Write small labelled CSV fixtures in `tests/` (a good file, a `food_100me` header, a bad number, a missing column, an "na" value).
2. Implement `parse` for each importer against the fixtures.
3. Add a real lookup in `services/nutrition.py` that reads the database, and keep the placeholder for tests.
4. Run the import on the real file once and check counts against the source.

## Checks

`AGENTS.md` section 1 definition of done; tests run without a real database (SQLite or in-memory).

## Record

`CONTEXT.md` sections 3 and 8, `OPEN_ITEMS.md` section D, `CHANGELOG.md`.
