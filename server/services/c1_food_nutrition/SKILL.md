# SKILL.md — C1 Technical Reference

How Component 1 (Food Recognition & Nutritional Analysis) is built. Read `AGENTS.md` first for the rules; this file covers the technical detail.

---

## 1. Pipeline

```
Meal image (+ meal type, capture time, optional reference card)
  → 1. Validate & preprocess      (Pillow/OpenCV)
  → 2. Recognise foods            (multi-label CNN, PyTorch + timm)
  → 3. Estimate portions          (reference-card calibration → grams)
  → 4. Look up nutrition          (Sri Lankan composition data → USDA fallback)
  → 5. Calculate per-food and meal totals
  → 6. Return meal_nutrition JSON (to C2, C3 and the app, through the gateway)
```

Each step is a separate module, so each can be built and tested on its own and replaced by a stub while it isn't ready.

---

## 2. Tech stack (C1 only)

| Need | Use |
|---|---|
| API | FastAPI, Pydantic v2, Uvicorn, `python-multipart` (file uploads) |
| Images | Pillow (decode and validate), OpenCV (card detection, segmentation), Albumentations (training augmentation) |
| Deep learning | PyTorch, torchvision, `timm` (EfficientNetV2 as primary, MobileNetV3 as the lightweight comparison) |
| Database | PostgreSQL 16 (`c1` schema), SQLAlchemy 2, Alembic, `psycopg[binary]` |
| Experiments | MLflow (local, SQLite backend) |
| Data versioning | DVC (data lives in `data/c1/`) |
| Quality | Ruff, mypy, pytest, FastAPI `TestClient` |

Add packages with `uv add --package c1-food-nutrition <name>`. Use only the libraries a phase needs.

---

## 3. Folder layout

```
server/services/c1_food_nutrition/
├── src/c1_food_nutrition/
│   ├── main.py              # FastAPI app, /health, router include
│   ├── config.py            # settings (env vars), size limits, model path
│   ├── schemas.py           # Pydantic models = the meal_nutrition contract
│   ├── api/routes.py        # /v1/meals/* endpoints (thin: validate → call service)
│   ├── services/
│   │   ├── image_validation.py
│   │   ├── recognition.py   # wraps ml/; mock until the model is ready
│   │   ├── portion.py       # reference card → grams
│   │   ├── nutrition.py     # lookup + scaling + totals
│   │   └── pipeline.py      # runs steps 1–6 in order
│   ├── ml/                  # model definition, loading, inference (no training here)
│   └── db/                  # SQLAlchemy models, importer, repository
├── training/                # training & evaluation scripts (write to MLflow)
├── notebooks/               # exploration only; nothing the API depends on
├── tests/                   # unit/ and integration/ tests, plus fixtures/
├── docs/                    # C1's own notes and design docs
├── AGENTS.md  SKILL.md  CLAUDE.md  README.md  pyproject.toml
```

Keep routes thin: the route validates input and calls `pipeline.py`, and all the logic lives in `services/`.

---

## 4. API

### `GET /health`
Returns `{"status": "ok", "service": "c1_food_nutrition"}`. Never remove or change it; the gateway depends on it.

### `POST /v1/meals/analyze`
The gateway exposes it as `/api/v1/meals/analyze`.

**Request** (`multipart/form-data`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `image` | file | yes | JPEG or PNG. Check the real file bytes with Pillow, not the extension |
| `meal_type` | string | yes | `breakfast`, `lunch`, `dinner` or `snack` |
| `captured_at` | ISO 8601 datetime with timezone | no | Defaults to the server time if missing |
| `reference_object` | string | no | `card` or `none`. **The final format is still open with C4** |

**Error responses:**

| Case | Status |
|---|---|
| No image, missing `meal_type`, or an invalid `meal_type` | 422 |
| Not a JPEG/PNG (checked from the bytes) | 415 |
| The image can't be decoded | 422 |
| The file is over the size limit (set in `config.py`) | 413 |
| No food recognised | 200, with an empty `foods` list and a warning |
| Unexpected error | 500, with a generic message. Log the details; never leak a stack trace |

Use one error body shape everywhere, for example `{"detail": "<message>", "code": "<snake_case_code>"}`.

### Response: the `meal_nutrition` contract
**This is a DRAFT until C2 and C3 approve it in `contracts/`.**

```json
{
  "contract_version": "meal_nutrition/v1",
  "meal_id": "uuid",
  "meal_type": "lunch",
  "captured_at": "2026-10-08T12:40:00+05:30",
  "is_mock": false,
  "foods": [
    {
      "label": "red_rice_cooked",
      "display_name": "Red rice (cooked)",
      "portion_g": 180.0,
      "portion_method": "reference_card",
      "nutrition": {
        "energy_kcal": 0.0, "carbohydrate_g": 0.0, "protein_g": 0.0,
        "fat_g": 0.0, "fibre_g": null
      },
      "nutrition_source": "SL_FCDB",
      "source_food_code": "<code in the source table>",
      "recognition_score": 0.0
    }
  ],
  "totals": { "energy_kcal": 0.0, "carbohydrate_g": 0.0, "protein_g": 0.0, "fat_g": 0.0, "fibre_g": null },
  "model": { "recognition": "<model name>", "version": "<version or 'mock'>" },
  "warnings": []
}
```

**Rules for the response:**
- A nutrient that is unknown is `null`, never `0`. Totals skip nulls and add a warning saying which nutrient is incomplete.
- `nutrition_source` is `SL_FCDB` (Sri Lankan food composition data) or `USDA_FDC`.
- `portion_method` is `reference_card`, `default_serving` or `user_edited`.
- `recognition_score` is for C2, C3 and evaluation only. **The app must never show it to patients** (team rule), even though the HTML prototype shows confidence percentages. Don't copy those from the prototype.
- Mock responses set `"is_mock": true` and `"version": "mock"`.

---

## 5. Image validation and preprocessing

1. Read the upload into memory, and reject it as soon as it passes the size limit.
2. Open it with Pillow and `verify()` it, then reopen it. The real format must be JPEG or PNG.
3. Apply the EXIF orientation (`ImageOps.exif_transpose`) and convert to RGB.
4. For the model: resize and normalise with the transforms the model was trained with. Keep these in `ml/`, next to the model, so training and inference always match.
5. Never save the uploaded image to disk unless a task needs it, and never commit images.

---

## 6. Food recognition

### Datasets (secondary only, see ADR 0002)

| Dataset | Role | Notes |
|---|---|---|
| Food-101 | Primary, for the baseline | 101 classes, 101,000 images. Use the **official split**: 750 train and 250 test images per class. Take the validation set out of the train split |
| UEC-FOOD-256, VIREO Food-172 | Optional | Check each licence and record it in an ADR before use |
| Public Sri Lankan food sets (Kaggle, Roboflow) | For Sri Lankan dishes and multi-label training | Check the licence and class list. Report how small they are |
| Nutrition5k | Possible | **Not confirmed yet.** Agree with the supervisors before using it |

### Approach
1. **Baseline:** EfficientNetV2 with ImageNet weights, fine-tuned single-label on Food-101. Train the head first, then unfreeze the backbone.
2. **Multi-label:** a sigmoid output per class with BCE loss, trained on the plates that contain several foods. Per-class thresholds are chosen on the validation set, never on the test set.
3. **Comparison:** MobileNetV3 with the same data and splits, to compare speed against accuracy.
4. **Label mapping:** every model class maps to a row in the nutrition table (section 8). A class with no mapping is a bug, so write a test for it.

### Rules for experiments
- Fix the random seeds and log the config, dataset version, metrics and model file to MLflow for every run.
- Report on the test split only once a model is final.
- **Metrics:**
  - single-label: top-1 and top-5 accuracy, and macro F1
  - multi-label: mAP, and micro and macro F1
  - Always include a confusion matrix or the classes the model confuses most.
- Weights go in `data/c1/models/` or MLflow artifacts, never in Git.

---

## 7. Portion estimation

**Reference card:** a standard bank card, ID-1 size, **85.60 × 53.98 mm**, placed flat next to the plate.

1. Detect the card using OpenCV (edges → largest four-sided contour with the right aspect ratio), then correct the perspective.
2. Work out the scale in mm per pixel from the card's known size.
3. Find each food's region (a segmentation mask, or a bounding area to start with) and calculate its area in cm².
4. Convert area to grams with a per-food factor (g per cm²). Use the sources the factors come from, and record them; never guess.
5. **No card found:** use a default serving size from the nutrition data, set `portion_method` to `default_serving`, and add a warning.
6. **User edits** in the app: recalculate from the edited grams and set `portion_method` to `user_edited`.

**Evaluation:** ECUSTFD has ground-truth weights. It uses a **coin**, not a card, as its reference, so say so in the report. Report MAE and MAPE in grams.

---

## 8. Nutrition knowledge base

### Sources, in priority order
1. **Sri Lankan food composition data.** Confirm the publisher before citing it (the peer-reviewed paper is Opatha et al., 2025). The current CSV export is corrupted: **the importer must reject a header of `food_100me`**.
2. **USDA FoodData Central** as fallback. Use `sri_lankan_food_converted.csv` (363 rows, mapped to the 36-column template), with `..._all_nutrients.csv` and `..._food_metadata.csv` for extra detail.

### Tables in the `c1` schema (planned)
- `foods`: id, name, source (`SL_FCDB` | `USDA_FDC`), source_food_code, nutrients **per 100 g** (null where unknown), default_serving_g.
- `label_map`: model label → food id, plus the reason for the match.
- `meals` and `meal_items`: saved analyses (meal id, time, type, per-item grams, portion method, nutrition snapshot).

### Calculation
`nutrient_for_portion = nutrient_per_100g × portion_g / 100`, rounded only when the result is shown, never when it is stored.

### Importer rules
- Validate the header, column count, units and number types. Reject bad files with a clear error that names the file and the row.
- Make the importer idempotent: running it twice gives the same table.
- Never fill a missing value with an estimate. Leave it null.

---

## 9. Testing

| Type | Where | Examples |
|---|---|---|
| Unit | `tests/unit/` | image validation cases, portion maths, nutrient scaling, null handling, the importer rejecting `food_100me` |
| API | `tests/integration/` | `TestClient` calls to `/v1/meals/analyze`: each status code in section 4, and the response shape matching `schemas.py` |
| Contract | `tests/integration/` | the response validates against the agreed `meal_nutrition` schema |
| Model | `tests/unit/` | the model loads and output shapes are right, using a tiny dummy model; no training in tests |

- **Test images** are generated in fixtures (for example a coloured Pillow image, a fake card drawn on it, and corrupt bytes). Never use real patient photos.
- Tests must run fast, with no GPU, no internet and no database. Use a SQLite or in-memory fake for the repository.

---

## 10. App screens (owned by the client owner, for reference)

The prototype's meal-scan flow, as the C1 output must support it:
1. **Capture:** photo with the card beside the plate, plus the meal type.
2. **Analysing:** steps shown while the request runs.
3. **Confirm detected foods:** the patient can remove, edit or add foods. **No confidence percentages.**
4. **Meal analysis:** totals for energy, carbohydrate, protein and fat, with the data source available.
5. **Edit portion:** the app sends the edited grams, and C1 recalculates.

Design tokens, from the prototype: primary `#087F8C`, background `#F7FAFA`, card `#FFFFFF`, text `#172B35`, secondary text `#667780`, border `#DCE5E7`, success `#2E9B62`, warning `#E6A23C`, danger `#D9534F`, font Inter, card radius 16 px, button and input radius 12 px.

---

## 11. Open items for C1

- The final `reference_object` format (agree with C4).
- `meal_nutrition` v1 approval (C2 and C3).
- The confirmed publisher name of the Sri Lankan food composition database, and a fixed CSV export.
- The licences of the optional and Sri Lankan image datasets, and whether Nutrition5k is used.
- Evaluation targets (agree with the supervisors).
- Whether a qualitative band ("High" or "Medium") may be shown to patients instead of a percentage (supervisor decision).
