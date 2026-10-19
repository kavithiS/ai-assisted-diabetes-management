# uv.lock PR note from C3 (database phase, 2026-10-19)

**For:** whoever owns the root `uv.lock`. **From:** C3.

C3 added three database packages to `server/services/c3_risk_xai/pyproject.toml` (its own
file), as agreed in the team stack (PostgreSQL 16, SQLAlchemy 2, Alembic):

| Package | Pinned version | Why |
|---|---|---|
| `sqlalchemy` | 2.1.5 | ORM / tables in the `c3` schema |
| `alembic` | 1.20.0 | Migrations for the `c3` schema (own version table `c3.alembic_version`) |
| `psycopg[binary]` | 3.3.6 | PostgreSQL driver (binary wheel, no compiler needed on Windows) |

`uv lock` result: **90 lines added, 0 removed**. New entries: alembic 1.20.0, mako 1.4.3
(needed by alembic), psycopg 3.3.6, psycopg-binary 3.3.6, sqlalchemy 2.1.5. No existing
package changed version.

CI impact: none expected. The Postgres test (`tests/test_storage.py`) skips itself when no
database is reachable, and every other C3 test uses an in-memory store
(`C3_PERSISTENCE=false` is set for the test session).
