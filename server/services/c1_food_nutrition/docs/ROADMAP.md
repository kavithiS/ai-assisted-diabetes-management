# C1 Roadmap

> The service serves `/v1/meals/analyze` (the gateway exposes it as `/api/v1/meals/analyze`),
> `/docs` and `/openapi.json`. Docker is not used (ADR 0003). C1 uses secondary datasets only
> (ADR 0002). For the day-to-day state, read `CONTEXT.md` first; this page is the phase plan.

Plan written 2026-10-03; **status updated 2026-10-15.** Phase 0 (scaffolding) is done.
Phase 1 has started on the model side (item d); the importers (a, b) and portion
estimation (e) have not.

| Item | Status 2026-10-15 |
|---|---|
| a. USDA importer | Not started (stub). Playbook: `tasks/nutrition-importers.md` |
| b. MRI importer | Not started (stub). A repaired Sri Lankan table now exists (`data/c1/c1_foods_combined.csv`); see `CONTEXT.md` section 8 |
| c. Source of every nutrition row | As below |
| d. Model pipeline | Training runs outside the repo: Stage 1 on Food-101 and Stage 2 on the Sri Lankan sets (results in `EXPERIMENTS.md`). Not yet in the repo or behind `FoodRecognizer` |
| e. Portion estimation | Not started. Playbook: `tasks/portion-estimation.md` |

## Phase 1

### a. Nutrition knowledge base: USDA FoodData Central importer (first)

- Source: a converted USDA FDC CSV, already in hand. Its columns match the MRI CSV, so both
  importers can share one CSV parser.
- **Empty cells mean "not reported" and must become NULL, never 0.** The importer must never
  fill in or estimate a value.
  - Current schema: a nutrient the source does not report has no `food_nutrient` row, and it
    reads back as `null` in `NutrientProfile`. Before implementing, confirm whether this is
    enough or whether explicit NULL rows are wanted.
  - Tests must cover empty cell → `null`, and must show that `0` stays `0` (a real zero is
    different from "not reported").
- Put the source file under `data/external/` and version it with DVC, not git.
- Implement `UsdaFdcImporter.parse` (currently a stub).

### b. MRI Sri Lanka FCDB importer (blocked)

- **Blocked** until the source CSV corruption is fixed. In that file, "na" was replaced by
  "100" (e.g. header `food_100me`, value `Ba100`).
- **The importer must reject a header named `food_100me`**, so the corrupted file can never
  load. This needs a test using a small, labelled fixture file.
- Header checks alone will not catch corrupted values: a cell that should be "na" may now
  read as a plausible number (`100`). Agree on value-level validation before import.
- Implement `MriSriLankaImporter.parse` (currently a stub).

### c. Record the source of every nutrition row

- Already in place:
  - every `food` row has `source_id → nutrition_source` (`MRI_SL_FCDB` / `USDA_FDC`)
  - the API exposes this as `items[].nutrition_source`
- To do: decide what happens when a food exists in both sources (precedence or explicit
  selection), and record the dataset release and import date in `nutrition_source`.

### d. Model pipeline: Food-101 baseline

- As built (2026-10-15): PyTorch and torchvision (CUDA 12.6 wheels) in a separate training
  environment, not a service dependency. timm, Albumentations and MLflow are not used; each
  run writes a JSON report instead. DVC is not set up.
- Data: secondary datasets only (ADR 0002). Food-101 for Stage 1 (reconstructed split), the
  public Sri Lankan sets for Stage 2 (multi-label, split by scene group, leak-audited).
- Still to do: move the training code into `training/` (`tasks/move-training-into-repo.md`),
  then put the model behind `FoodRecognizer` (`tasks/wire-recognizer.md`).
- Report only measured results, never estimated ones.

### e. Portion estimation

- Replace `MockPortionEstimator`.
- **Finalise the `reference_object` format here, before C4 integration (ADR 0004).** It will
  likely become an enum or a dimensions object. The change is breaking: update the ADR,
  schema, OpenAPI description and C4.

## Open items outside Phase 1

- ADR 0002 (monorepo layout) stays **Proposed** while the C2–C4 owners are consulted.
