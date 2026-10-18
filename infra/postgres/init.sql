-- One-time database setup, run by the PostgreSQL superuser (see infra/postgres/README.md).
--   psql -U postgres -d diacare -f infra/postgres/init.sql \
--        -v core_password=... -v c1_password=... -v c2_password=... -v c3_password=... -v c4_password=...
--
-- One schema per component plus `core` for the gateway (ADR 0006). Each schema has its own
-- login role that can use that schema only, so "a service never reads another service's
-- schema" is enforced by PostgreSQL, not only by convention.

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS c1;
CREATE SCHEMA IF NOT EXISTS c2;
CREATE SCHEMA IF NOT EXISTS c3;
CREATE SCHEMA IF NOT EXISTS c4;

-- Nobody creates tables in `public` by accident.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

CREATE ROLE diacare_core LOGIN PASSWORD :'core_password';
CREATE ROLE diacare_c1   LOGIN PASSWORD :'c1_password';
CREATE ROLE diacare_c2   LOGIN PASSWORD :'c2_password';
CREATE ROLE diacare_c3   LOGIN PASSWORD :'c3_password';
CREATE ROLE diacare_c4   LOGIN PASSWORD :'c4_password';

GRANT USAGE, CREATE ON SCHEMA core TO diacare_core;
GRANT USAGE, CREATE ON SCHEMA c1   TO diacare_c1;
GRANT USAGE, CREATE ON SCHEMA c2   TO diacare_c2;
GRANT USAGE, CREATE ON SCHEMA c3   TO diacare_c3;
GRANT USAGE, CREATE ON SCHEMA c4   TO diacare_c4;

-- Unqualified table names resolve to the role's own schema.
ALTER ROLE diacare_core SET search_path = core;
ALTER ROLE diacare_c1   SET search_path = c1;
ALTER ROLE diacare_c2   SET search_path = c2;
ALTER ROLE diacare_c3   SET search_path = c3;
ALTER ROLE diacare_c4   SET search_path = c4;
