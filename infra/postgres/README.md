# PostgreSQL setup

Status on 2026-10-18: **`init.sql` has not been run.** The local `diacare` database user is not a
superuser (it cannot create roles), and only the `public` schema exists. Until a superuser runs the
script, C1's tables stay in `public` and the gateway keeps its `core` tables in the `core` schema
that its own migration creates.

## What `init.sql` does

- Creates the schemas `core`, `c1`, `c2`, `c3`, `c4` (ADR 0006).
- Creates one login role per schema (`diacare_core`, `diacare_c1` ... `diacare_c4`) that can use
  its own schema only.
- Stops anyone creating tables in `public`.

## Run it once (as the PostgreSQL superuser)

```
psql -U postgres -p 5433 -d diacare -f infra/postgres/init.sql ^
     -v core_password=... -v c1_password=... -v c2_password=... -v c3_password=... -v c4_password=...
```

Use different passwords, and put the matching URLs in `.env`
(`postgresql+psycopg://diacare_c1:<password>@localhost:5433/diacare`, and so on).

## Not done yet (needs the step above)

- Moving C1's tables from `public` into the `c1` schema (a migration plus `MetaData(schema="c1")`).
  Do it only after the roles exist, and check it on a scratch database first.
- One `DATABASE_URL` per service in `scripts/dev.ps1`. Today every package reads the same `.env`.

## Tables the gateway creates itself

`GATEWAY_DATABASE_URL` points at the same database. From the repository root:

```
uv run alembic -c server/gateway/alembic.ini upgrade head
```

This creates the schema `core` (when the user may create schemas) with `app_user`, `refresh_token`,
`consent` and `audit_event`.
