# Wire the trained model behind `FoodRecognizer`

**Goal:** `POST /v1/meals/analyze` returns foods recognised by the trained model instead of the mock, and each recognised class maps to a nutrition row.

**State (2026-10-15):** not started. `api/deps.py` (`get_meal_analysis_service`) builds `MealAnalysisService` with `MockFoodRecognizer`, `MockPortionEstimator` and `PlaceholderNutritionLookup`, so every response has `is_mock: true`.

## What the code expects

- `ml/interfaces.py`: `FoodRecognizer` has `model_name`, `model_version`, `is_mock` and `recognize(image) -> list[RecognizedFood]`. The image is a BGR `uint8` array (OpenCV order). `RecognizedFood` has `label`, `confidence`, `food_code`, `region`.
- `services/pipeline.py` looks up nutrition with `food.food_code`; no `food_code` means an empty nutrient profile.
- Recognition is synchronous; the pipeline notes that a real model should run in a worker thread.
- `confidence` reaches the response; the app must never show it to patients.

## Before you start (decisions)

- Which run's weights to ship (currently the best is the ImageNet start; see `CONTEXT.md` section 10).
- The decision threshold for "food present" (choose it on the **valid** set, never the test set).
- How the weights reach the service (path setting; weights never in git).
- PyTorch as a runtime dependency of the service: it is not one now, and adding it needs the owner's approval (see `move-training-into-repo.md`).

## Steps

1. Inference preprocessing must match training: RGB (convert from BGR), resize to 224 × 224, ImageNet mean and standard deviation (as `vtf` in `stage2_finetune_srilankan.py`). Keep it in `ml/`.
2. Implement a recogniser class in `ml/` that loads the checkpoint (`arch`, `state`, `classes`), runs a sigmoid per class and returns every class above the threshold.
3. Class to nutrition mapping: `_curation\class_map.csv` has concept ids, and the nutrition table links concepts to foods through `food_concepts.csv` and `food_metadata.csv` [UNVERIFIED: columns and locations not re-checked]. Write the mapping into a versioned file in the C1 folder.
4. Add a test that **every** model class maps to a nutrition row. A class with no mapping is a bug.
5. Choose the recogniser in `deps.py` through a setting, so tests keep the mock.
6. Tests with a tiny dummy model (no real weights, no GPU): output shape, threshold, label order, mapping.

## Checks

The full definition of done in `AGENTS.md` section 1, including manual API QA (JPEG, PNG, no image, wrong type, corrupt, oversized, each `meal_type`) and `GET /health` through the gateway.

## Record

`CONTEXT.md` sections 3 and 5, `OPEN_ITEMS.md` section D, `CHANGELOG.md`.
