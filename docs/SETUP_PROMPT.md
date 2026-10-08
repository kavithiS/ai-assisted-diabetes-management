# DiaCare AI — Repository Setup Prompt (J26-IT-352)

You are setting up the shared monorepo for a SLIIT final-year research project with four members. Your job is to create a clean **client-server scaffold** on which every member can create their own branch. Follow the steps in order. When something is marked `[INFORMATION REQUIRED]`, stop and ask the user. Do not guess.

---

## 0. Ground rules

1. The source of truth, in priority order: (1) the official TAF (J26-IT-352), (2) supervisor and team decisions recorded in this prompt or in `docs/adr/`, (3) the rest of this prompt.
2. This is a research prototype. Never make clinical diagnosis or validation claims, and never invent data, results, metrics, participants or citations.
3. **Scaffold only.** Do not write ML models, training code, datasets or business logic. Each service gets a health endpoint and one placeholder route that returns `501 Not Implemented`.
4. Create **only** the files and folders listed in section 4. Add no extras.
5. Never delete, move or overwrite existing files without first listing them and getting the user's approval.
6. Never push to `main` directly and never force-push.
7. Items marked `[OWNER TO CONFIRM]` belong to that member. Record them as open items in that service's README; never decide them on the member's behalf.

---

## 1. Project facts (from the TAF)

**Topic:** Personalized AI Diabetes Care System for Sri Lankan Patients. TIM group, IT specialization.
**Supervisor:** Ms Chathurangika Kahandawaarachchi. **Co-supervisor:** Ms Aruni Premarathne.

| # | Component | Member | Reg No | Service package | Port |
|---|---|---|---|---|---|
| C1 | Food Recognition & Nutritional Analysis | Thilakarathne K.S | IT23295742 | `c1_food_nutrition` | 8001 |
| C2 | Glycemic Prediction & Risk Forecasting | Jayamanna J.M.A.N.D | IT23319042 | `c2_glycemic_forecasting` | 8002 |
| C3 | Multi-Factor Diabetic Risk Profiling & XAI | Rajapaksha R.M.L.I | IT23315846 | `c3_risk_xai` | 8003 |
| C4 | Mobile Platform & Foot Monitoring | G.P. Welikala | IT23327580 | `c4_foot_monitoring` + Flutter client | 8004 |

---

## 1a. Component details

Each component below uses the same layout: TAF tasks, novelty, data, inputs and outputs, decisions, and open items. Copy each component's subsection into its service `README.md`.

### C1 — Food Recognition & Nutritional Analysis (Thilakarathne K.S)

**TAF tasks:**

1. Food image data. The TAF wording was "collect & annotate"; this is **replaced by secondary datasets** (see Decisions).
2. Fine-tune EfficientNetV2/MobileNetV3 via transfer learning.
3. Multi-label classification for mixed-dish meals (rice and curry platters).
4. Portion-size estimation by reference-object calibration.
5. Nutritional analysis API linked to the MRI Sri Lanka Food Composition DB.

**Novelty (TAF):**

- Multi-label CNN for complex mixed-dish recognition.
- Hybrid nutritional knowledge base merging MRI Sri Lanka with USDA values.
- *The "first large-scale annotated Sri Lankan food dataset" claim no longer applies. Do not repeat it anywhere.*

**Data:**

| Purpose | Source | Role |
|---|---|---|
| Food images | Food-101 | Primary |
| Food images | UEC-FOOD-256, VIREO Food-172 | Optional |
| Nutrition | USDA FoodData Central (mapped to the MRI 36-column schema) | Primary |
| Nutrition | MRI Sri Lanka Food Composition DB | Sri Lankan values. The current CSV export is corrupted: the importer must reject a header of `food_100me` |

**Inputs and outputs:**

- Input: a meal image, an optional `reference_object`, and a meal timestamp.
- Output: identified foods, estimated portions and nutrition totals (carbohydrate, protein, fat, fibre, energy), with the data source recorded per value.
- Consumers: C2 and C3, through the gateway.

**Decisions:**

- Secondary datasets only; no new image collection. The TAF supervisor comment "Data sets are available" supports this. It is recorded in ADR 0002.
- No ethical clearance is needed for C1, because no primary images are collected.

**Open items:**

- The final `reference_object` format (this blocks C4's camera screen).
- The MRI CSV corruption fix.

### C2 — Glycemic Prediction & Risk Forecasting (Jayamanna J.M.A.N.D)

**TAF tasks:**

1. Compile a Sri Lankan meal glycemic index reference dataset.
2. Engineer features from the nutritional profile, patient history and meal timing.
3. Train LSTM/GRU time-series models for 4-hour glucose forecasting.
4. Build an XGBoost dietary risk classifier and a composite risk-score algorithm.
5. Validate predictions against clinical glucose reference data.

**Novelty (TAF):**

- Personalised glucose trajectory forecasting using locally validated Sri Lankan meal GI profiles.
- A dynamic dietary risk score integrating meal timing, carbohydrate load and cumulative daily intake.

**Data:**

| Purpose | Source | Status |
|---|---|---|
| Glucose time-series and meal data for model development and validation | CGMacros | Confirmed C2 dataset |
| GI references | University of Sri Jayewardenepura GI references | Named in the TAF |
| Meal nutrition | C1 output | Via contract |

**Inputs and outputs:**

- Runtime inputs:
  - C1 meal nutrition
  - Meal timing
  - Patient-provided current/pre-meal blood glucose measurement
- Training inputs:
  - CGMacros meal/nutrition data
  - Pre-meal glucose
  - Post-meal glucose observations
  - Other approved contextual features where available
- Outputs:
  - A 4-hour predicted post-meal glucose trajectory
  - Measurable trajectory characteristics
  - A research-defined dietary risk score/category
  - Model/version metadata
- Consumers: C3 and the client, through the gateway.

**Decisions:**

- CGMacros is the confirmed dataset for C2 model development and validation.
- ShanghaiT2DM is NOT used as an independent external validation dataset.
- The runtime workflow requires the patient to provide their current/pre-meal glucose measurement before the meal.
- The current-glucose workflow is a supervisor-approved implementation decision and should not be described as a TAF requirement.
- No primary patient glucose data may be collected for research purposes without ethical clearance.
- CGMacros meal events should be aligned with glucose measurements to construct meal-centred prediction samples.
- Participant-aware train/validation/test splitting must be used to reduce participant-level data leakage.
- The XGBoost output is a research-defined dietary/postprandial risk measure and is not a clinical diagnosis.

**Open items:**

- Final C2 feature set.
- Final format and validation rules for the pre-meal glucose input.
- Final Sri Lankan GI reference source and licensing/access details.
- Final validation protocol and evaluation metrics.

### C3 — Multi-Factor Diabetic Risk Profiling & XAI (Rajapaksha R.M.L.I)

**TAF tasks:**

1. Design the patient risk-profile schema: physical activity, smoking, medication history, BP, cholesterol, kidney and liver disease, and body-weight changes.
2. Develop a multi-factor risk engine combining clinical and lifestyle inputs with food data.
3. Implement SHAP and LIME explainability over the prediction models.
4. Build an adaptive Diabetic Health Score (DHS) that evolves with patient behaviour.
5. Validate recommendations through domain expert review and a user study.

**Novelty (TAF):**

- A multi-factor diabetic risk profiling engine for the Sri Lankan context that goes beyond food.
- Transparent SHAP/LIME explanations per prediction. Recommendations come from clinician-reviewed templates.
- A dynamic DHS integrating dietary quality, activity, adherence and clinical risk markers.

**Data:**

| Purpose | Source (TAF) | Status |
|---|---|---|
| Risk factors | Structured patient questionnaires, collected with informed consent | BRFSS 2015 (secondary) for now. Sri Lankan data (WHO STEPS, SLHAS) planned. Primary questionnaire data only after ethics approval. |
| Food and glycemic inputs | C1 and C2 outputs | Via contract |
| Clinical thresholds | Ministry of Health Sri Lanka, National Guideline for Management of Diabetes (2021), and Sri Lanka College of Endocrinologists Clinical Practice Guideline – Diabetes (2025). The 'SLMA/SHRI 2019' guideline in the TAF could not be found, so it is not used. | Reference only |

**Inputs and outputs:**

- Inputs: the risk profile, plus C1 nutrition and C2 forecast and risk score.
- Outputs: an estimated risk level, the DHS, and explanations per prediction.
- Consumer: the client, through the gateway.

**Decisions:**

- Data approach: BRFSS 2015 (secondary) for now. Sri Lankan data (WHO STEPS, SLHAS) planned. Primary questionnaire data only after ethics approval.
- C3 stores the C1/C2 results it receives in its own c3 schema, so it can use several days of data, not just one meal.

**Open items:**

- The risk-profile schema fields and units. These become a contract.
- The expert reviewer and the user-study plan.

### C4 — Mobile Platform & Foot Monitoring (G.P. Welikala)

**TAF tasks:**

1. Design and develop the cross-platform Flutter app (iOS and Android).
2. Train a CNN (ResNet50/DenseNet) on DFUC2021 for foot abnormality detection.
3. Build a real-time health analytics dashboard with longitudinal trend visualisations.
4. Implement context-aware push notifications and a smart alert system.
5. Integrate all AI microservices, and conduct UAT with 50+ diabetic patients.

**Novelty (TAF):**

- The first consumer-grade AI foot ulcer monitoring module embedded in a dietary diabetes app.
- An adaptive smart dashboard with predictive alerts driven by behavioural and clinical patterns.

**Data:**

| Purpose | Source (TAF) | Status |
|---|---|---|
| Foot images | DFUC2021, DFU-QUT | Secondary. Check each dataset's access and licence terms |
| Local foot images | "Potential hospital partnership" | Optional. Requires ethical clearance |
| UAT | 50+ diabetic patients | Requires ethical clearance |

**Inputs and outputs:**

- Foot service input: a foot image. Output: an estimated abnormality class.
- Client: consumes every gateway endpoint and renders all screens.

**Decisions:**

- Flutter is the client (per the TAF).
- Proposed: C4 owns `client/` and `server/gateway/`, per TAF task 5. Awaiting confirmation.

**Open items:**

- The push-notification provider.
- Ethics timing for UAT.
- The access status of DFUC2021 and DFU-QUT.

---

## 2. Architecture (client-server)

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

**Rules:**

- The client talks **only** to the gateway (port 8000). It never calls a service directly.
- Services do not call each other. The gateway orchestrates the TAF data flow:
  - meal image → C1 (foods and nutrition) → C2 (glucose forecast and dietary risk) → C3 (risk, DHS and explanations)
  - foot image → C4 (foot analysis)
- Each service owns its own Postgres schema: `c1`, `c2`, `c3`, `c4`. A service never reads another service's schema.
- Payloads exchanged between components are documented in `contracts/`. Changing a contract requires a PR that touches `contracts/` and is reviewed by every affected member.

**Planned contracts** (list them in `contracts/README.md` as "planned"; do not define fields yet):

| Contract | From | To |
|---|---|---|
| `meal_nutrition` | C1 | C2, C3 |
| `glucose_forecast` | C2 | C3, client |
| `risk_history` | C3 | C3 (internal; stores past meals and glucose for trend analysis) |
| `risk_assessment` | C3 | client |
| `foot_analysis` | C4 service | client |
| `patient_risk_profile` | client | C3 |

---

## 3. Tech stack

| Layer | Choice | Source |
|---|---|---|
| Client | Flutter (Dart, stable channel) | TAF (C4 task 1) |
| Gateway and services | Python 3.11, FastAPI, Pydantic v2, Uvicorn | Team decision |
| Deep learning | PyTorch and torchvision | TAF allows TensorFlow or PyTorch; the team standardises on PyTorch |
| C1 models | `timm` (EfficientNetV2 / MobileNetV3), OpenCV, Albumentations | TAF |
| C2 models | PyTorch LSTM/GRU, XGBoost | TAF |
| C3 models | XGBoost / scikit-learn, SHAP, LIME | TAF |
| C4 models | torchvision ResNet50 / DenseNet, OpenCV | TAF |
| Database | PostgreSQL 16, SQLAlchemy 2, Alembic | Team decision |
| Experiments and data | MLflow, DVC | Team decision |
| Python tooling | uv (one workspace, one `uv.lock`), Ruff, mypy, pytest, pre-commit | Team decision |
| Delivery | Docker, Docker Compose, GitHub Actions, GitHub flow | Team decision |

**Do not add** ASP.NET/C#, React/Node frontends, extra databases or other frameworks. Install no ML libraries in the scaffold; each owner adds their own on their branch.

**Python package names must be unique**, because they share one uv environment: `diacare_shared`, `diacare_gateway`, `c1_food_nutrition`, `c2_glycemic_forecasting`, `c3_risk_xai`, `c4_foot_monitoring`. Use the `src/` layout.

---

## 4. Target structure (create exactly this)

```
<repo-root>/
├── .github/
│   ├── workflows/ci.yml
│   ├── CODEOWNERS
│   └── pull_request_template.md
├── client/
│   └── mobile_app/                          # created with `flutter create` (C4 lead)
│       ├── lib/
│       │   ├── main.dart
│       │   ├── core/                        # api_client.dart, config.dart, theme.dart
│       │   └── features/
│       │       ├── meal_scan/               # C1 screens
│       │       ├── glucose/                 # C2 screens
│       │       ├── risk_profile/            # C3 screens
│       │       ├── foot_monitor/            # C4 screens
│       │       └── dashboard/               # C4
│       └── test/
├── server/
│   ├── shared/
│   │   ├── src/diacare_shared/              # __init__.py, config.py, logging.py, health.py
│   │   └── pyproject.toml
│   ├── gateway/
│   │   ├── src/diacare_gateway/             # main.py, config.py, routes/{meals,glucose,risk,foot}.py
│   │   ├── tests/test_health.py
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   └── services/
│       ├── c1_food_nutrition/
│       │   ├── src/c1_food_nutrition/       # main.py, api/routes.py, schemas.py, services/, ml/, db/
│       │   ├── training/                    # .gitkeep
│       │   ├── notebooks/                   # .gitkeep
│       │   ├── tests/test_health.py
│       │   ├── docs/                        # member's own documents (.gitkeep)
│       │   ├── Dockerfile
│       │   ├── pyproject.toml
│       │   └── README.md                    # C1 subsection from section 1a
│       ├── c2_glycemic_forecasting/         # same layout; README = C2 subsection
│       ├── c3_risk_xai/                     # same layout; README = C3 subsection
│       └── c4_foot_monitoring/              # same layout; README = C4 subsection
├── contracts/
│   └── README.md                            # versioning rules + planned contracts table
├── infra/
│   ├── docker-compose.yml
│   └── postgres/init.sql                    # creates schemas c1, c2, c3, c4
├── data/                                    # gitignored, DVC-tracked: c1/ c2/ c3/ c4/ with .gitkeep
├── docs/
│   ├── adr/
│   │   ├── 0001-client-server-monorepo.md
│   │   └── 0002-c1-secondary-datasets.md
│   ├── TEAM.md
│   └── SETUP_PROMPT.md                      # this file
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml                           # uv workspace root
├── uv.lock
├── CLAUDE.md                                # shared AI-assistant rules (section 9)
└── README.md
```

Members add their own ADRs (`0003-…` onward) on their branches when they make decisions such as a dataset choice.

---

## 5. Placeholder behaviour

**Each service** (C1 to C4):

- `GET /health` returns `{"status": "ok", "service": "<package_name>"}`.
- It has one placeholder route that returns `501 Not Implemented`:

| Service | Placeholder route |
|---|---|
| C1 | `POST /v1/meals/analyze` |
| C2 | `POST /v1/glucose/forecast` |
| C3 | `POST /v1/risk/assess` |
| C4 | `POST /v1/foot/analyze` |

**Gateway** (port 8000):

- `GET /health` checks all four services and reports each one's status.
- It proxies `/api/v1/meals/*` to C1, `/api/v1/glucose/*` to C2, `/api/v1/risk/*` to C3 and `/api/v1/foot/*` to C4.
- Service URLs come from environment variables (see `.env.example`).

**Ports:** gateway 8000, C1 8001, C2 8002, C3 8003, C4 8004, Postgres 5432, MLflow 5000.

**Flutter:**

- A home screen with placeholder tabs: Meal Scan, Glucose, Risk Profile, Foot Monitor, Dashboard.
- The API base URL is set in `core/config.dart`.
- The default widget test is updated so it passes.

**Tests:** one health test per Python package, plus the Flutter widget test.

---

## 6. Git workflow

1. **Inspect first.** Run `git status`, `git branch -a`, and list the tree to depth 3 on `main`. Report what exists.
   - If `main` contains `components/` or any .NET files (`Program.cs`, `*.csproj`, `bin/`, `obj/`, `appsettings*.json`), list them and ask before removing or moving anything.
   - Do not touch other branches.
2. **Create the working branch** from an up-to-date main: `git checkout main && git pull && git checkout -b setup/monorepo-scaffold`.
3. **Commit in small, logical steps** using Conventional Commits:
   1. `chore: add root config (workspace, gitignore, env example, pre-commit)`
   2. `feat(server): add shared package and API gateway skeleton`
   3. `feat(server): add C1–C4 service skeletons`
   4. `feat(client): add Flutter app skeleton`
   5. `build: add docker compose and postgres schemas`
   6. `ci: add GitHub Actions workflow`
   7. `docs: add README, TEAM, contracts, ADRs 0001–0002 and CLAUDE.md`
4. **Push and open a PR into `main`.** Do not merge it yourself.
5. **Member branches.** Each member branches from `main` after the PR is merged:
   - C1: `c1_kavithi` (already exists)
   - C2: `[INFORMATION REQUIRED: ask the user]`
   - C3: `c3_lochana`
   - C4: `[INFORMATION REQUIRED: ask the user]`
   - Use the convention `c<N>_<firstname>`. Record all branch names in `docs/TEAM.md`.
6. **CODEOWNERS.** Ask the user for each member's GitHub username `[INFORMATION REQUIRED]`.
   - If they are not available yet, write the file with commented placeholders.
   - Each member owns `server/services/c<N>_*/` and `data/c<N>/`.
   - `client/` and `server/gateway/`: proposed owner C4, pending confirmation.
   - `contracts/` and `server/shared/`: all four members.

---

## 7. CI (`.github/workflows/ci.yml`)

**Triggers:** pull requests to `main`, and pushes to `main` and to branches matching `c*_*`.

**Python job:**

```
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy server
uv run pytest
```

**Flutter job:** `flutter analyze` and `flutter test`, run in `client/mobile_app`.

---

## 8. Done criteria (verify each one, then report)

- [ ] `uv sync` succeeds.
- [ ] `uv run ruff check .`, `uv run mypy server` and `uv run pytest` all pass.
- [ ] `docker compose -f infra/docker-compose.yml up --build` starts the gateway, C1 to C4, Postgres and MLflow.
- [ ] `http://localhost:8000/health` reports all four services as ok.
- [ ] `flutter analyze` and `flutter test` pass in `client/mobile_app`.
- [ ] Each service README contains its section 1a subsection.
- [ ] Final report lists: files created, every command run with its result, and the open items.

---

## 9. `CLAUDE.md` content (shared rules for every member's AI assistant)

- This is a research prototype. Use "estimated" and "prediction", never "diagnosis". Make no clinical-validation claims.
- Never invent data, results, metrics, citations or participants. Write `[INFORMATION REQUIRED]` instead.
- Work only inside your own component folder. Changes to `contracts/`, `server/shared/`, the gateway or the client need a PR reviewed by the affected owner.
- Never show raw model confidence values in patient-facing UI. **C3 note:** Risk % output includes a risk percentage. Should patients see only the risk band (low/medium/high) and DHS, or the % as well? Flag this with supervisors.
- No primary data from patients may be collected before ethical clearance.
- Follow the tech stack in `docs/SETUP_PROMPT.md` section 3. Ask before adding a new framework. **C3 note:** Can Streamlit be used for PP1 demo only?
- Follow the workflow: understand → inspect → implement → lint → test → report.

---

## 10. Project-wide open items (write these into the root `README.md`; do not resolve them yourself)

1. **Clinician & Admin Portal.** It appears as an output in the TAF architecture diagram, but no member owns it in the TAF. Its owner and technology need deciding. Do not scaffold it.
2. **Gateway and client ownership.** Proposed: C4. Needs confirmation.
3. **Authentication approach** for the gateway.
4. **Performance targets** (accuracy, latency) for every component. These are not in the TAF. Set them with the supervisors; do not present them as TAF requirements.
5. **Ethical clearance.** The TAF plans the application in months 1–2. It is required before any primary patient data: C2 (no primary glucose data for research without clearance; development uses CGMacros), C3 questionnaires, C4 hospital images and UAT.

Component-specific open items live in each service README (section 1a).

**Resolved:**

- C1 uses secondary datasets only (ADR 0002).
- C2 uses CGMacros for model development and validation (see the C2 subsection in section 1a).
- C3 starts with BRFSS 2015 (secondary); see the C3 subsection in section 1a.
