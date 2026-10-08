# ADR 0003: Remove Docker

- **Status:** Accepted
- **Date:** 2026-10-08
- **Component:** All (supersedes the local-runtime part of ADR 0001, item 6)

## Decision

Docker is removed. Local development uses uvicorn (`uv run uvicorn`), a native PostgreSQL 16
install, and a local MLflow with a SQLite backend.

## Why

Docker Desktop is not installed on members' laptops, and the project does not need containers
to develop or demo.

## Consequences

- Each member installs PostgreSQL 16 and runs `infra/postgres/init.sql` once to create the
  `c1`–`c4` schemas.
- The full system (gateway and C1–C4) is started with `scripts/dev.ps1`.
- Deployment packaging can be revisited later if the supervisors require it.
