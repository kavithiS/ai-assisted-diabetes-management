# Repository context for C4 (Foot Monitoring + Flutter client)

Written on 2026-10-20 from what is actually on the remote branches of
`github.com/kavithiS/ai-assisted-diabetes-management`. Use it to plan and prompt the C4 work so
it matches what the other three members have already built. Nothing here is a requirement from
the TAF. Where something is a team decision, the source is named.

---

## 1. Project in one paragraph

DiaCare AI (SLIIT J26-IT-352) is a research-prototype diabetes care system for Sri Lankan
patients. It has four components: C1 food recognition and nutrition, C2 glucose forecasting,
C3 risk profiling with SHAP/LIME, and C4 (G.P. Welikala) foot ulcer detection plus the Flutter
patient app. It is a client-server monorepo: a Flutter app talks only to a FastAPI gateway on
port 8000, and the gateway proxies to one FastAPI service per component (ports 8001–8004).
Services never call each other. Each service owns one PostgreSQL schema (`c1`–`c4`).

## 2. State of the branches (2026-10-20)

Nothing has been merged into `main` since 2026-10-08. `main` only holds the empty scaffold.
Every member's real work is on their own branch:

| Branch | Owner | What it holds |
|---|---|---|
| `main` | all | Scaffold: health checks, a plain proxy gateway, 501 placeholder routes, placeholder Flutter screens |
| `feat/c1-food-recognition-fix` | C1 | **The most complete branch.** C1 service (trained PyTorch recogniser, nutrition DB, meal history), **gateway JWT login**, the shared error envelope and internal auth in `server/shared`, the **full Flutter design system and app shell** (splash, login, register, onboarding questionnaire, home dashboard, 5-tab navigation, profile), architecture docs |
| `c2_nethmi` | C2 | GRU glucose forecast at `POST /v1/glucose/forecast`, training scripts on CGMacros, Flutter glucose screen with an `fl_chart` trajectory chart |
| `c3_lochana` | C3 | Risk model (LR/RF/XGBoost, calibrated), SHAP + LIME, `POST /v1/risk/assess`, Streamlit demo, Flutter risk_profile feature (data/domain/presentation layers) |
| `c4_guwindu_footmonitoring` | C4 | Local only, same as `main`. No C4 work yet |

**C4's branch starts from `main`, so the C1 login, shared error envelope and Flutter design
system are not in it yet.** See section 9 for what that means.

## 3. Team rules that apply to every line of C4 code

From `CLAUDE.md`, `docs/SETUP_PROMPT.md` and the ADRs:

- Research prototype. Say "estimated" and "prediction", never "diagnosis". No
  clinical-validation claims. Every result screen shows a disclaimer.
- **Never show raw model confidence values in patient-facing UI.** Confidence may exist in an
  API response only as an internal or research-only field.
- Never invent data, results, metrics, citations or participants. Write `[INFORMATION REQUIRED]`.
- No primary patient data before ethical clearance. This blocks hospital foot images and the
  UAT with 50+ patients until clearance. Development uses DFUC2021 / DFU-QUT (check licences).
- **Images are never stored** (on disk or in the database). Only derived results are stored,
  each with `model_version`. (Owner answer recorded in C1's `BACKEND_ARCHITECTURE.md`.)
- Work only in your own folders: `server/services/c4_foot_monitoring/`, `data/c4/`,
  `client/mobile_app/lib/features/foot_monitor/`. The gateway and client were decided as C4's
  on 2026-10-18 (decision D2), but `contracts/` and `server/shared/` need all affected owners
  to review the PR.
- Ask the team before adding a new framework. Stack is fixed (section 4).
- Workflow: understand → inspect → implement → lint → test → report.
- Conventional Commits (`feat(c4): …`), GitHub flow, PR to `main`, never push to `main`.

## 4. Languages, frameworks and libraries in use

### Server (all services)

| What | Used by the team |
|---|---|
| Language | Python 3.11 (`requires-python = ">=3.11,<3.12"`) |
| Web framework | FastAPI, Pydantic v2, pydantic-settings, Uvicorn |
| Deep learning | **PyTorch + torchvision** (team standard; TAF names torchvision ResNet50 / DenseNet for C4) |
| Images | OpenCV (`opencv-python-headless`), NumPy. C1 decodes with `cv2.imdecode` and checks JPEG/PNG magic bytes, no Pillow at serve time |
| Database | PostgreSQL 16, SQLAlchemy 2, Alembic, `psycopg[binary]`. SQLite is used in unit tests |
| Packaging | uv workspace, one root `uv.lock`, `src/` layout, hatchling build backend |
| Quality | Ruff (line length 100; rules E, F, W, I, B, UP, SIM), `ruff format`, **mypy strict** with the pydantic plugin, pytest (`--import-mode=importlib`), pre-commit |
| CI | GitHub Actions: `uv sync`, ruff check, ruff format --check, mypy server, pytest; then flutter pub get, analyze, test |
| Local run | No Docker (ADR 0003). `scripts/dev.ps1` opens one PowerShell window per service. Native PostgreSQL 16. Optional local MLflow on SQLite |
| Not allowed | ASP.NET/C#, React/Node frontends, extra databases (no Redis, no MongoDB), new frameworks without asking |

Other members' ML libraries: C2 uses `torch`, `numpy`, `pandas`. C3 pins `scikit-learn`,
`xgboost`, `shap`, `lime`, `numpy==1.26.4`. C1 needs `numpy>=2.4.6`. **These numpy versions
conflict in the shared `uv.lock`** and will have to be resolved when the branches merge. C1's
PyTorch is not in `uv.lock` yet: it runs in a separate training environment (`training/requirements.txt`)
and the service imports torch lazily.

### Client

| What | Used by the team |
|---|---|
| Language / SDK | Dart, Flutter stable, `sdk: ^3.5.0`, Material 3 |
| Packages on C1's branch | `http`, `http_parser`, `image_picker`, `google_fonts`, `flutter_secure_storage` |
| Packages on C2's branch | `fl_chart`, `http` |
| Packages on C3's branch | `http`, `shared_preferences` |
| Dev | `flutter_test`, `integration_test`, `flutter_lints` |
| State management | None added. `StatefulWidget` + `setState` (C1, C2), `ChangeNotifier` (C3). No Provider/Riverpod/Bloc, no routing package |
| Platforms | Android and web folders were generated with `flutter create` (org `lk.sliit.diacare`). Cleartext HTTP is allowed for the local gateway |
| Base URL | `AppConfig.apiBaseUrl`, default `http://10.0.2.2:8000` (Android emulator), override with `--dart-define=API_BASE_URL=...` |

## 5. Server architecture patterns to copy

### 5.1 Request path and identity (ADR 0005, on C1's branch)

```
Flutter ──Bearer JWT──► Gateway :8000 ──X-Patient-Id + X-Internal-Token + X-Request-ID──► C4 :8004
```

- The gateway owns login (email + password, Argon2id, JWT access token 15 min, rotating
  refresh token 30 days, users in schema `core`). Self-registration is off until ethical
  clearance; demo accounts are made with `uv run python -m diacare_gateway.cli create-user`.
- The gateway strips any client-sent `Authorization`, `X-Patient-Id`, `X-Internal-Token`, and
  adds its own. **Services never handle passwords or tokens.**
- A service trusts `X-Patient-Id` only when `X-Internal-Token` matches its `INTERNAL_TOKEN`
  setting. Use `diacare_shared.internal_auth.make_patient_id_dependency(...)`.
- The gateway route for C4 already exists on C1's branch:
  `/api/v1/foot` and `/api/v1/foot/{path}` → C4 `/v1/foot/...`, authenticated, with the
  patient id forwarded.
- Patient deletion: the gateway calls `DELETE /internal/v1/patients/{patient_id}` on each
  service in `DELETE_FANOUT_SERVICES`. Every service that stores patient data must offer it
  (internal-token only, returns 204 even when nothing was found).

### 5.2 Shared package (`server/shared/src/diacare_shared/`, on C1's branch)

| Module | Use |
|---|---|
| `errors.py` | `AppError(status, code, message, details=...)`, `ErrorCode` enum, `install_exception_handlers(app)`. Every package returns the same envelope: `{"error": {"code", "message", "details": [{"field", "issue"}]}, "request_id"}` |
| `request_context.py` | `RequestContextMiddleware`: reads or creates `X-Request-ID`, logs `duration_ms` |
| `internal_auth.py` | `make_patient_id_dependency`, `make_internal_token_dependency` |
| `health.py` | `create_health_router(SERVICE_NAME)` → `GET /health` |
| `logging.py` | `configure_logging(level)` (JSON logs) |
| `db.py` | Engine and session helpers (SQLite gets `schema_translate_map`) |
| `config.py` | `BaseServiceSettings` (`log_level`, `database_url`, `mlflow_tracking_uri`, `internal_token`) |

The C4 `main.py` on C1's branch already calls `install_exception_handlers(app)` and adds
`RequestContextMiddleware`. The route `POST /v1/foot/analyze` still returns 501.

### 5.3 Service layout (C1 is the reference implementation)

```
server/services/c1_food_nutrition/src/c1_food_nutrition/
  main.py            create_app(settings) factory + lifespan that pre-loads the model in a thread
  config.py          pydantic-settings Settings (frozen, env vars, validators)
  api/routes.py      thin routes only; logic lives in services/
  api/deps.py        FastAPI dependencies (settings, model, patient id, multipart checks)
  api/history.py     patient-scoped CRUD
  api/internal.py    DELETE /internal/v1/patients/{id}
  api/exception_handlers.py, api/middleware.py (body size limit, request context)
  core/errors.py     service-specific error codes on top of the shared envelope
  ml/interfaces.py   typing.Protocol for the model (FoodRecognizer), frozen dataclasses for outputs
  ml/mock.py         Mock implementation returning obviously synthetic output, is_mock = True
  ml/torch_recognizer.py  real PyTorch model; torch imported lazily; bundle loaded with weights_only=True
  ml/preprocessing.py     image decode / resize
  services/image_validation.py  upload checks (size, magic bytes, Content-Type, decodable)
  services/pipeline.py          orchestrates validate → model → result
  schemas/           Pydantic request/response models (common.py holds DISCLAIMER, ErrorResponse)
  db/models/, db/repositories/, db/migrations/ (Alembic), db/session.py
src/c1_training/     training code (cleaning, leak audit, stage1/stage2 training, export to a model bundle)
training/            configs, requirements.txt for the GPU/training env, training tests
tests/unit/, tests/integration/
docs/                CONTEXT, DATA, EXPERIMENTS, CHANGELOG, OPEN_ITEMS, ROADMAP, api/*.md, adr/
```

Key C1 conventions worth copying for the foot model:

- Settings switch `RECOGNIZER=mock|torch`. With `torch`, `MODEL_PATH` is required
  (validated). `MODEL_DEVICE=cpu|cuda`. The service and CI tests run on the mock without
  PyTorch installed.
- Model weights and data are never committed to git (`data/` is gitignored, DVC planned).
- Every response carries `model_name`, `model_version`, `is_mock`, and a disclaimer.
- Image upload: `multipart/form-data`, field `image`, JPEG or PNG, max 10 MiB, read in
  chunks, magic-byte check, truncated-JPEG check, `cv2.imdecode` must succeed. Error codes:
  `IMAGE_REQUIRED` 422, `IMAGE_TOO_LARGE` 413, `UNSUPPORTED_MEDIA_TYPE` 415,
  `IMAGE_UNREADABLE` 422. The gateway caps bodies at 11 MB. The app resizes photos to 1280 px.
- Inference runs in a worker thread. Run one uvicorn worker per model service.
- Never log health values, images, emails or tokens. Log only `request_id`, `patient_id`, timings.

C3's variation: the lifespan loads model bundles; if missing, the service still starts,
`GET /v1/risk/status` reports `model_loaded: false`, and the predict route returns 503.
C2 returns 503 when the model file cannot be loaded.

### 5.4 Database conventions (C1's `BACKEND_ARCHITECTURE.md`, accepted 2026-10-18)

- One database `diacare`, schemas `core`, `c1`…`c4`, one login role per schema (`diacare_c4`).
- Every patient-owned table: `patient_id UUID NOT NULL`, indexed with its time column. No
  foreign keys across schemas.
- `timestamptz` in UTC. Unknown values are `NULL`, never 0. Every model output row stores
  `model_version`. Every table has a primary key and `created_at`. Use C1's constraint naming
  convention (`db/base.py`). Alembic per service with `version_table_schema="c4"`.
- Proposed `c4` tables (owner C4 confirms):
  - `foot_screening`: `id`, `patient_id`, `captured_at`, `foot_side` (`left`/`right`),
    `abnormality_class`, `risk_level`, `model_version`, `recommendation_code`. **No image.**
  - `notification`: `id`, `patient_id`, `kind`, `created_at`, `sent_at`, `read_at`, added only
    when alerts are designed.
- List endpoints paginate and cap `limit` at 100.

### 5.5 Contracts

`contracts/` has rules but no fields yet. `foot_analysis` (C4 service → client) is C4's to
propose in a PR. Each field states type, unit and required/optional, version `MAJOR.MINOR`,
breaking changes get `/v2/`. C1 documented its request contract in an ADR
(`docs/adr/0004-meal-analyze-request-contract.md`) and `docs/api/meals-analyze.md`; C3 wrote
`docs/contract_proposal.md`. C4 can follow either.

## 6. Flutter app: the look and structure to match

The shared design is on **C1's branch** (`feat/c1-food-recognition-fix`). Its code says it
matches the team's HTML prototype (`DiaCare_AI_-_Interactive_Prototype_Component1-4.html`).
That file is not in any branch on GitHub; it sat untracked on C1's machine. The prototype shows
confidence percentages; those must **not** be copied into the app.

### 6.1 Theme (`lib/core/theme.dart`)

- Material 3, font **Inter** via `google_fonts` (`GoogleFonts.interTextTheme`).
- Colours (`AppColors`):

| Token | Hex | Token | Hex |
|---|---|---|---|
| `primary` | `#087F8C` (teal) | `text` | `#172B35` |
| `primaryDark` | `#05636D` | `textSecondary` | `#667780` |
| `primaryLight` | `#E6F6F7` | `border` | `#DCE5E7` |
| `background` | `#F7FAFA` | `card` | `#FFFFFF` |
| `success` / `successBg` | `#2E9B62` / `#E9F6EF` | `warning` / `warningBg` | `#E6A23C` / `#FCF3E3` |
| `danger` / `dangerBg` | `#D9534F` / `#FBEAE9` | | |

- Buttons: full width, 50 px high, radius 12, Inter 15 bold. Helpers `primaryButtonStyle()`,
  `secondaryButtonStyle()` (teal outline), `ghostButtonStyle()` (grey outline).
- Cards: `appCardDecoration()`, white, radius 16, 1 px `border` colour, no shadow.
- Inputs: filled white, radius 12, border 1.5 px, teal when focused.
- Chips: radius 20, selected = teal fill with white text.

### 6.2 Shared widgets (`lib/core/widgets.dart`)

`AppCard`, `AppBadge` (success / warning / danger / neutral pill), `AiTag` and `AiCard`
("AI Insight" box on `primaryLight`), `SectionLabel` (small uppercase grey heading),
`NutritionBarRow` (label + value + progress bar), `AppListRow`, `IconContainer` (rounded square
icon tile), `DisclaimerBanner` (amber box with a warning icon), `ChipRow` (single-choice chips).
`lib/core/coming_soon_view.dart` is the template for unbuilt features.

### 6.3 App shell (`lib/main.dart`)

- `main()` restores the saved login (`AuthSession.instance.restore()`), then opens `/`
  (splash → welcome → login/register → questionnaire) or `/home`.
- `HomeShell`: custom bottom bar (white, top border, 62 px, icon 19 px + label 10.5 px, teal
  when active) with 5 tabs in an `IndexedStack`: **Home, Meals, Insights, Foot, Profile**.
- The **Foot tab is index 3** and shows `FootMonitorScreen`. The home dashboard also has an
  `onFootCheck` shortcut that pushes `FootMonitorScreen`.
- Today `FootMonitorScreen` is a `ComingSoonView` ("Foot Monitoring", "Photograph your foot and
  get an estimated abnormality class", "Smart alerts when something may need attention").

### 6.4 Feature folder pattern

C1 (closest match for a photo-based feature):

```
lib/features/meal_scan/
  meal_scan_screen.dart        stage machine: enum _Stage { capture, review, analysing, result }
  data/meal_api.dart           MealApi: multipart POST via the gateway, timeout, error mapping
  data/meal_analysis.dart      response models with fromJson
  widgets/...                  result view, dialogs
test/features/meal_scan/       screen, API and model tests with fake data
```

- Photo picking: `ImagePicker().pickImage(source, maxWidth: 1280, maxHeight: 1280)` → bytes.
  The picker is injected as a function so tests can fake it.
- API classes take optional `ApiClient`, `http.Client` and timeout in the constructor (for
  tests). Requests go through `AuthHttpClient` (adds the Bearer token, refreshes on 401).
- Errors: read the shared envelope's `error.code`, map it to a patient-safe message; handle
  `TimeoutException` and `http.ClientException` with "Cannot reach the server..." messages;
  never crash on a bad response (`BAD_RESPONSE`).
- Every screen uses `AppColors.background`, `SafeArea`, a `ListView` with padding about
  `22, 6, 22, 24`, an optional back `IconButton`, a header row (`IconContainer` + Inter 20
  w800 title + optional `AppBadge`), then `AppCard`s, then a `DisclaimerBanner`.

C3 uses a layered variant (`data/`, `domain/`, `presentation/`, `c3_strings.dart` for all text,
a repository interface with mock and API implementations, a `ChangeNotifier` controller) and
uses `Theme.of(context).colorScheme` instead of `AppColors`. C2 uses a single form screen with
plain Material widgets and `fl_chart`. **C1's style is the one the app shell uses, so C4 should
match C1.** C3's ideas worth reusing: all strings in one file, risk shown as words + icon +
colour (not colour alone, WCAG), mock repository switch for demos.

## 7. What C4 has to build (from the TAF, via the C4 README)

1. The cross-platform Flutter app (iOS and Android). Most of the shell exists on C1's branch.
2. A CNN (ResNet50 / DenseNet, torchvision) trained on DFUC2021 for foot abnormality detection.
   Optional DFU-QUT. Hospital images only after ethical clearance.
3. A real-time health analytics dashboard with longitudinal trend charts (the Insights tab is
   "Coming in a future release"; the home dashboard numbers are hard-coded today).
4. Context-aware push notifications and a smart alert system (provider not chosen, decision
   D10).
5. Integrate all AI microservices, and UAT with 50+ diabetic patients (after ethical
   clearance).

Foot service: input a foot image, output an estimated abnormality class.

Already done for C4 by others (on C1's branch, needs C4's review): gateway login, gateway foot
proxy, login/register screens, token storage, onboarding, home shell.

## 8. Open decisions that touch C4

| # | Decision | Status |
|---|---|---|
| D2 | Gateway and client owner | Decided 2026-10-18: C4 |
| D7 | Where onboarding answers are stored (foot module → C4) | Open |
| D8 | Write the `foot_analysis` contract | Open |
| D9 | UAT server and HTTPS reverse proxy | Sent to supervisors, no answer |
| D10 | Push notification provider | Open (C4) |
| D11 | Performance targets | Open, measure first |
| D12 | Data protection (Sri Lanka PDPA No. 9 of 2022) for UAT | Sent to supervisors, no answer |
| D14 | Offline use of the app | Open (C4), default online only |
| D16 | Risk band vs percentage for patients | Sent to supervisors, default band only |
| — | DFUC2021 / DFU-QUT access and licence | Open |
| — | Ethics timing for UAT | Open |
| — | The foot output classes and risk levels | [INFORMATION REQUIRED] |

## 9. Practical notes before starting

- C4's branch is based on `main`. To build the Flutter screen in the shared style, C4 needs
  `lib/core/theme.dart`, `lib/core/widgets.dart`, `lib/main.dart` and the auth client from
  C1's branch. Options: wait for C1's PR to merge and then merge `main`; or merge
  `origin/feat/c1-food-recognition-fix` into the C4 branch now (brings all of C1's work, so
  C4's PR would contain it too). Agree this with C1.
- The server side of C4 can start on `main` without waiting: model training, `ml/interfaces.py`
  + mock + torch implementation, image validation, schemas, tests. The shared envelope and
  internal auth arrive with C1's merge.
- `client/mobile_app/lib/core/api_client.dart` was changed differently on C1's and C2's
  branches. Expect a merge conflict there. C4, as client owner, will review both.
- Run before every commit: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy server`, `uv run pytest`, and in `client/mobile_app`: `flutter analyze`,
  `flutter test`.
