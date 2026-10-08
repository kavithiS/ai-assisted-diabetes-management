# AGENTS.md — C1 Food Recognition & Nutritional Analysis

Rules for any AI coding agent working on Component 1 of DiaCare (J26-IT-352).

- **Owner:** Thilakarathne K.S (IT23295742)
- **Branch:** `c1-kavithi` (created from `main`). The old branch `c1_kavithi` is a read-only archive of earlier work.
- **Folder:** `server/services/c1_food_nutrition/`
- **Port:** 8001

Read these before starting any task:
1. The root `CLAUDE.md` (shared team rules).
2. `docs/SETUP_PROMPT.md`, especially the C1 subsection of section 1a.
3. `SKILL.md` in this folder (technical reference).

If any of these disagree, the priority order is: (1) the user's explicit instruction, (2) the TAF, (3) decisions in `docs/adr/` and `docs/SETUP_PROMPT.md`, (4) this file and `SKILL.md`, (5) general best practice.

---

## 1. Workflow for every task

```
Understand → Inspect → Plan → Implement → Lint → Test → Run → QA → Fix → Regression → Report
```

1. **Understand.** Restate the task in one or two sentences. If anything is unclear, ask (see section 3).
2. **Inspect.** Read the existing code, schemas, routes, tests and the `contracts/` folder. Use the real repo, never assumptions.
3. **Plan.** List the files you will create or change. For anything over ~3 files, show the plan and wait for approval.
4. **Implement.** Keep changes inside `server/services/c1_food_nutrition/` and `data/c1/`.
5. **Lint.** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy server`.
6. **Test.** `uv run pytest server/services/c1_food_nutrition`, then the full `uv run pytest`.
7. **Run.** Start the service and call the endpoints (section 2).
8. **QA, fix, regression.** If anything fails, find the root cause, fix it and re-run everything.
9. **Report.** Use the completion report format (section 7).

### A task is only complete when all of these are true

- Ruff, Ruff format and mypy pass with no new warnings.
- All C1 tests pass, and the full test suite still passes.
- The service starts with no errors.
- The changed endpoints work when called for real, not just in tests.
- Error cases return the right status codes.
- `GET /health` still works, through C1 directly and through the gateway.
- No data files, model weights, secrets or `.env` files are staged for commit.

If any item fails: stop, diagnose, fix, re-test. Never mark the task done with a failing check.

---

## 2. How to QA C1

There is no browser UI in this service, so QA means calling the API.

**Start C1 on its own:**
```powershell
uv run uvicorn c1_food_nutrition.main:app --port 8001 --reload
```
- Open `http://localhost:8001/docs` (Swagger UI) to try endpoints by hand.
- Or call it from a script using `httpx`, with a generated test image (never a real patient photo).

**Check through the gateway:** run `.\scripts\dev.ps1`, then call `http://localhost:8000/api/v1/meals/...`.

**Every endpoint change must be checked for:**
- a valid JPEG and a valid PNG
- no image at all
- a wrong file type, for example a `.txt` renamed to `.jpg`
- a corrupt image
- an image over the size limit
- each `meal_type` value, plus an invalid one

**Flutter screens** (`client/mobile_app/lib/features/meal_scan/`) are owned by the client owner (proposed: C4). Only change them when the user asks. Every change goes through a PR they review, and is checked with `flutter analyze`, `flutter test`, and a run on an emulator or device.

---

## 3. Do not assume. Ask.

Stop and ask one clear question when:
- a requirement, field name, unit or status code is not written down anywhere
- a change would touch `contracts/`, `server/shared/`, the gateway, the client or another component
- a dataset, licence, model choice or evaluation metric is not already decided
- you would need to invent a number (accuracy, threshold, portion size, nutrient value)

Good question: *"The contract doesn't define what happens when no food is recognised. Should C1 return 200 with an empty `foods` list, or 422?"*

---

## 4. Research integrity (this is an academic project)

**Never invent:**
- accuracy, F1, mAP or MAE values: report only what a run actually produced, and say which run
- nutrient values: every value must come from the Sri Lankan food composition data or USDA FoodData Central, with its source recorded
- datasets, citations, participants or results

**Use honest language:**

| Avoid | Use instead |
|---|---|
| "diagnosis", "detects disease" | "food recognition", "nutrition estimate" |
| "accurate", "guaranteed" | "estimated", plus the measured error on a named test set |
| "clinically validated" | "evaluated on the Food-101 test split" (or whichever split was actually used) |

**Mark anything that isn't real.** Mock responses, sample data and placeholder values must be labelled clearly in the code and in the response (`"is_mock": true`).

**Performance targets:** the TAF sets none. Don't write targets such as "85%+" into code, docs or tests. They are agreed with the supervisors and recorded in an ADR.

---

## 5. Boundaries

- **C1 owns** `server/services/c1_food_nutrition/`, `data/c1/`, and the `c1` PostgreSQL schema.
- **C1 never** reads or writes another component's schema, and never calls C2, C3 or C4 directly. The gateway orchestrates.
- **Contract changes** (`contracts/meal_nutrition*`) need a PR into `main` approved by C2 and C3, because they consume C1's output.
- **Shared files** (`server/shared/`, `pyproject.toml` at the root, CI, the gateway, `docs/` outside the C1 folder) need a PR reviewed by the team.
- **Dependencies:** add them to C1 only, with `uv add --package c1-food-nutrition <name>`. Never add a new framework without asking.
- **Not allowed:** .NET/C#, React, Node, TensorFlow alongside PyTorch, Docker.

---

## 6. Data, models and Git

- **Never commit** datasets, images, CSVs, model weights (`*.pt`, `*.pth`, `*.onnx`), `mlruns/`, `mlflow.db` or `.env`. Data lives in `data/c1/`, which is gitignored and tracked by DVC.
- **Patient data:** C1 uses secondary datasets only (ADR 0002). Never collect, store or commit photos of real patients' meals.
- **Commits:** small, using Conventional Commits with the `c1` scope: `feat(c1): …`, `fix(c1): …`, `test(c1): …`, `docs(c1): …`, `refactor(c1): …`.
- **Never** push to `main`, force-push, or delete or move files without listing them and getting approval first.
- Before committing, run `git status` and check that only the intended files are staged.

---

## 7. Completion report

End every task with this report:

```
## Task: <name>

### What was done
<2–4 sentences>

### Files changed
- <path> (new | changed | deleted)

### Checks
| Check | Result |
|---|---|
| ruff check | pass / fail |
| ruff format --check | pass / fail |
| mypy server | pass / fail |
| pytest (C1) | N passed |
| pytest (all) | N passed |
| Service starts | yes / no |
| Manual API QA | <cases tried and results> |

### Issues found and fixed
| Issue | Cause | Fix |

### Open questions / not done
- <anything blocked, with the reason>

### Status: DONE | BLOCKED (<reason>)
```

---

## 8. What C1 does (keep focus)

1. Accept a meal image, the meal type, the capture time and an optional reference card.
2. Recognise one or more foods on the plate (multi-label).
3. Estimate each food's portion in grams, using the reference card where present.
4. Look up nutrition: Sri Lankan composition data first, USDA as fallback, source recorded.
5. Return structured JSON (the `meal_nutrition` contract) for C2, C3 and the app.

Anything outside this list is out of scope unless the user asks for it.
