# `POST /api/v1/meals/analyze`

> **TODO(c1):** copied from the old `c1_kavithi` branch. Paths in this file predate the
> monorepo move: the service now serves `/v1/meals/analyze` (the gateway exposes it as
> `/api/v1/meals/analyze`), `/docs` and `/openapi.json`. Docker is no longer used (ADR 0003),
> and C1 uses secondary datasets only (ADR 0002).

Reference for C2, C3 and C4. The live, authoritative schema is the OpenAPI document at
`/api/v1/openapi.json`. The request rules are recorded in
[ADR 0004](../adr/0004-meal-analyze-request-contract.md).

> **Still MOCK (2026-10-16).** `meta.is_mock` is `true`. By default the items are also
> synthetic. With `RECOGNIZER=torch` and `MODEL_PATH` set (see `training/README.md`) the
> **items come from a trained model**, and with `NUTRITION_TABLE_PATH` set the **nutrient
> values come from the Sri Lankan FCDB or USDA** (`nutrition_source`, per 100 g scaled to the
> portion). Portions are still a fixed 100 g placeholder; `meta.warnings` says which parts
> are mock, notes close or partial table matches, and names foods with no table entry
> (their nutrients, and the totals, are `null`). `carbohydrate_g` from the table is
> *available* carbohydrate (fibre excluded); `sugars_g` is always `null`. Consumers must check
> `meta.is_mock` and must not treat mock values as nutrition data. An empty `items` list
> comes with the warning `No food was recognised in the image.`

## Request: `multipart/form-data`

| Field | Required | Notes |
|---|---|---|
| `image` | yes | JPEG or PNG; the part's Content-Type must be `image/jpeg` or `image/png`. HEIC is unsupported. |
| `meal_type` | no | `breakfast` \| `lunch` \| `dinner` \| `snack` (lower case) |
| `captured_at` | no | RFC 3339 with offset, e.g. `2026-10-03T12:30:00+05:30` |
| `reference_object` | no | **Experimental** free text, echoed back. Will change (breaking) before C4 integration. |

## Response: `200 OK`

```jsonc
{
  "analysis_id": "uuid",
  "meta": {
    "is_mock": true,
    "api_version": "v1",
    "model_name": "mock-recognizer",
    "model_version": "0.0.0-mock",
    "generated_at": "2026-10-03T07:00:01Z",
    "request_id": "…",
    "warnings": ["MOCK RESPONSE: …"]
  },
  "metadata": { "meal_type": "lunch", "captured_at": "2026-10-03T07:00:00Z", "reference_object": null },
  "image": { "media_type": "image/jpeg", "width": 1280, "height": 960, "size_bytes": 123456 },
  "items": [
    {
      "item_id": "item-1",
      "label": "…",
      "food_code": "…",
      "confidence": 0.0,            // INTERNAL (C2/C3 only)
      "region": { "x": 0, "y": 0, "width": 0.5, "height": 1 },
      "portion": {
        "grams": 0.0,
        "household_measure": null,
        "estimation_method": "mock | reference_object | model",
        "confidence": 0.0           // INTERNAL (C2/C3 only)
      },
      "nutrition": { "energy_kcal": 0.0, "carbohydrate_g": 0.0, "sugars_g": 0.0,
                     "dietary_fiber_g": 0.0, "protein_g": 0.0, "fat_g": 0.0, "sodium_mg": 0.0 },
      "nutrition_source": { "source": "MRI_SL_FCDB | USDA_FDC | MOCK", "source_food_id": "…" }
    }
  ],
  "totals": { "energy_kcal": 0.0, "carbohydrate_g": 0.0, "...": "..." },
  "disclaimer": "Research prototype (J26-IT-352). Not a diagnostic or clinically validated tool; …"
}
```

- Nutrient values of `null` mean **unknown**, never zero. A total is `null` if that
  nutrient is unknown for any item.
- `captured_at` is always returned in UTC.
- **Confidence fields are internal.** They exist for C2/C3 modelling. **The
  patient-facing UI (C4) must not display model confidence.**

## Errors

Every error uses the same envelope, and `request_id` matches the `X-Request-ID` header:

```json
{ "error": { "code": "IMAGE_TOO_LARGE", "message": "…", "details": [{ "field": "image", "issue": "…" }] },
  "request_id": "…" }
```

| Status | `error.code` | When |
|---|---|---|
| 400 | `MALFORMED_REQUEST` | Multipart body cannot be parsed |
| 413 | `IMAGE_TOO_LARGE` | Image > `MAX_IMAGE_BYTES`, or request body > image limit + overhead |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Not multipart; bytes not JPEG/PNG; declared type not allowed |
| 422 | `IMAGE_REQUIRED` | No `image` part, or empty file |
| 422 | `IMAGE_UNREADABLE` | JPEG/PNG signature, but corrupt or truncated |
| 422 | `INVALID_METADATA` | Bad `meal_type`, `captured_at` or `reference_object` |
| 500 | `INTERNAL_ERROR` | Unexpected failure (no internals are exposed) |
