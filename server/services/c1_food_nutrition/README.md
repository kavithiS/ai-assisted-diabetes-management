# `c1_food_nutrition` — C1 Food Recognition & Nutritional Analysis

> Research prototype. Outputs are estimates and predictions, not diagnoses.

| | |
|---|---|
| Port | 8001 |
| Postgres schema | `c1` |
| Health | `GET /health` |
| Meal analysis | `POST /v1/meals/analyze` (returns a **mock** response, `meta.is_mock: true`) |
| Gateway prefix | `/api/v1/meals/*` |
| API docs | `GET /docs` |

Run locally from the repository root:

```bash
uv sync
uv run uvicorn c1_food_nutrition.main:app --reload --port 8001
uv run pytest server/services/c1_food_nutrition
```

## Settings

Read from environment variables (or `.env`) by `src/c1_food_nutrition/config.py`:

| Variable | Default | Meaning |
|---|---|---|
| `ALLOWED_IMAGE_TYPES` | `image/jpeg,image/png` | Comma-separated; may only narrow this set |
| `MAX_IMAGE_BYTES` | `10485760` (10 MiB) | Largest accepted image |
| `UPLOAD_CHUNK_BYTES` | `65536` | Read size for the chunked size check |
| `MULTIPART_OVERHEAD_BYTES` | `65536` | Request-body cap is `MAX_IMAGE_BYTES` plus this |
| `CAPTURED_AT_MAX_FUTURE_SKEW_SECONDS` | `300` | How far in the future `captured_at` may be |
| `REFERENCE_OBJECT_MAX_LENGTH` | `200` | Maximum length of the experimental `reference_object` |
| `DATABASE_URL` | `sqlite:///./c1_local.db` | Database for the nutrition tables |

Database migrations (Alembic): `uv run alembic -c server/services/c1_food_nutrition/alembic.ini upgrade head`.

Docs brought over from the old `c1_kavithi` branch: [request contract](docs/adr/0004-meal-analyze-request-contract.md),
[API notes](docs/api/meals-analyze.md), [roadmap](docs/ROADMAP.md).

## Component details

Copied from `docs/SETUP_PROMPT.md` section 1a.

### C1 — Food Recognition & Nutritional Analysis (Thilakarathne K.S)

**TAF tasks:**

1. Food image data. The TAF wording was "collect & annotate"; this is **replaced by secondary datasets** (see Decisions).
2. Fine-tune EfficientNetV2/MobileNetV3 via transfer learning.
3. Multi-label classification for mixed-dish meals (rice and curry platters).
4. Portion-size estimation by reference-object calibration.
5. Nutritional analysis API linked to the MRI Sri Lanka Food Composition DB.

**Novelty (TAF):**

- Multi-label CNN for complex mixed-dish recognition.
- Hybrid nutritional knowledge base merging MRI Sri Lanka with USDA values.
- *The "first large-scale annotated Sri Lankan food dataset" claim no longer applies. Do not repeat it anywhere.*

**Data:**

| Purpose | Source | Role |
|---|---|---|
| Food images | Food-101 | Primary |
| Food images | UEC-FOOD-256, VIREO Food-172 | Optional |
| Nutrition | USDA FoodData Central (mapped to the MRI 36-column schema) | Primary |
| Nutrition | MRI Sri Lanka Food Composition DB | Sri Lankan values. The current CSV export is corrupted: the importer must reject a header of `food_100me` |

**Inputs and outputs:**

- Input: a meal image, an optional `reference_object`, and a meal timestamp.
- Output: identified foods, estimated portions and nutrition totals (carbohydrate, protein, fat, fibre, energy), with the data source recorded per value.
- Consumers: C2 and C3, through the gateway.

**Decisions:**

- Secondary datasets only; no new image collection. The TAF supervisor comment "Data sets are available" supports this. It is recorded in ADR 0002.
- No ethical clearance is needed for C1, because no primary images are collected.

**Open items:**

- The final `reference_object` format (this blocks C4's camera screen).
- The MRI CSV corruption fix.
