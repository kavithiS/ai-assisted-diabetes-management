# `c4_foot_monitoring` — C4 Mobile Platform & Foot Monitoring

> Research prototype. Outputs are estimates and predictions, not diagnoses.

| | |
|---|---|
| Port | 8004 |
| Postgres schema | `c4` |
| Health | `GET /health` |
| Analysis route | `POST /v1/foot/analyze` (multipart field `image`, JPEG/PNG, max 10 MiB) |
| Gateway prefix | `/api/v1/foot/*` |

Run locally from the repository root:

```bash
uv sync
uv run uvicorn c4_foot_monitoring.main:app --reload --port 8004
uv run pytest server/services/c4_foot_monitoring
```

### Mock and trained model

Without settings the service uses a **mock classifier**: results are synthetic and every
response says `meta.is_mock: true`. The mock cycles Low → Medium → High so a demo shows every
band.

To use the trained ResNet50 (`best_resnet50_dfu.pth`, never committed; keep it in `data/c4/`):

```bash
uv sync --all-packages --extra model   # adds torch and torchvision to the shared .venv
```

Then set in `.env`:

| Variable | Example | Note |
|---|---|---|
| `FOOT_MODEL_PATH` | `data/c4/best_resnet50_dfu.pth` | Missing file → warning and mock |
| `FOOT_MODEL_CLASSES` | `["ulcer", "normal"]` | Label of output index 0 and 1, in training order. Required with the path: [INFORMATION REQUIRED] |
| `FOOT_MODEL_DEVICE` | `cpu` | or `cuda` |
| `FOOT_LOW_RISK_MIN_NORMAL_PROBABILITY` | `0.8` | "normal" at or above → Low, below → Medium. Placeholder cut-off, to agree with the supervisors |

### Response

`analysis_id`, `classification` (`normal`/`ulcer`), `risk_band` (`Low`/`Medium`/`High`),
`recommendations`, `disclaimer`, `meta` (`is_mock`, `model_name`, `model_version`). There is
**no confidence field**: the score stays inside the service. Errors use the shared envelope
with `IMAGE_REQUIRED` 422, `IMAGE_TOO_LARGE` 413, `UNSUPPORTED_MEDIA_TYPE` 415 or
`IMAGE_UNREADABLE` 422. The photo is never stored. The recommendation texts are placeholders
until clinician-reviewed templates exist.

## Component details

Copied from `docs/SETUP_PROMPT.md` section 1a.

### C4 — Mobile Platform & Foot Monitoring (G.P. Welikala)

**TAF tasks:**

1. Design and develop the cross-platform Flutter app (iOS and Android).
2. Train a CNN (ResNet50/DenseNet) on DFUC2021 for foot abnormality detection.
3. Build a real-time health analytics dashboard with longitudinal trend visualisations.
4. Implement context-aware push notifications and a smart alert system.
5. Integrate all AI microservices, and conduct UAT with 50+ diabetic patients.

**Novelty (TAF):**

- The first consumer-grade AI foot ulcer monitoring module embedded in a dietary diabetes app.
- An adaptive smart dashboard with predictive alerts driven by behavioural and clinical patterns.

**Data:**

| Purpose | Source (TAF) | Status |
|---|---|---|
| Foot images | DFUC2021, DFU-QUT | Secondary. Check each dataset's access and licence terms |
| Local foot images | "Potential hospital partnership" | Optional. Requires ethical clearance |
| UAT | 50+ diabetic patients | Requires ethical clearance |

**Inputs and outputs:**

- Foot service input: a foot image. Output: an estimated abnormality class.
- Client: consumes every gateway endpoint and renders all screens.

**Decisions:**

- Flutter is the client (per the TAF).
- Proposed: C4 owns `client/` and `server/gateway/`, per TAF task 5. Awaiting confirmation.

**Open items:**

- The push-notification provider.
- Ethics timing for UAT.
- The access status of DFUC2021 and DFU-QUT.
