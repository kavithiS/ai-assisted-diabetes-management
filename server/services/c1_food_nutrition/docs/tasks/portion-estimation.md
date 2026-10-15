# Portion estimation

**Goal:** replace `MockPortionEstimator` (a fixed 100 g placeholder) with an estimate in grams per recognised food.

**State (2026-10-15):** not started. `PortionEstimator.estimate(image, food, reference_object)` in `ml/interfaces.py` returns a `PortionEstimate` (`grams`, `method`, `household_measure`, `confidence`). The response schema allows `method` values `mock`, `reference_object` and `model` (`PortionEstimationMethod` in `schemas/meal_analysis.py`). `SKILL.md` section 7 describes `reference_card`, `default_serving` and `user_edited`; this mismatch is open.

## Before you start (decisions)

- The `reference_object` format is still open with C4 (`OPEN_ITEMS.md` A3, ADR 0004).
- The method names: align the schema and `SKILL.md`. A contract change needs C2 and C3 to approve.
- The source of the grams-per-area factors and default serving sizes: each must come from a named source. Never guess.
- The evaluation set: SKILL.md names ECUSTFD, which uses a coin, not a card. Using it needs a licence check.
- Portion edits already happen in the app (`newGrams / oldGrams`), not in C1.

## Steps (outline from SKILL.md section 7)

1. Detect the card (ID-1, 85.60 × 53.98 mm) with OpenCV: edges, largest four-sided contour with the right aspect ratio, perspective correction.
2. Millimetres per pixel from the card.
3. Area of each food region (a box to start, a mask later), in cm².
4. Grams from area with a per-food factor from a named source.
5. No card: default serving from the nutrition data, with a warning.
6. Tests on generated images with a drawn card; no real meal photos.

## Checks

`AGENTS.md` section 1 definition of done. Evaluation: MAE and MAPE in grams on a named set.

## Record

`CONTEXT.md` section 3, `OPEN_ITEMS.md` section D, `CHANGELOG.md`, and `EXPERIMENTS.md` rows for any evaluation.
