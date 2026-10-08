# DiaCare AI — Personalized AI Diabetes Care System for Sri Lankan Patients

SLIIT final-year research project **J26-IT-352** (TIM group, IT specialization).
Supervisor: Ms Chathurangika Kahandawaarachchi. Co-supervisor: Ms Aruni Premarathne.

> **Research prototype.** This system is not a diagnostic or clinically validated tool and
> must not be used for medical decisions. Its outputs are estimates and predictions.

## Components

| # | Component | Member | Service package | Port | Branch |
|---|---|---|---|---|---|
| C1 | Food Recognition & Nutritional Analysis | Thilakarathne K.S | [`c1_food_nutrition`](server/services/c1_food_nutrition/) | 8001 | `c1_kavithi` |
| C2 | Glycemic Prediction & Risk Forecasting | Jayamanna J.M.A.N.D | [`c2_glycemic_forecasting`](server/services/c2_glycemic_forecasting/) | 8002 | `c2_nethmi` |
| C3 | Multi-Factor Diabetic Risk Profiling & XAI | Rajapaksha R.M.L.I | [`c3_risk_xai`](server/services/c3_risk_xai/) | 8003 | `c3_lochana` |
| C4 | Mobile Platform & Foot Monitoring | G.P. Welikala | [`c4_foot_monitoring`](server/services/c4_foot_monitoring/) + [Flutter client](client/mobile_app/) | 8004 | `c4_guwindu` |

Each service README holds the component's TAF tasks, data, decisions and open items.
See [docs/TEAM.md](docs/TEAM.md) for the team and branch list.

## Architecture (client-server)

```
        CLIENT                                   SERVER
┌──────────────────────┐   HTTPS / JSON   ┌───────────────────────────┐
│ Flutter mobile app   │ ───────────────► │ API Gateway (FastAPI)     │
│ (patients)           │ ◄─────────────── │ routing · orchestration   │
└──────────────────────┘                  └─────────────┬─────────────┘
                                                        │ internal REST
                     ┌──────────────┬───────────────────┼───────────────┐
                     ▼              ▼                   ▼               ▼
              C1 Food &       C2 Glycemic         C3 Risk &       C4 Foot
              Nutrition       Forecasting         XAI / DHS       Monitoring
              :8001           :8002               :8003           :8004
                     └──────────────┴─────────┬─────────┴───────────────┘
                                              ▼
                              PostgreSQL (one schema per component)
                              MLflow (experiment tracking)
```

- The client talks **only** to the gateway (port 8000).
- Services do not call each other. The gateway orchestrates the data flow:
  meal image → C1 → C2 → C3, and foot image → C4.
- Each service owns its own Postgres schema (`c1`–`c4`) and never reads another's.
- Payloads between components are documented in [`contracts/`](contracts/README.md).

Decision record: [ADR 0001](docs/adr/0001-client-server-monorepo.md).

## Repository layout

```
client/mobile_app/      Flutter app (feature folders per component)
server/shared/          diacare_shared: config, logging, health helpers
server/gateway/         diacare_gateway: API gateway (port 8000)
server/services/c1_…c4_ FastAPI services, one per component
contracts/              Inter-component payload contracts
infra/                  Docker Compose and Postgres init
data/                   Gitignored, DVC-tracked data (c1/ … c4/)
docs/                   ADRs, team list, setup prompt
```

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/) (installs Python 3.11), Docker, and the Flutter
SDK (stable) for the client.

```bash
cp .env.example .env
uv sync                                   # one environment for every Python package
uv run pre-commit install                 # optional: run checks on commit

# Checks (same as CI)
uv run ruff check .
uv run ruff format --check .
uv run mypy server
uv run pytest

# Full stack: gateway, C1–C4, Postgres, MLflow
docker compose -f infra/docker-compose.yml up --build
curl http://localhost:8000/health

# Client
cd client/mobile_app && flutter pub get && flutter analyze && flutter test
```

| Service | Port |
|---|---|
| Gateway | 8000 |
| C1 / C2 / C3 / C4 | 8001 / 8002 / 8003 / 8004 |
| PostgreSQL | 5432 |
| MLflow | 5000 |

## Workflow

- GitHub flow: branch from `main` using `c<N>_<firstname>`, open a PR, and never push to `main`
  directly.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:` …).
- Changes to `contracts/`, `server/shared/`, the gateway or the client need a PR reviewed by
  every affected owner.
- Record decisions as ADRs in `docs/adr/` (`0003-…` onward).
- AI-assistant rules for every member: [CLAUDE.md](CLAUDE.md).

## Project-wide open items

These are not resolved yet. Component-specific open items are in each service README.

1. **Clinician & Admin Portal.** It appears as an output in the TAF architecture diagram, but no
   member owns it in the TAF. Its owner and technology need deciding. It is not scaffolded.
2. **Gateway and client ownership.** Proposed: C4. Needs confirmation.
3. **Authentication approach** for the gateway.
4. **Performance targets** (accuracy, latency) for every component. These are not in the TAF.
   They are to be set with the supervisors and are not TAF requirements.
5. **Ethical clearance.** The TAF plans the application in months 1–2. It is required before any
   primary patient data: C2 (no primary glucose data for research without clearance;
   development uses CGMacros), C3 questionnaires, C4 hospital images and UAT.

**Resolved:**

- C1 uses secondary datasets only ([ADR 0002](docs/adr/0002-c1-secondary-datasets.md)).
- C2 uses CGMacros for model development and validation (see the
  [C2 README](server/services/c2_glycemic_forecasting/README.md)).
- C3 starts with BRFSS 2015 (secondary); see the [C3 README](server/services/c3_risk_xai/README.md).
