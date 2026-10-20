# C1 next steps

**Written:** 2026-10-18. Remove items as they are completed and log them in `CHANGELOG.md`.

Project-wide backend and database plan (login, patient identity, schemas, phases P0–P10): `docs/architecture/BACKEND_ARCHITECTURE.md` and `docs/architecture/DECISIONS_AND_GAPS.md` at the repo root (proposed 2026-10-18).

This is the remaining work for C1 after the training experiments, nutrition matching and service wiring are done. Items are grouped by priority. See `CONTEXT.md` section 10 for current scores and `OPEN_ITEMS.md` for decisions that need someone else.

## Priority 1: owner decisions (blocking other work)

These need the owner's answer before the next training or service change.

| # | Decision | Options | What it blocks |
|---|---|---|---|
| D1 | **Seed averaging** | (a) Use 3-model average: test mAP 0.936, but 3 bundles, ~3x inference, threshold 0.65. (b) Keep single model: test mAP 0.909, 1 bundle, threshold 0.85. | A6 final model, service changes |
| D2 | **Epochs for the final model** | 15 (current default) or another count. Once train+valid are combined there is no validation set to pick the best epoch, so the number must be fixed beforehand. | A6 final model |
| D3 | **Threshold for the final model** | 0.85 (current single model) or 0.65 (if seed averaging). Chosen on validation; after combining train+valid, it cannot be tuned. | A6 final model |

## Priority 2: model and data improvements

| # | Task | Effort | Details |
|---|---|---|---|
| T1 | **A6: train the final model on train+valid** | ~5 min per run (GPU) | After D1-D3 are decided. Combine train and valid photos, train with the locked settings, export with `python -m c1_training.export`, restart the service. If seed averaging: train 3 seeds and export 3 bundles. |
| T2 | **A7: list weak classes needing more photos** | Small (analysis) | Classes with low AP and few test photos: `lunu_miris` (0.53 AP, 6 test), `fish_curry` (0.64, 5), `vegetable_salad` (0.68, 3), `fried_potato` (0.77, 3). Also `pumpkin_curry`, `fanta`, `iced_coffee` which dropped out after the leak fix. Check licences (ADR 0002) before collecting new photos. |
| T3 | **Collect more Sri Lankan food photos** | Medium to large | For the weak classes above. Needs ethical clearance if photos come from patients. Public datasets or the owner's own photos are fine. |
| T4 | **10 unmatched nutrition classes** | Small | `asmi`, `brinjal_dish`, `cutlet`, `kokis`, `konda_kewum`, `lunu_miris`, `mun_kewum`, `pappadam`, `shrimp_curry`, `watalappam`. Options: find better table rows, ask supervisors about regional tables (OPEN_ITEMS A1), or accept as unknown. |

## Priority 3: portion estimation

| # | Task | Effort | Details |
|---|---|---|---|
| P1 | **Decide the reference-object approach with C4** | Decision | OPEN_ITEMS A3: the `reference_object` format in the request contract is not finalised. |
| P2 | **Build the portion estimator** | Large | Replace the fixed 100 g mock. Playbook in `docs/tasks/portion-estimation.md`. Until this is done, calorie totals are per 100 g and `is_mock` stays `true`. |

## Priority 4: engineering and clean-up

| # | Task | Effort | Details |
|---|---|---|---|
| E1 | **Seed-average inference in the service** | Medium | Only needed if D1 = yes. Load 3 bundles, average their sigmoid outputs, use the new threshold. |
| E2 | **PyTorch as optional dependency** | Small (team PR) | Add to `pyproject.toml` as optional; update `uv.lock`. Shared file: needs the team's review. |
| E3 | **`.env.example` updates** | Small (shared file) | Add `RECOGNIZER`, `MODEL_PATH`, `MODEL_DEVICE`, `NUTRITION_TABLE_PATH`. |
| E4 | ~~Gateway routes for meal history~~ | Done 2026-10-18 | The bare `/api/v1/meals` path returned a 307 redirect; fixed with a test. All meal and food routes now go through the gateway with the patient's identity. |
| E5 | **Fix contract wording for `carbohydrate_g`** | Small (contract PR) | Says "Total carbohydrate" but the value is available carbohydrate (fibre excluded). Tell C2 and C3. |
| E6 | **USDA Foundation energy gap** | Medium | 158 of 232 USDA rows have no `energy_kcal`. Rebuild from the Atwater energy ids in the USDA download, or accept and document the gap. |
| E7 | **CI for PyTorch tests** | Small | Currently skipped in CI. Add a CI step with the server environment, or mark them as integration tests. |
| E8 | **Move remaining curation scripts** | Small | `build_curation.py`, `make_class_map.py`, `process_food101.py` are still outside the repo. |
| E9 | **Clean up outside git** | Small (owner action) | Old `.venv` (3.13), `runs_backup_2026-10-15/`, `runs_quicktest_py311/`, `*.bak_*` script copies. Keep the two manifest backups until the leak fix is confirmed final. Delete `server/services/c1_food_nutrition/c1_local.db` (stray SQLite file). |

## Priority 5: team coordination

| # | Task | Who | Details |
|---|---|---|---|
| C1 | Approve `meal_nutrition` v1 schema | C2, C3 | OPEN_ITEMS A4 |
| C2 | Finalise `reference_object` format | C4 | OPEN_ITEMS A3 |
| C3 | Regional nutrition tables as fallback | Supervisors | OPEN_ITEMS A1; would cover the 10 unmatched classes |
| C4 | Evaluation targets | Supervisors | OPEN_ITEMS A5; no target may be written until supervisors set one |
| C5 | GitHub usernames for CODEOWNERS | All members | OPEN_ITEMS A8 |

## What is done (summary)

- Model training: MobileNetV3-Large, 48 Sri Lankan food classes, ImageNet start, 256 px, 15 epochs, 3 seeds. Test mAP 0.919 mean (deployed seed 2: 0.909). Extra datasets (veg_cooking, pust, FoodBD) tested and not adopted. Food-101 pretraining tested and not adopted.
- Leak audit and fix: two passes, 0 test copies remaining.
- Relish relabelling: `lunu_sambol` / `lunu_miris` separated.
- Nutrition lookup: 38 of 48 classes matched to Sri Lankan FCDB or USDA entries. Real values served (opt-in).
- Service: trained model wired in (opt-in), startup preload, 60 s timeout, gateway route.
- Flutter: Meal Scan screen, portion editing, meal history screens, tests passing.
- Test-time options: flip, per-class thresholds (not helpful), seed averaging (helpful but not deployed).
- Docs: CONTEXT, CHANGELOG, EXPERIMENTS, OPEN_ITEMS, DATA, NUTRITION_MATCHES, task playbooks all current.
