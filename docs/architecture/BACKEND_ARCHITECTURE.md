# DiaCare AI backend and database architecture

- **Status:** Accepted by the team on 2026-10-18 (D1 to D3). Phases P0 to P5 are built (table below); P6 to P10 are not.
- **Date:** 2026-10-18
- **Author:** C1 (Thilakarathne K.S). Each part names its owner. Shared parts need the team's
  approval by PR.
- **Related:** ADR 0005 (login), ADR 0006 (patient identity and `core` schema), and
  `DECISIONS_AND_GAPS.md` (open decisions and missing items).

## Implementation status (2026-10-18)

| Phase | State | Notes |
|---|---|---|
| P0 docs | Done | This file, `DECISIONS_AND_GAPS.md`, ADR 0005 and 0006 |
| P1 shared foundation | Done | `server/shared`: error envelope, request id and body limit, JSON logs, internal-token check, engine helper. Wired into the gateway, C1 (error handler and request id) and C2 to C4 |
| P2 database foundation | **Partly** | `.env.example` and `infra/postgres/init.sql` written. **Not done**: the roles and schemas (needs a PostgreSQL superuser; `diacare` is not one), moving C1 into `c1`, one `DATABASE_URL` per service |
| P3 login in the gateway | Done | Register (closed by default), login, refresh with rotation and reuse detection, logout, `/me`, delete account, rate limit, command-line `create-user`, `core` tables migrated on the local database |
| P4 patient scoping in C1 | Done | `meal.patient_id`, every meal endpoint and `analyze` need the gateway's proof, `DELETE /internal/v1/patients/{id}`. Migration applied locally |
| P5 gateway hardening | Done | Shared HTTP client, bare `/api/v1/meals` path, identity headers set by the gateway only, per-route timeouts, 502/504 in the envelope, 11 MB body limit |
| P6 to P10 | Not started | Waiting for the contracts (D8), client login (P8), supervisors (D9) |

Checked on 2026-10-18: ruff, ruff format and mypy clean; pytest passed (counts in C1's `CHANGELOG.md`); a 21-step run against the real services and local PostgreSQL (login, isolation between two patients, forged headers, refresh reuse, rate limit, account deletion) passed, and its test data was removed afterwards.

## 0. Why this document exists

- C1 works: meal photo → foods → nutrition, plus meal history. C2, C3 and C4 are stubs that
  return 501.
- The gateway is a plain pass-through proxy.
- There is **no user or patient identity anywhere**: meals are global, and the app sends no
  token. The onboarding questionnaire answers are never saved.
- C1 defaults to SQLite and keeps its tables outside any schema.
- `contracts/` has no fields yet.

This document proposes how the backend and database should be built so that all four
components can store per-patient data safely.

### Owner answers (2026-10-18)

1. Scope: the whole project.
2. Login: our own JWT login in the gateway.
3. Hosting: local now (ADR 0003), one server later for C4's UAT.
4. Images: never stored.

### Facts this design is built on

- **Stack (SETUP_PROMPT §3):** Python 3.11, FastAPI, Pydantic v2, PostgreSQL 16, SQLAlchemy 2,
  Alembic, uv, ruff, mypy strict, pytest. "Do not add … extra databases", so no Redis and no
  MongoDB. Ask before adding a new framework. Native Postgres, no Docker (ADR 0003).
- **Architecture rules (SETUP_PROMPT §2):** the client talks only to the gateway. Services never
  call each other; the gateway orchestrates (meal → C1 → C2 → C3; foot → C4). Each service owns
  one schema (`c1`…`c4`) and never reads another's. C3 stores the C1 and C2 results it receives
  in `c3`.
- **Ethics and wording:** no primary patient data before ethical clearance. Never show raw model
  confidence to patients. Say "estimated" and "prediction", never "diagnosis".

## A. Target architecture

```
Flutter app ──HTTPS/JSON (Bearer access token)──► Gateway :8000  (owns schema core)
                                                     │  verifies the JWT, strips client identity headers,
                                                     │  adds X-Patient-Id, X-Internal-Token, X-Request-ID
             ┌───────────────┬───────────────┬───────┴───────┬───────────────┐
             ▼               ▼               ▼               ▼
         C1 :8001        C2 :8002        C3 :8003        C4 :8004
         schema c1       schema c2       schema c3       schema c4
             └───────────────┴──── one PostgreSQL 16 database "diacare" ─────┘
                       (one login role per schema; a role can use only its own schema)
```

- **Local:** every process binds to `127.0.0.1`. The emulator reaches the gateway at
  `10.0.2.2:8000`.
- **Later (phase P9):** one VM, an HTTPS reverse proxy in front of the gateway, services on
  localhost only.
- **Trust:** a service trusts `X-Patient-Id` only when `X-Internal-Token` matches its secret.
  The gateway always removes `Authorization`, `X-Patient-Id` and `X-Internal-Token` from client
  requests before forwarding.
- **Images** are never written to disk or the database. Only derived results are stored, each
  with `model_version`.

## B. Database architecture

### B1. Layout

- **One database, `diacare`.** Schemas: `core` (gateway: identity, consent, audit) and
  `c1`–`c4`. No tables in `public`.
- **One login role per schema:** `diacare_core`, `diacare_c1` … `diacare_c4`. Each role has
  `USAGE, CREATE` on its own schema only, and `search_path` set to it. So "never read another
  schema" is enforced by PostgreSQL.
- **Connection settings:** each service has its own `DATABASE_URL` with its own role.
- **Migrations:** each service has its own Alembic setup with `version_table_schema=<schema>`.
- **Patient link:** every patient-owned table has `patient_id UUID NOT NULL`, indexed with its
  time column.
  - There is no foreign key across schemas.
  - Integrity comes from the gateway (it sends only valid ids) and the fan-out delete (B4).
- **Conventions:**
  - Times are `timestamptz` in UTC. The client sends its UTC offset for "today" queries (C1
    already does).
  - Measurements are nullable: unknown is `NULL`, never 0.
  - Every model output row stores `model_version`.
  - Every schema uses C1's constraint naming convention
    (`server/services/c1_food_nutrition/src/c1_food_nutrition/db/base.py`).
  - Every table has a primary key and `created_at`.

### B2. `core` schema (gateway)

| Table | Columns | Notes |
|---|---|---|
| `app_user` | `id uuid pk`, `email text not null`, `password_hash text not null`, `display_name text null`, `role text not null` (one of `patient`, `researcher`, `clinician`, `admin`), `is_active bool default true`, `is_demo bool default false`, `created_at timestamptz`, `last_login_at timestamptz null` | Unique index on `lower(email)`. `is_demo` marks test accounts made before ethical clearance |
| `refresh_token` | `id uuid pk`, `user_id uuid fk → app_user on delete cascade`, `token_hash text unique not null` (sha256 hex), `issued_at`, `expires_at`, `revoked_at null`, `replaced_by uuid null`, `user_agent text null` | Rotated on every refresh. Reuse of a revoked token revokes all of that user's tokens |
| `consent` | `id uuid pk`, `user_id fk cascade`, `consent_version text`, `scope text` (for example `app_use`, `research_data`), `granted_at`, `withdrawn_at null` | Wording and versions come from the ethics application: [INFORMATION REQUIRED] |
| `audit_event` | `id bigint identity pk`, `user_id uuid null`, `event text` (`login_ok`, `login_failed`, `register`, `logout`, `token_reuse`, `account_deleted`, `data_export`), `occurred_at`, `request_id text`, `ip_hash text null` | No passwords, no health data, no raw IP (salted sha256) |
| `device_push_token` | added only after the push provider is chosen | Open decision D10 |

### B3. Service schemas (proposals; each owner confirms their own)

**`c1`** (owner C1; the tables exist, the changes come in P2 and P4)
- `nutrition_source`, `food`, `food_nutrient`: unchanged, moved into schema `c1`.
- `meal`: add `patient_id uuid not null` and the index `ix_meal_patient_eaten (patient_id,
  eaten_at desc)`.
- `meal_item`: unchanged. It is scoped through its meal.
- Never stored: images, raw model confidence.

**`c2`** (owner C2)
- `glucose_reading`: `id`, `patient_id`, `measured_at`, `value`, `unit`, `context` (`pre_meal`,
  `post_meal`, `fasting`, `random`), `source` (`manual`, `glucometer`, `cgm`), `meal_ref` null.
- `glycemic_forecast`: `id`, `patient_id`, `meal_ref`, `created_at`, `model_version`,
  `horizon_minutes` (240), `points jsonb` (time and value), `peak_value`, `time_to_peak_min`,
  `risk_score`, `risk_category`.
- `meal_ref` is the C1 meal id passed by the gateway. It is not a foreign key.

**`c3`** (owner C3)
- `risk_profile`: one row per submission (versioned). Fields come from the
  `patient_risk_profile` contract: BP, activity, smoking, medication, cholesterol, kidney,
  liver, weight change.
- `received_meal_event`: the C1 totals and the C2 forecast summary, with `meal_ref` and
  `eaten_at`. This is the "stores the C1/C2 results it receives" rule.
- `risk_assessment`: `patient_id`, `created_at`, `model_version`, `dhs` (0–100), `risk_band`,
  `explanation jsonb`, `inputs_snapshot jsonb`.
- No raw probability goes to patients.

**`c4`** (owner C4)
- `foot_screening`: `id`, `patient_id`, `captured_at`, `foot_side` (`left`, `right`),
  `abnormality_class`, `risk_level`, `model_version`, `recommendation_code`. No image.
- `notification`: `id`, `patient_id`, `kind`, `created_at`, `sent_at`, `read_at`. Added only
  when the alerts feature is designed.

**Onboarding questionnaire (four modules).** Proposed default (decision D7): each module goes to
the service that uses it, keyed by `patient_id`. Diet goes to C1 (only if C1 needs it), glucose
and medication to C2, lifestyle to C3 `risk_profile`, and foot to C4. The gateway offers one
`POST /api/v1/onboarding` endpoint and splits the answers.

### B4. Deleting a patient

`DELETE /api/v1/me` on the gateway:
1. Revoke the user's refresh tokens, so no new session can start.
2. Call `DELETE /internal/v1/patients/{patient_id}` on each service listed in the gateway
   setting `DELETE_FANOUT_SERVICES` (today `c1`; add `c2`–`c4` when they store patient data).
   Each call deletes every row with that id and returns 204, even when nothing was found.
3. When all succeed, delete the `app_user` row, its tokens and consents, and write one
   `audit_event` with no user id.

If a service fails, return 502 and leave the account as it is, so the same call can be
repeated. (An earlier draft switched the account off first; that would have stopped the
patient from retrying, because the login no longer worked.)

## C. Authentication (ADR 0005)

**New libraries.** These need the team's approval (D3), and the root `uv.lock` changes.
- Tokens and passwords: `pyjwt` and `argon2-cffi`.
- Database access in the gateway: `sqlalchemy`, `alembic` and `psycopg[binary]` (already used
  by C1).

**Gateway settings**

| Setting | Default | Note |
|---|---|---|
| `JWT_SECRET` | none, required | at least 32 bytes |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_MINUTES` | 15 | |
| `REFRESH_TOKEN_DAYS` | 30 | |
| `GATEWAY_DATABASE_URL` | none, required | role `diacare_core` |
| `INTERNAL_TOKEN` | none, required | the same value in every service |
| `REGISTRATION_ENABLED` | `false` | no self sign-up before ethical clearance |
| `AUTH_REQUIRED` | `true` | |
| `DEMO_PATIENT_ID` | none | used only when `AUTH_REQUIRED=false`, until the client has login |

**Tokens**
- **Access token claims:** `sub` (user UUID), `role`, `iat`, `exp`, `jti`, `typ="access"`.
- **Refresh token:** `secrets.token_urlsafe(32)`. Only its sha256 is stored.

**Endpoints** (`server/gateway/src/diacare_gateway/routes/auth.py`)

| Method and path | Body | Result |
|---|---|---|
| `POST /api/v1/auth/register` | `{email, password, display_name?, consent_version, accept: true}` | 201 `{user_id}`; 403 `REGISTRATION_CLOSED`; 409 `EMAIL_TAKEN` |
| `POST /api/v1/auth/login` | `{email, password}` | 200 `{access_token, refresh_token, token_type: "bearer", expires_in}`; 401 `INVALID_CREDENTIALS`, the same message whether or not the email exists |
| `POST /api/v1/auth/refresh` | `{refresh_token}` | 200 with a new pair; 401 if expired, revoked or reused |
| `POST /api/v1/auth/logout` | `{refresh_token}` | 204 |
| `GET /api/v1/me` | none | `{user_id, email, display_name, role, created_at}` |
| `DELETE /api/v1/me` | none | 204 (see B4) |

**Rules**
- **Passwords:** 10 to 128 characters, hashed with Argon2id (library defaults).
- **Rate limit:** in-process. After 5 failed logins in 15 minutes for the same lowercase email
  and client IP, return 429 `TOO_MANY_ATTEMPTS`.
- **Demo accounts:** `uv run python -m diacare_gateway.cli create-user --email … --demo`.
- **Which routes need a token:** the meals, foods, glucose, risk, foot and onboarding routers.
  `/health` and `/api/v1/auth/*` are public.

## D. Gateway responsibilities

1. **Authenticate:** verify the JWT, then set `X-Patient-Id`.
2. **Forward:** use one shared `httpx.AsyncClient` created at startup, with connection limits.
   Timeouts: C1 analyze 65 s, everything else 15 s.
3. **Request id:** create `X-Request-ID` when the client did not send one.
4. **Errors:** return upstream failures in the shared error envelope (502
   `UPSTREAM_UNAVAILABLE`, 504 `UPSTREAM_TIMEOUT`).
5. **Orchestrate:** meal saving (P6) and patient deletion (B4).
6. **Size limit:** cap request bodies at 11 MB, a little above C1's 10 MiB.
7. **CORS:** none needed, because there is no web client.

## E. Performance

The TAF sets no targets (SETUP_PROMPT §10.4). **Measure first, then agree targets with the
supervisors** (D11).

Known numbers:
- about 2.5 s per analyze call through the gateway (C1 CHANGELOG 2026-10-17);
- about 15 ms model time on CPU;
- about 10 s model load at startup.

What to do:
- **C1 model memory:** run C1 with one uvicorn worker, because every worker loads its own copy
  of the model. Inference already runs in a worker thread. Do not use `--reload` outside
  development.
- **Gateway connections:** a shared `httpx` client avoids a new TCP connection on every call.
- **Database:**
  - pool settings per service: `pool_size=5`, `max_overflow=5`, `pool_pre_ping=True`. That is
    at most 50 connections, under Postgres's default limit of 100;
  - index every list query on `(patient_id, time desc)`;
  - always paginate, and cap `limit` at 100.
- **Payloads:** the app already shrinks photos to 1280 px before upload. Responses carry no
  images.
- **Caching:** in-process only (`lru_cache` for the food table and settings, as now). No Redis.
- **Meal chain:** the steps run one after another (C1 save → C2 → C3), each with its own
  timeout. If C2 or C3 fails, the saved meal is still returned, with
  `forecast_status: "unavailable"`.
- **Measurement:** the gateway logs `duration_ms` for every upstream call. A script in
  `scripts/` times 20 analyze calls and reports the median and 95th percentile.

## F. Security and privacy

- **Transport:** plain HTTP is acceptable locally (test data only). The UAT server **must** use
  HTTPS; Android release builds block cleartext by default.
- **Secrets:** `.env` stays gitignored, and `.env.example` lists every variable with a
  placeholder. Generate `JWT_SECRET` and `INTERNAL_TOKEN` with
  `python -c "import secrets;print(secrets.token_urlsafe(48))"`.
- **Logs:** never log passwords, tokens, emails, glucose values or other health values. Log only
  `request_id`, `patient_id` and timings.
- **Least privilege:** one database role per schema, and services listen on 127.0.0.1.
- **Ethics:** registration stays closed and only demo accounts exist until ethical clearance.
  Consent records exist before any real data is stored.
- **Law:** the Sri Lanka Personal Data Protection Act No. 9 of 2022 may apply to the UAT.
  Whether it applies, how long data is kept and where it is stored must be confirmed with the
  supervisors and the ethics committee (D12). Do not claim compliance.
- **Patient-facing output:** no raw confidence. Any confidence field in a contract is marked
  `research_only`.

## G. Reliability and operations

- **Health checks:** `/health` stays a liveness check. A new `/ready` checks the database
  (`SELECT 1`) and, in C1, that the model is loaded. The gateway's health response reports
  readiness per service.
- **Backups:** a daily `pg_dump -Fc diacare` to a folder outside the repo, keeping 7 copies
  (`scripts/backup_db.ps1`). Test a restore once into a scratch database.
- **Migrations:** run `alembic upgrade head` from the **repo root**, so the right `.env` is read.
  Running it from the service folder once used SQLite by mistake.
- **Logs:** every service writes JSON logs (C1's format, moved into `server/shared`) with the
  `request_id` the gateway creates, so one request can be followed across services.

## H. Tests and CI

- **Unit tests** stay on SQLite. SQLite has no schemas, so the shared engine helper sets
  `schema_translate_map={"<schema>": None}` for SQLite URLs.
- **Postgres tests:** marker `@pytest.mark.postgres`, skipped without `TEST_POSTGRES_URL`. They
  run the migrations and check role isolation. Proposed CI change (shared file, needs approval):
  a `postgres:16` service container in `.github/workflows/ci.yml`.
- **Auth tests:**
  - register when closed and when open;
  - login success and failure;
  - the rate limit;
  - refresh rotation and reuse detection;
  - an expired token;
  - a client-sent `X-Patient-Id` being stripped;
  - a service rejecting a missing or wrong internal token.

## Implementation phases

Do one phase at a time. Never commit or push; the owner does that. Put no AI or tool attribution
anywhere. Run the checks in "Verification" after every phase. Do not start a phase until its
approval is confirmed.

| Phase | What | Owner | Approval needed from |
|---|---|---|---|
| P0 | These docs | C1 | Team review by PR |
| P1 | Shared foundation (`server/shared`) | All four | All four |
| P2 | Database foundation: roles, schemas, Alembic per schema | Each owner and `infra/` | All four |
| P3 | Identity and auth in the gateway | Gateway owner (proposed C4) | All four and supervisors |
| P4 | Patient scoping in C1 | C1 | C1 |
| P5 | Gateway hardening | Gateway owner | Gateway owner |
| P6 | Meal chain C1 → C2 → C3 | Gateway, C2, C3 | After the contracts are approved |
| P7 | C2, C3 and C4 schemas | Each owner | Each owner |
| P8 | Client login and tokens | C4 | C4, and a new Flutter package |
| P9 | One server for UAT | Gateway owner | Supervisors |
| P10 | Operations: readiness, backups, latency script | All | All |

### Code to reuse (C1, under `server/services/c1_food_nutrition/src/c1_food_nutrition/`)

| Pattern | File |
|---|---|
| Settings | `config.py` |
| Error envelope | `core/errors.py`, `api/exception_handlers.py` |
| JSON logs and request id | `core/logging.py` |
| Engine and session | `db/session.py`, `api/deps.py` (`get_session`) |
| Models and naming convention | `db/base.py`, `db/models/meal.py` |
| Alembic | `../../alembic.ini`, `db/migrations/env.py` |
| Migration test | `../../tests/unit/test_migrations.py` |

### P1: Shared foundation (`server/shared/src/diacare_shared/`)

1. `errors.py`: a generic copy of C1's envelope.
   - `ErrorCode` values: `VALIDATION_ERROR`, `NOT_FOUND`, `UNAUTHORIZED`, `FORBIDDEN`,
     `UPSTREAM_UNAVAILABLE`, `UPSTREAM_TIMEOUT`, `INTERNAL_ERROR`, `TOO_MANY_ATTEMPTS`.
   - An `AppError` base class and `install_exception_handlers(app)`.
   - C1 keeps its own codes.
2. `request_context.py`: `RequestContextMiddleware`. It reads or creates `X-Request-ID` and logs
   one line with `duration_ms`, as in C1.
3. `logging.py`: add C1's JSON formatter, and a `configure_logging(level, json=True)` parameter.
4. `internal_auth.py`: a FastAPI dependency `require_patient_id(request) -> uuid.UUID`.
   - Compare `X-Internal-Token` with `settings.internal_token` using `hmac.compare_digest`.
   - Parse `X-Patient-Id` as a UUID.
   - Raise `AppError(UNAUTHORIZED)` otherwise.
5. `db.py`: `make_engine(url, schema)`, with the E pool settings and the SQLite
   `schema_translate_map`, and `make_session_factory(engine)`.
6. `config.py`: add `internal_token: str | None = None`.
7. Tests in `server/shared/tests/`:
   - the envelope shape;
   - the request id echoed back;
   - internal auth: success, missing token, wrong token and bad UUID.
8. In the C2, C3 and C4 `main.py` files, call `install_exception_handlers`, add the middleware
   and switch on JSON logging.

### P2: Database foundation

1. Rewrite `infra/postgres/init.sql` to use psql variables for passwords:
   ```sql
   CREATE SCHEMA IF NOT EXISTS core;  -- and c1, c2, c3, c4
   REVOKE ALL ON SCHEMA public FROM PUBLIC;
   CREATE ROLE diacare_c1 LOGIN PASSWORD :'c1_password';   -- same for core, c2, c3, c4
   GRANT USAGE, CREATE ON SCHEMA c1 TO diacare_c1;
   ALTER ROLE diacare_c1 SET search_path = c1;
   ```
   Add `infra/postgres/README.md` with the exact command, run as the `postgres` superuser:
   `psql -U postgres -d diacare -v core_password=... -v c1_password=... -f infra/postgres/init.sql`.
2. `.env.example`:
   - add `CORE_DATABASE_URL` and `C1_DATABASE_URL` … `C4_DATABASE_URL`, each
     `postgresql+psycopg://diacare_<schema>:change-me@localhost:5432/diacare`;
   - add `INTERNAL_TOKEN`, `JWT_SECRET`, `RECOGNIZER`, `MODEL_PATH`, `MODEL_DEVICE` and
     `NUTRITION_TABLE_PATH`.

   In `scripts/dev.ps1`, set `DATABASE_URL` from the matching variable in each service's window.
3. Move C1 into its schema:
   1. In `db/base.py`, set `MetaData(schema="c1", naming_convention=...)`.
   2. Add a new migration `db/migrations/versions/20261020_<rev>_move_to_c1_schema.py`. On
      Postgres it runs `ALTER TABLE public.<t> SET SCHEMA c1` for each of the five tables that
      exist in `public`. On SQLite it does nothing.
   3. In `env.py`, for Postgres only, set `version_table_schema="c1"` and `include_schemas=True`.
   4. Add `schema_translate_map={"c1": None}` for SQLite in `db/session.py`, or use the shared
      `make_engine`.
   5. `tests/unit/test_migrations.py` must still upgrade and downgrade on SQLite.
4. Keep C1's SQLite default for tests. Document in the C1 README that development uses Postgres
   through `C1_DATABASE_URL`.

### P3: Identity and auth in the gateway

1. In `server/gateway/pyproject.toml`, add `sqlalchemy>=2.1`, `alembic>=1.20`,
   `psycopg[binary]`, `pyjwt`, `argon2-cffi` and `diacare-shared`. Run `uv lock` and `uv sync`
   only after D3 is approved.
2. Under `server/gateway/src/diacare_gateway/`, add:
   - `db/base.py`: C1's naming convention, with `MetaData(schema="core")`.
   - `db/models.py`: the B2 tables. Generate UUIDs in Python with `default=uuid.uuid4`, so the
     models work on SQLite too.
   - `db/migrations/`, plus `server/gateway/alembic.ini`. The first revision creates the `core`
     tables.
   - `auth/passwords.py`: `hash_password` and `verify_password` (argon2).
   - `auth/tokens.py`: `create_access_token`, `decode_access_token`, and `new_refresh_token()`,
     which returns `(plain, sha256_hex)`.
   - `auth/rate_limit.py`: a `dict[str, deque[float]]` behind a `threading.Lock`.
   - `auth/deps.py`: `current_user`. It reads `Authorization: Bearer`, decodes the token and
     loads an active user. When `AUTH_REQUIRED=false`, it returns `DEMO_PATIENT_ID`.
   - `routes/auth.py`: the section C endpoints.
   - `cli.py`: `create-user --email --display-name --demo`, which asks for the password.
3. In `config.py`, add the section C settings.
4. In `main.py`, create the engine and session factory at startup, include the auth router, and
   install the shared envelope and middleware.
5. Add `server/gateway/tests/test_auth.py`, running on SQLite, covering every auth case in
   section H.

### P4: Patient scoping in C1

1. `db/models/meal.py`:
   - add `patient_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)`;
   - add `Index("ix_meal_patient_eaten", "patient_id", desc("eaten_at"))`.
2. Add a migration `..._meal_patient_id.py` that:
   1. adds the column as nullable;
   2. assigns the existing demo rows to `DEMO_PATIENT_ID`, or deletes them (decision D4);
   3. sets the column to NOT NULL;
   4. creates the index.
3. `api/history.py`: add `patient_id: UUID = Depends(require_patient_id)` to every meal endpoint.
   - List and summary filter on `Meal.patient_id`.
   - Get and delete also filter on it, and return 404 for another patient's meal.
   - Create stores the patient id.
   - `/v1/foods` needs no patient.
   - `/v1/meals/analyze` requires the dependency but stores nothing.
4. Add `api/internal.py`: `DELETE /internal/v1/patients/{patient_id}`, protected by the internal
   token only. It deletes that patient's meals (their items cascade) and returns 204.
5. Tests:
   - patient A cannot list, get or delete patient B's meals;
   - a missing header gives 401;
   - the internal delete removes only that patient's rows;
   - the migration test covers the new revision.
6. Update C1's `docs/CHANGELOG.md` and `docs/CONTEXT.md` section 5.

### P5: Gateway hardening (`server/gateway/src/diacare_gateway/`)

1. At startup, create one `httpx.AsyncClient(limits=httpx.Limits(max_connections=50))` and keep
   it on `app.state`. `get_http_client` returns it.
2. `routes/meals.py`: add the bare-path route the way `routes/foods.py` does. Add a test that
   `GET /api/v1/meals` and `POST /api/v1/meals` reach C1.
3. `forward()`:
   - drop the incoming `authorization`, `x-patient-id` and `x-internal-token` headers;
   - add `X-Patient-Id`, `X-Internal-Token` and `X-Request-ID`;
   - give each route its own timeout;
   - map `httpx.TimeoutException` to 504 `UPSTREAM_TIMEOUT` and other `httpx.RequestError`s to
     502 `UPSTREAM_UNAVAILABLE`, in envelope form.
4. Add an 11 MB body-size limit, the same idea as C1's `BodySizeLimitMiddleware`.
5. Tests: header stripping, 504 in envelope form, and the bare-path routes.

### P6 to P10 (detailed after their decisions)

- **P6, meal chain (after D5 and D8).** A gateway endpoint `POST /api/v1/meals`:
  1. C1 saves the meal;
  2. C2 `POST /v1/glucose/forecast` receives the `meal_nutrition` and the optional pre-meal
     glucose;
  3. C3 `POST /v1/risk/meal-events` receives both results;
  4. the gateway returns `{meal, forecast | null, forecast_status}`.

  A C2 or C3 failure never undoes the saved meal.
- **P7, C2–C4 schemas.** Each owner adds their B3 models, Alembic with their schema,
  `require_patient_id` on their endpoints and the internal delete endpoint.
- **P8, client (C4).** Coordinate first, because another session has uncommitted client work.
  - login and register screens;
  - token storage with `flutter_secure_storage` (new package, needs approval);
  - an `Authorization` header in `ApiClient`, and refresh on 401;
  - logout;
  - the questionnaire submitted to `POST /api/v1/onboarding`.
- **P9, UAT server (D9).** One VM with Postgres 16. Services run as system services bound to
  localhost, behind an HTTPS reverse proxy for the gateway. The app sets `API_BASE_URL` with
  `--dart-define`.
- **P10, operations.** `/ready` endpoints, `scripts/backup_db.ps1` and one restore test, and the
  latency script from section E.

## Verification (after every phase)

From the repo root:
```
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy server
uv run pytest
```
For client changes: `cd client/mobile_app ; flutter analyze ; flutter test`. Report the exact
pass and skip counts.

**P2**
1. Run `init.sql` on a scratch database.
2. Connect as `diacare_c1`. `SELECT` on any `c2` table must fail with "permission denied".
3. Run `alembic upgrade head` for C1 from the repo root.
4. `\dt c1.*` must show the five tables.

**P3:** start the gateway with `AUTH_REQUIRED=true` and create a demo user with the CLI. Then,
with `curl.exe`:
1. log in;
2. `GET /api/v1/me` with the token returns 200, and without it 401;
3. refresh, then reuse the old refresh token: 401;
4. make 6 bad logins: the last one gets 429.

**P4 and P5:** with two demo users:
- a meal saved as A does not appear in B's list, and B's delete returns 404;
- a client-sent `X-Patient-Id` is ignored;
- `GET /api/v1/meals` through the gateway returns 200.

**End to end (after P8):** on the Android emulator, scan a meal, save it and see it listed.
Before P8, use `AUTH_REQUIRED=false` with `DEMO_PATIENT_ID`.

Always say what was not checked: Postgres in CI, the UAT server, real devices.
