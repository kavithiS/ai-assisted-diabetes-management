-- Runs once when the Postgres volume is first created.
-- One schema per component. A service never reads another service's schema.
CREATE SCHEMA IF NOT EXISTS c1;
CREATE SCHEMA IF NOT EXISTS c2;
CREATE SCHEMA IF NOT EXISTS c3;
CREATE SCHEMA IF NOT EXISTS c4;
