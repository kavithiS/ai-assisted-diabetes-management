-- Run once against a local PostgreSQL 16: psql -U diacare -d diacare -f infra/postgres/init.sql
-- One schema per component. A service never reads another service's schema.
CREATE SCHEMA IF NOT EXISTS c1;
CREATE SCHEMA IF NOT EXISTS c2;
CREATE SCHEMA IF NOT EXISTS c3;
CREATE SCHEMA IF NOT EXISTS c4;
