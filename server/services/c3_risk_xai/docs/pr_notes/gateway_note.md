# Gateway / dev-script PR note from C3

**For:** the gateway owner and whoever owns `scripts/dev.ps1`. **From:** C3.
`server/gateway/` and `scripts/` were NOT edited. The proxy itself already works
(see `../gateway_pr_note.md`).

## 1. CORS for the Flutter web build (needed for `flutter run -d chrome`)

Measured 2026-10-19: a browser preflight to the gateway fails.

```
OPTIONS http://localhost:8000/api/v1/risk/assess
Origin: http://localhost:5000, Access-Control-Request-Method: POST
-> 405, no Access-Control-Allow-Origin header
```

So Chrome blocks every POST from the web app. Until this is fixed, C3 develops with Chrome
started as `--disable-web-security` (local only, never for users). Android/APK is not
affected (CORS is a browser rule).

Proposed change in the gateway app (development origins only):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)
```

A setting (for example `GATEWAY_CORS_ORIGIN_REGEX`) would keep it off in deployment.

## 2. Use 127.0.0.1 instead of localhost on Windows (latency, NFR1)

Measured 2026-10-19 on the C3 owner's Windows laptop, same trivial request:

| URL | Time |
|---|---|
| `http://localhost:8003/v1/risk/assess` | 2.77 s |
| `http://127.0.0.1:8003/v1/risk/assess` | 0.56 s |
| `http://localhost:8000/api/v1/risk/assess` (gateway, `C3_URL=localhost`) | 3.47 s |
| `http://127.0.0.1:8000/api/v1/risk/assess` | 1.39 s |

`localhost` first tries IPv6 (::1), where uvicorn is not listening, and loses about 2 s per
hop. With `127.0.0.1` everywhere, 10 warm full assessments (model + SHAP + LIME) through the
gateway took a median of 2.15 s (max 3.21 s).

Proposed: in `scripts/dev.ps1`, set `C1_URL ... C4_URL` to `http://127.0.0.1:800x`, and in
`.env.example` the same. No other change.
