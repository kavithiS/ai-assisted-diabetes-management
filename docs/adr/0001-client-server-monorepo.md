# ADR 0001: Client-server monorepo

- **Status:** Accepted (team decision recorded in `docs/SETUP_PROMPT.md`). Gateway and client
  ownership is proposed and still needs confirmation.
- **Date:** 2026-10-08

## Context

J26-IT-352 has four components (C1–C4) built by four members. The TAF specifies a Flutter client
(C4 task 1) and the integration of all AI microservices (C4 task 5). The data flow runs across
components: meal image → C1 → C2 → C3, and foot image → C4. Members need to work independently
on their own branches, while the integration points stay stable and reviewed.

An earlier proposal placed each component, with its own tooling and CI, under `components/`.
It is replaced by this layout.

## Decision

1. **One repository** with a client-server layout:
   - `client/mobile_app/`: the Flutter app. It talks only to the gateway.
   - `server/gateway/`: a FastAPI API gateway (port 8000) that routes and orchestrates.
   - `server/services/c<N>_*/`: one FastAPI service per component (ports 8001–8004).
   - `server/shared/`: common config, logging and health helpers.
2. **Services do not call each other.** The gateway orchestrates the data flow.
3. **PostgreSQL 16 with one schema per component** (`c1`–`c4`). A service never reads another
   service's schema.
4. **Contracts** in `contracts/` describe every payload between components. Changing one
   requires a PR reviewed by every affected member.
5. **Python tooling:** one uv workspace and one `uv.lock` (Python 3.11), with Ruff, mypy, pytest
   and pre-commit. Package names are unique and use the `src/` layout.
6. **Delivery:** Docker and Docker Compose for local runs, and GitHub Actions CI on PRs to `main`
   and on pushes to `main` and `c*_*` branches. *Superseded by
   [ADR 0003](0003-remove-docker.md) for local runtime.*
7. **Ownership:** each member owns `server/services/c<N>_*/` and `data/c<N>/`. `client/` and
   `server/gateway/` are proposed for C4, pending confirmation.

## Consequences

- One `uv sync` and one CI run check every Python package together. A dependency conflict
  between components shows up early and must be resolved jointly.
- Members add ML libraries on their own branches. The shared lock file means those additions
  are reviewed in PRs.
- The gateway is a single integration point and the owner of cross-component orchestration.
- Contract changes are slower (they need multi-member review), but integrations stay stable.
