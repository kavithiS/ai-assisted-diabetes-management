# ADR 0006: Patient identity in a `core` schema, referenced by UUID in every service

- **Status:** Accepted by the team on 2026-10-18. Partly built: the `core` tables, `patient_id` in C1 and the delete fan-out exist; the per-schema database roles and moving C1 into `c1` wait for a PostgreSQL superuser (`infra/postgres/README.md`).
- **Date:** 2026-10-18
- **Component:** All (database layout); extends ADR 0001 (one schema per component)

## Decision

- A fifth schema, `core`, owned by the gateway, holds `app_user`, `refresh_token`, `consent`
  and `audit_event`.
- Every patient-owned table in `c1`–`c4` has `patient_id UUID NOT NULL`, indexed together with
  its time column. It is a **logical reference**: there is no foreign key across schemas,
  because a service cannot see `core`.
- Each schema gets its own login role (`diacare_core`, `diacare_c1` … `diacare_c4`) with rights
  on its own schema only and `search_path` set to it. The rule "a service never reads another
  service's schema" is then enforced by PostgreSQL.
- Each service runs its own Alembic migrations with `version_table_schema` set to its schema.
- **Deleting a patient** is a fan-out from the gateway:
  1. revoke the user's refresh tokens (no new sessions);
  2. call `DELETE /internal/v1/patients/{patient_id}` on each service that stores patient data
     (idempotent, 204; today only C1, set in `DELETE_FANOUT_SERVICES`);
  3. when all succeed, delete the user row and keep one audit event with no user id.

  If one fails, the answer is 502 and the account is unchanged, so the same call is repeated.
- Images are never stored. Only derived results are stored, each with `model_version`.

## Why

- There is no patient identity today, and C3 must keep several days of C1 and C2 results per
  patient (SETUP_PROMPT §1a).
- Cross-schema foreign keys would break the one-schema-per-component rule.
- Database roles turn a convention into a guarantee.

## Consequences

- `infra/postgres/init.sql` creates `core` and the five roles. Each service gets its own
  `DATABASE_URL`.
- C1's existing tables move from `public` into `c1`, and `meal` gains `patient_id`. Existing
  demo meals are assigned to a demo patient or deleted (C1 owner decides).
- SQLite tests keep working through `schema_translate_map`.
- Every service adds the internal delete endpoint.

Details: `docs/architecture/BACKEND_ARCHITECTURE.md` section B.
