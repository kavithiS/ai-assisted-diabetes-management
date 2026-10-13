# Gateway note for C3 (no gateway change needed)

**For:** the gateway owner. **From:** C3. `server/gateway/` was not edited.

## What the client needs

| Client calls (gateway :8000) | Forwarded to (C3 :8003) | Method |
|---|---|---|
| `/api/v1/risk/assess` | `/v1/risk/assess` | POST |
| `/api/v1/risk/status` | `/v1/risk/status` | GET |

## What the gateway already does (checked in `routes/risk.py` and `routes/__init__.py`)

- `/api/v1/risk/{path}` is proxied to `C3_URL/v1/risk/{path}` for GET/POST/PUT/PATCH/DELETE,
  so both routes above **already work with no change**.
- Status codes and bodies are relayed unchanged, so C3's three statuses (`ok`,
  `insufficient_data`, `invalid_input` in a 200 body) and its 422 / 503 errors reach the
  client as they are. Query strings are forwarded too (`?debug=true`).
- If C3 is down, the gateway answers **502** "Upstream service unavailable".

## Timeout

`request_timeout_seconds` is 30 s. A C3 assessment (model + SHAP + LIME) takes about
1-6 s on a laptop, so 30 s is enough. No change requested.

## Optional, later

- `/health` on the gateway could also call C3's `/v1/risk/status` to show `model_loaded`.
  Not needed for PP1.
