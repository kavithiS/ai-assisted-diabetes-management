# ADR 0004: Request contract for `POST /api/v1/meals/analyze`

> **TODO(c1):** copied from the old `c1_kavithi` branch. Paths in this file predate the
> monorepo move: the service now serves `/v1/meals/analyze` (the gateway exposes it as
> `/api/v1/meals/analyze`), `/docs` and `/openapi.json`. Docker is no longer used (ADR 0003),
> and C1 uses secondary datasets only (ADR 0002).

- **Status:** Accepted (`reference_object` is experimental, see below)
- **Date:** 2026-10-03
- **Decider:** Thilakarathne K.S (IT23295742), C1 owner

## Context

C4's Flutter app sends meal photos to C1. C2 needs accurate meal timing for glucose
forecasting. Portion calibration with a reference object is specified in the TAF, but its
format is not, and it is not implemented yet. The contract must be fixed now
(contract-first) so that consumers can build against it.

## Decision

The endpoint accepts **`multipart/form-data`** with these fields:

| Field | Type | Required | Rules |
|---|---|---|---|
| `image` | file | yes | **JPEG or PNG only.** Allowed types (`ALLOWED_IMAGE_TYPES`, which may only narrow `{image/jpeg, image/png}`) and the max size (`MAX_IMAGE_BYTES`) come from config. |
| `meal_type` | enum | no | One of `breakfast`, `lunch`, `dinner`, `snack` (case-sensitive). |
| `captured_at` | string | no | Timezone-aware ISO 8601 / RFC 3339 datetime. Validated strictly (see below). |
| `reference_object` | string, nullable | no | **Experimental.** Accepted and passed through unchanged (see below). |

Empty form values are treated as not provided (FastAPI behaviour).

### Image rules

1. **Size is enforced while reading, never after loading the whole file.**
   - An ASGI middleware caps the whole request body at `MAX_IMAGE_BYTES +
     MULTIPART_OVERHEAD_BYTES`. A larger `Content-Length` is rejected before any of the body
     is read. Bodies without a length (chunked transfer) are counted as they stream and
     aborted once they pass the cap.
   - The image part is then read in `UPLOAD_CHUNK_BYTES` chunks and rejected as soon as it
     exceeds `MAX_IMAGE_BYTES`.
2. **An empty file** counts as a missing image.
3. **Format is detected from the bytes** (JPEG `FF D8 FF`, PNG `89 50 4E 47 0D 0A 1A 0A`),
   using our own signature checks. No Pillow, no `imghdr`. If the bytes are not an allowed
   format, the result is **415**.
4. **The declared part Content-Type must also be an allowed type.** Parameters are ignored,
   and `image/jpg` / `image/pjpeg` are treated as `image/jpeg`. A misleading header (for
   example a text file declared `image/jpeg`, or a JPEG declared `text/plain` or
   `application/octet-stream`) gives **415**. If both the declared and the detected type are
   allowed but differ (PNG bytes declared `image/jpeg`), the detected type wins and a warning
   is logged.
5. **Decoding uses OpenCV (`cv2.imdecode`).** If the bytes match JPEG/PNG but fail to decode
   (corrupt or truncated), the result is **422 `IMAGE_UNREADABLE`**. A JPEG with no
   End-Of-Image marker (`FF D9`) is treated as truncated, because libjpeg would otherwise
   decode it silently.
6. **HEIC/HEIF is unsupported.** *Dependency on C4:* the Flutter client must convert photos
   to JPEG before upload, and must set the image part's Content-Type to `image/jpeg`. Some
   Flutter HTTP clients default to `application/octet-stream`, which is rejected.

### `captured_at` rules

- Must be a string matching RFC 3339: `YYYY-MM-DDTHH:MM:SS[.ffffff](Z|±HH:MM)`.
  Rejected: naive datetimes, date-only values, Unix timestamps, a space separator, offsets
  without a colon, and lower-case `t`/`z`.
- Normalised to UTC in the response.
- Rejected if later than now + `CAPTURED_AT_MAX_FUTURE_SKEW_SECONDS` (default 300 s).
  **Past timestamps are always valid.**

### `reference_object` (experimental)

- Interim design: an optional string, at most `REFERENCE_OBJECT_MAX_LENGTH` characters,
  echoed back unchanged. It has no effect on the analysis.
- It is marked **EXPERIMENTAL** in the OpenAPI field description (also `x-experimental: true`).
- The TAF does not define its format. It will **likely become an enum** (e.g. a known
  object type) **or a dimensions object**.
- **It must be finalised before C4 integration**, and that change **will be breaking**.

### Error responses

All 4xx/5xx responses, including framework errors (404, 405, body-parsing failures), use
one envelope:

```json
{
  "error": {
    "code": "UNSUPPORTED_MEDIA_TYPE",
    "message": "Human-readable explanation.",
    "details": [{"field": "image", "issue": "..."}]
  },
  "request_id": "..."
}
```

`request_id` matches the `X-Request-ID` response header.

| Case | HTTP status | `error.code` |
|---|---|---|
| `image` missing, empty, or sent as a non-file field | 422 | `IMAGE_REQUIRED` |
| Request is not `multipart/form-data` | 415 | `UNSUPPORTED_MEDIA_TYPE` |
| Bytes are not JPEG/PNG, or not in `ALLOWED_IMAGE_TYPES` | 415 | `UNSUPPORTED_MEDIA_TYPE` |
| Declared part Content-Type missing or not allowed | 415 | `UNSUPPORTED_MEDIA_TYPE` |
| Image exceeds `MAX_IMAGE_BYTES` / body exceeds the cap | 413 | `IMAGE_TOO_LARGE` |
| JPEG/PNG signature but corrupt or truncated | 422 | `IMAGE_UNREADABLE` |
| Invalid `meal_type`, `captured_at` or `reference_object` | 422 | `INVALID_METADATA` |
| Multipart body cannot be parsed (e.g. no boundary) | 400 | `MALFORMED_REQUEST` |
| Unexpected server error | 500 | `INTERNAL_ERROR` |

Every error path has a pytest test, including a corrupt JPEG, a truncated JPEG, a JPEG
without an EOI marker, and misleading Content-Type headers.

## Consequences

- C4 sends a standard multipart upload (JPEG). No base64 overhead.
- C2 receives `captured_at` normalised to UTC, or `null`.
- Changing allowed types or the size limit is a config change, not a code change.
- The response schema (food items, portion, nutrition, internal confidence fields) is
  defined in `schemas/meal_analysis.py` and documented in `docs/api/meals-analyze.md`.
  Confidence fields are for C2/C3 only. **The patient-facing UI must not display model
  confidence.**

## Alternatives considered

- **Base64 image in a JSON body:** about 33% larger payloads and worse streaming behaviour.
- **Image URL:** would require C1 to fetch remote content, which adds SSRF risk and coupling
  to storage. Out of scope.
- **Accept HEIC via an extra decoder:** adds a dependency outside the approved stack. JPEG
  conversion on the device is simpler.
