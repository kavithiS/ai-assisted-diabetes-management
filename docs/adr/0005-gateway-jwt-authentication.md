# ADR 0005: Patient login with JWT tokens issued by the gateway

- **Status:** Accepted by the team on 2026-10-18. Built in phases P1, P3 and P5.
- **Date:** 2026-10-18
- **Component:** Gateway and client (owner C4, decided 2026-10-18); affects C1–C4
- **Context:** SETUP_PROMPT §10.3 listed the authentication approach as open.

## Decision

The gateway owns login. Patients sign in with an email and password. The gateway stores users
in its own `core` schema (ADR 0006), and issues a short-lived access token (JWT, HS256, 15
minutes) and a refresh token (random, 30 days, rotated on every use). Only the refresh token's
hash is stored.

For every authenticated request the gateway:

- removes any `Authorization`, `X-Patient-Id` and `X-Internal-Token` header sent by the client;
- adds `X-Patient-Id` (the user's UUID), `X-Internal-Token` (a shared secret) and `X-Request-ID`.

A service accepts `X-Patient-Id` only when `X-Internal-Token` matches its configured secret.
Services do not handle passwords or tokens.

Self-registration is off by default (`REGISTRATION_ENABLED=false`), because no primary patient
data may be collected before ethical clearance. Until then, demo accounts (`is_demo=true`) are
created with a command-line tool.

## Why

- No identity exists anywhere today: meals are global and the app sends no token. The
  prototype shows "I already have an account" and "Logout".
- This keeps the stack rule (no new framework, no outside login service) and keeps one place
  that knows about users.
- Services stay simple: they receive a trusted patient id and never see credentials.

## Consequences

- New libraries in the gateway: `pyjwt`, `argon2-cffi` (password hashing), and `sqlalchemy`,
  `alembic`, `psycopg[binary]` for the `core` schema. These change the shared `uv.lock`.
- New settings: `JWT_SECRET`, `ACCESS_TOKEN_MINUTES`, `REFRESH_TOKEN_DAYS`,
  `GATEWAY_DATABASE_URL`, `INTERNAL_TOKEN`, `REGISTRATION_ENABLED`, `AUTH_REQUIRED`,
  `DEMO_PATIENT_ID`.
- Login failures are rate-limited in-process (5 per 15 minutes per email and IP). This is
  enough for a single gateway process.
- The client needs login screens, secure token storage (a new Flutter package, to be approved)
  and refresh-on-401.
- Until the client has login, `AUTH_REQUIRED=false` with a fixed `DEMO_PATIENT_ID` keeps the
  current app working.
- Services must listen on `127.0.0.1` only, so nothing but the gateway can reach them.

Details: `docs/architecture/BACKEND_ARCHITECTURE.md` section C.
