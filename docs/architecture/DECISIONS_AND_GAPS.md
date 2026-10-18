# DiaCare AI: open decisions and gaps

- **Status:** Living list; statuses updated 2026-10-18
- **Date:** 2026-10-18
- **Companion to:** `BACKEND_ARCHITECTURE.md`

Everything here comes from reading the repository on 2026-10-18. Nothing is assumed: where a
fact is unknown it says [INFORMATION REQUIRED]. When an item is settled, set its Status to
`Decided` or `Fixed` and record the answer and its date, or link the ADR.

Some gaps were found by reading the code, not by running it. They are marked **(not run)**.

## 1. Decisions needed

| # | Item | Why it matters | Who decides | Proposed default | Status |
|---|---|---|---|---|---|
| D1 | Approve ADR 0005 (JWT login in the gateway) and ADR 0006 (`core` schema, `patient_id` everywhere) | No per-patient data can be stored without an identity | All four members, supervisors | As written in the ADRs | **Decided 2026-10-18.** The team agreed to the JWT login and the `core` schema design |
| D2 | Who owns the gateway and the client (SETUP_PROMPT §10.2) | Phases P3, P5 and P8 need an owner | Team | C4 (proposed in SETUP_PROMPT) | **Decided 2026-10-18.** Gateway and client owned by C4. The team said this is not an important decision, because each member builds the Flutter screens for their own component |
| D3 | New libraries: `pyjwt` and `argon2-cffi`; the gateway also needs `sqlalchemy`, `alembic` and `psycopg` | Changes the shared `uv.lock` ("ask before adding a new framework") | Team | Approve | **Decided 2026-10-18.** The team approved adding `pyjwt` and `argon2-cffi` |
| D4 | What happens to the demo meals already in C1 when `patient_id` is added | The migration needs a rule | C1 | Assign them to a fixed `DEMO_PATIENT_ID` | **Applied 2026-10-18 (proposed default; the owner can still change it).** The migration gives existing meals the id `00000000-0000-4000-8000-000000000001`; the local database had no meals, so nothing was reassigned |
| D5 | When the meal chain C1 → C2 → C3 runs: at analyze or at save | Analyze results are not yet confirmed by the patient | C1, C2, C3 | At save, after the patient confirms foods and portions | Open |
| D6 | Glucose unit: mg/dL (app and prototype) or mmol/L (C3 contract proposal) | A unit mix-up corrupts the forecasts and the risk inputs | C2, C3 | Store a value plus a `unit` column; every contract names its unit | Open |
| D7 | Where each onboarding questionnaire module is stored | The answers are not saved today | Team | Each module in the service that uses it (diet → C1, glucose and medication → C2, lifestyle → C3, foot → C4), behind one gateway endpoint | Open |
| D8 | Write v1 of the contracts `meal_nutrition`, `glucose_forecast`, `risk_assessment`, `foot_analysis` and `patient_risk_profile` (all empty in `contracts/`) | The meal chain (P6) cannot be built without them | The producer and consumers of each | Write them before P6 | Open |
| D9 | UAT hosting: which machine or VM, and which HTTPS reverse proxy | C4's UAT with 50+ patients needs a server that phones can reach | Supervisors | One VM; Caddy or nginx (a new tool, needs approval) | **Sent to supervisors 2026-10-18. No answer yet.** Still Open |
| D10 | Push notification provider (C4 "smart alerts") | Decides the `device_push_token` table and any outside service | C4 | Not chosen; leave out until decided | Open |
| D11 | Performance targets | Not in the TAF (SETUP_PROMPT §10.4) | Supervisors | Measure first (architecture section E), then set targets | Open |
| D12 | Data protection: whether the Sri Lanka Personal Data Protection Act No. 9 of 2022 applies to the UAT, the retention period, the data location | Real patient data during UAT | Supervisors, ethics committee | [INFORMATION REQUIRED] | **Sent to supervisors 2026-10-18. No answer yet.** Still Open |
| D13 | Clinician and Admin Portal (in the TAF diagram, no owner, SETUP_PROMPT §10.1) | Affects roles and access rules | Supervisors | Not built; the `role` column reserves `clinician` | **Sent to supervisors 2026-10-18. No answer yet.** Still Open |
| D14 | Offline use of the app | No local storage package exists; C3 has a TODO to persist history on the device | C4 | Online only for now | Open |
| D15 | Sinhala and Tamil interface | Only `name_si` and `name_ta` exist (C1 food table); no requirement was found | Supervisors | Out of scope until confirmed | Open |
| D16 | Show patients a risk band or a percentage (C1 OPEN_ITEMS A6, CLAUDE.md C3 note) | Patient-facing rule on confidence values | Supervisors | Band and DHS only | **Sent to supervisors 2026-10-18. No answer yet.** Still Open |
| D17 | Meal totals when one food's nutrients are unknown | Today the totals become `null` | C1, C2, C3 | Keep `null` (current rule) | Open |
| D18 | Consent wording and versions | Needed before any real data (`core.consent`) | Ethics application | [INFORMATION REQUIRED] | Open |
| D19 | Self-registration after ethical clearance, or accounts created by the researchers only | Affects `REGISTRATION_ENABLED` and the UAT process | Supervisors | Researcher-created accounts for the UAT | Open |

## 2. Gaps found in the repository

| # | Gap | Where | Owner | Fixed by | Status |
|---|---|---|---|---|---|
| G1 | No user or patient identity anywhere: meals are global and the app sends no token | gateway, services, client | All | P3, P4, P8 | **Partly fixed 2026-10-18.** Gateway login and C1 patient scoping are built and tested. Still open: the app has no login screen (P8; until then the gateway runs with `AUTH_REQUIRED=false` and a fixed demo patient) and C2 to C4 store nothing yet (P7) |
| G2 | The gateway's meals route did not cover the bare `/api/v1/meals` path: GET or POST with no trailing segment got a 307 redirect to `/api/v1/meals/`, and even then C1 was called with a trailing slash | `server/gateway/src/diacare_gateway/routes/meals.py` | Gateway | P5 | **Fixed 2026-10-18.** Added a bare-path route, same pattern as `foods.py`. New test `server/gateway/tests/test_meals_routes.py` (failed before the fix, passes after). Verified with a real gateway on a real request: GET, POST, GET by id, DELETE, summary and analyze all return the expected codes with no redirect. The gateway on port 8000 was restarted to run the fixed code |
| G3 | The gateway creates a new `httpx` client for every request | `server/gateway/src/diacare_gateway/` (`get_http_client`) | Gateway | P5 | **Fixed 2026-10-18.** One shared client created at startup |
| G4 | The gateway and C2–C4 return FastAPI's `{"detail": ...}`, but the app parses C1's `{"error": ...}` envelope | gateway, C2–C4 | Shared | P1 | **Fixed 2026-10-18** for the gateway and C2 to C4 (C1 already had the envelope). The app's parser can now read errors from every package |
| G5 | C1 defaults to SQLite, and its tables sit in no schema (there is a TODO in `db/models/food.py`) | `server/services/c1_food_nutrition/src/c1_food_nutrition/config.py`, `db/` | C1 | P2 | Open. The SQLite default is kept for tests; the `c1` schema move waits for the superuser step (G6) |
| G6 | `infra/postgres/init.sql` creates schemas only: no roles, no grants, no `core` | `infra/postgres/init.sql` | All | P2 | **Partly fixed 2026-10-18.** The script now creates `core`, the five roles and the grants, with a README. **It has not been run**: it needs a PostgreSQL superuser, and the local `diacare` user is not one. Still Open until someone runs it |
| G7 | `.env.example` lacks `RECOGNIZER`, `MODEL_PATH`, `MODEL_DEVICE`, `NUTRITION_TABLE_PATH` and the new auth variables | `.env.example` | Shared | P2 | **Fixed 2026-10-18.** All listed variables are in `.env.example`. Its `DATABASE_URL` now uses `postgresql+psycopg://` (the plain `postgresql://` form picks a driver the project does not use) |
| G8 | `*.db` is not gitignored; a stray `c1_local.db` sat in the C1 folder | `.gitignore`, `server/services/c1_food_nutrition/` | Shared; owner deletes the file | small PR | **Partly fixed 2026-10-18.** Confirmed untracked (0 bytes) and deleted. `.gitignore` itself was not changed, so `*.db` can still be created untracked again; that part of the gap is still Open |
| G9 | Two untracked files with mangled names (mistyped shell commands) in the repo root | repo root | Owner deletes them | manual | **Fixed 2026-10-18.** Found and deleted: `s -ExecutionPolicy RemoteSigned) ; (& d:ai-assisted-diabetes-management.venvScriptsActivate.ps1)` and `tatus --short` (both held only saved `git diff --stat` terminal output). The prototype HTML file at the root was kept, as it is not one of these two |
| G10 | `MealHistoryScreen` and `TodaySummaryScreen` cannot be reached after the uncommitted `main.dart` rewrite | `client/mobile_app/lib/main.dart` | Client (another session's work, do not touch) | P8 | Open |
| G11 | The questionnaire answers are never saved; the home dashboard is static (name, DHS 82, glucose 118 are hard-coded) | `client/mobile_app/lib/features/onboarding/`, `home/` | Client | P8, D7 | Open |
| G12 | The HTML prototype shows confidence percentages, against the CLAUDE.md rule | `DiaCare_AI_-_Interactive_Prototype_Component1-4.html` | C4 | Do not copy them into the app | Open |
| G13 | All six contracts are empty; the enum names in C1's `SKILL.md` draft differ from the code (C1 OPEN_ITEMS E) | `contracts/`, C1 `SKILL.md` | All | D8 | Open |
| G14 | The `carbohydrate_g` wording says "Total carbohydrate", but the value is available carbohydrate (fibre excluded) | C1 schema text, future contract | C1 | contract PR | Open |
| G15 | PyTorch is not in `uv.lock`; C1's real model runs in a hand-built environment | root `uv.lock`, C1 | C1, team | team PR | Open |
| G16 | CI never runs the PyTorch tests or any PostgreSQL test | `.github/workflows/ci.yml` | Shared | architecture section H | Open |
| G17 | MLflow and DVC are in the stack but nobody uses them | SETUP_PROMPT §3 | Team | decide to use or drop | Open |
| G18 | `CODEOWNERS` is fully commented out (GitHub usernames unknown) | `.github/CODEOWNERS` | All | add usernames | **Partly fixed 2026-10-18.** C1's username (`@kavithiS`) is known; its rule is uncommented in `.github/CODEOWNERS` and `docs/TEAM.md`. C2, C3 and C4 usernames are still not known, so their rules and the shared `/contracts/` and `/server/shared/` rules (which need all four) stay commented out. Still Open for C2–C4 |
| G19 | C3's data source differs by branch: BRFSS on `main`, DiaBD on `c3_lochana` | C3 docs | C3 | update the docs | Open |
| G20 | No readiness check, no database backups, no audit log | everywhere | All | P3, P10 | **Partly fixed 2026-10-18.** `core.audit_event` records login, refresh reuse, logout, registration and account deletion. Readiness checks and backups (P10) are still Open |
| G21 | C1's settings do not extend `diacare_shared.config.BaseServiceSettings` | C1 `config.py` | C1 | optional | Open |
| G22 | Only C3 has its own requirement documents (on its branch); C2 and C4 have no AGENTS, SKILL, ROADMAP or OPEN_ITEMS files | C2, C4 | C2, C4 | each owner | Open |
| G23 | No TAF or proposal document in the repository, so its requirements are known only through SETUP_PROMPT | `docs/` | Team | add a copy, or a summary approved by the supervisors | Open |
| G24 | The app's base URL is plain HTTP (`http://10.0.2.2:8000`) | `client/mobile_app/lib/core/config.dart` | Client | P9 (HTTPS for the UAT) | Open |
| G25 | No per-patient time zone is stored; "today" depends on the offset the client sends | C1 summary endpoint | C1, client | keep the client offset; revisit if notifications need it | Open |

## 3. Things checked and found absent (for completeness)

The following do not exist anywhere in the code, the client or the infrastructure:
- caching, apart from in-process `lru_cache`;
- background jobs or queues;
- file or object storage (images are dropped after analysis, by design);
- rate limiting;
- metrics or tracing;
- user, consent or audit tables;
- push notifications;
- Docker (removed by ADR 0003).

The architecture proposes only what the project needs:
- in-process rate limiting and `core` tables;
- no queue, no Redis and no object storage, which follows the stack rule and the owner's
  "never store images" answer.
