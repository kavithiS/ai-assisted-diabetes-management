# C1 changelog

Newest first.

## 2026-10-18: Patient identity, gateway login and gateway fixes (project-wide plan, phases P1 to P5)

Plan: `docs/architecture/BACKEND_ARCHITECTURE.md` and `DECISIONS_AND_GAPS.md` at the repo root (ADR 0005 login, ADR 0006 patient identity). The team approved the login design and the new libraries on 2026-10-18.

C1 changes (all patient-scoped):
- `meal.patient_id` (UUID, not null) with the index `ix_meal_patient_eaten`; migration `d4a6c2f8b913` (existing meals get the demo patient `00000000-0000-4000-8000-000000000001`; the local database had none). Applied to the local PostgreSQL.
- Every meal endpoint and `POST /v1/meals/analyze` need the gateway's proof (`X-Internal-Token` equal to `INTERNAL_TOKEN`, and `X-Patient-Id`); otherwise 401. A patient only sees their own meals; another patient's meal is a 404. `/v1/foods` needs neither.
- `DELETE /internal/v1/patients/{id}` removes one patient's meals (idempotent, 204).
- New setting `INTERNAL_TOKEN`. Without it every patient endpoint answers 401. `core/context.py` now re-uses the request-id variable of `diacare_shared`, and C1 also handles the shared `AppError`.
- Tests: `tests/integration/test_patient_scoping.py` (isolation, missing or wrong proof, internal delete), a patient-id migration test, and the test client now sends the gateway's headers by default.

Shared (`server/shared`, needs the other members' review): error envelope, request id and body-size middleware, JSON logs, internal-token check, engine helper (14 tests). C2 to C4 now use the envelope and the middleware.

Gateway (shared area, owner C4 per the team): login, refresh with rotation and reuse detection, logout, `/me`, delete account (asks each service in `DELETE_FANOUT_SERVICES`, today `c1`), rate limit, command-line `create-user`, `core` tables (migration `9b3f0a7c5e21`, applied locally). Shared HTTP client, the bare `/api/v1/meals` path (it returned a 307 before; found and fixed, with a test), the gateway now sets the identity headers and drops the client's, per-route timeouts (analyze 65 s, others 15 s), 502 and 504 in the envelope, 11 MB body limit. New libraries: `pyjwt`, `argon2-cffi` (and their dependencies); `uv.lock` gained only those.

Dev setup: the local `.env` now has `AUTH_REQUIRED=false` and a fixed `DEMO_PATIENT_ID`, so the app (which has no login screen yet) keeps working. **Everyone else needs the new variables from `.env.example`** (`INTERNAL_TOKEN` at least) or C1 answers 401.

Not done: the per-schema database roles and moving C1 into the `c1` schema (`infra/postgres/README.md`; needs a PostgreSQL superuser), the app's login screen (P8), C2 to C4 storage (P7), the meal chain C1 → C2 → C3 (P6), readiness checks and backups (P10).

Checks (2026-10-18): ruff check and ruff format clean; mypy clean (165 files); `uv run pytest` 296 passed, 25 skipped, 0 failed; C1 and shared tests in the PyTorch server environment 213 passed, 0 skipped (the gateway tests do not run there: that environment has no `argon2`). A 21-step run against the real C1, the real gateway (login required) and the local PostgreSQL passed (two patients cannot see each other's meals, forged identity headers are ignored, reused refresh token is refused, the sixth failed login gets 429, deleting an account removes the patient's C1 data); its test accounts and audit rows were deleted afterwards. Not run: the `c1_training` tests in `.venv311` (training code untouched by this work), the Flutter tests, the app on the emulator, `init.sql`.
## 2026-10-18: Owner's nutrition matches, USDA SR Legacy rows, training options for extra datasets

- `ml/data/class_concepts.csv`: seven classes matched by the owner: `dhal_curry` SL_54 (exact), `fish_curry` SL_146 (close), `meat_curry` SL_158 (close), `noodles` SL_33 (partial; SL_32 never used), `milkshake` US_170884 (close), `submarine` US_170309 (partial), `patty` US_167660 (partial). Now 16 exact, 7 close, 15 partial, 10 none (`NUTRITION_MATCHES.md`). 38 of 48 model foods get nutrient values.
- `data/c1/c1_foods_combined.csv` (outside git): three USDA SR Legacy rows appended, values read from the local USDA download. `services/nutrition.py` accepts the source `USDA FoodData Central, SR Legacy` (same contract value `USDA_FDC`). Re-ran `db.import_cli --source usda_fdc`: foods 473 → 476, USDA 232 → 235, nutrient rows 2,426 → 2,444 (database query).
- Tests: `tests/unit/test_class_matches.py` (the seven matches, SR Legacy accepted, each matched food and a plate of all seven have known totals, unmatched classes stay null with the warning); `test_labels.py` no longer expects `dhal_curry` and `meat_curry` to be unmatched.
- Training code (`c1_training`): `stage2 --extras-train-only` makes the extra datasets (`--also`) add train photos only, selects the best epoch on the Sri Lankan baseline valid photos and reports baseline-class test mAP separately from the new classes (scored on the extras' own test photos). `leak_audit --also` compares extra-dataset train photos with the Sri Lankan valid/test photos. `manifest.load_manifest(train_only=...)` and `split_items`. Tests: `training/tests/test_stage2_subset.py`, two in `test_manifest.py`, one smoke run.
- Extra image datasets tested (12 runs, 3 seeds each, `--extras-train-only`, same 209 test photos and 48 classes): + veg_cooking 0.918, + pust 0.919, + foodbd 0.930 (SD 0.042), + all three 0.921, against the baseline 0.919 (SD 0.010). Paired test differences -0.001 (SE 0.002), +0.000 (0.004), +0.012 (0.020), +0.003 (0.006); none passes the keep rule, so the model is unchanged. Sources: `runs/stage2_..._seed{0,1,2}_{xveg,xpust,xfoodbd,xall}_report.json`; details in `EXPERIMENTS.md`.
- Test-time options (`a5_eval.py`, `a5_results.json`): flip augmentation and per-class thresholds do not help; averaging the three seed models raises valid mAP 0.940 → 0.951 and test mAP 0.919 → 0.936 (better on 3 of 3 seeds). Not in the service yet (it loads one bundle).
- Leak audit with pust, foodbd and veg_cooking train photos added (console output; `leak_audit_extras_2026-10-18.csv`): 0 of 209 test and 0 of 262 valid photos have a training copy at distance ≤ 30; none of the closest training photos at ≤ 48 come from the extra datasets.

## 2026-10-17: Startup model loading, longer timeouts, real-model start script

- `main.py`: the trained recogniser loads at startup (lifespan), about 10 s, so the first request is no longer slow. Test: `tests/unit/test_startup.py`.
- New `scripts/start_c1.ps1`: starts C1 with `RECOGNIZER=torch`, `MODEL_PATH` (relish-48 seed 2 bundle) and `NUTRITION_TABLE_PATH`, using the hand-built server environment. Plain `uv run uvicorn` still starts the mock recogniser and mock nutrition.
- App: photo resized to at most 1280 px before upload; analyze timeout 60 s with separate network / timeout messages. Gateway (shared, approved): `/api/v1/foods` route added, request timeout 65 s.
- End-to-end check through the gateway, 4 test photos (console output): string_hoppers → `mallum`, `string_hoppers`, `white_rice` (two false positives); hoppers → `hoppers`; kiribath → `kiribath`; pittu → nothing above the 0.85 threshold. About 2.5 s per request.
- Checks: ruff, ruff format, pytest (C1: 212 passed, 24 skipped), flutter test 39 passed.

## 2026-10-16: Flutter meal history, food search and today's summary screens

- New Flutter feature `lib/features/meal_history/`: `MealHistoryApi` (calls GET /v1/foods, POST/GET/DELETE /v1/meals, GET /v1/meals/summary), models (`FoodResult`, `MealOut`, `MealItemOut`, `DailySummary`, `MealCreate`, `MealItemIn`), four screens (`MealHistoryScreen`, `MealDetailScreen`, `AddFoodScreen`, `TodaySummaryScreen`), shared `NutrientTable` widget.
- Alembic migration `c3e5a1b7d2f4` applied: `meal` and `meal_item` tables created in the database.
- MRI Sri Lanka (241 rows) and USDA (232 rows) imported from `data/c1/c1_foods_combined.csv` via `db.import_cli`.
- Navigation updated in `main.dart`: "Meals" and "Today" tabs added after "Meal Scan".
- Tests: 6 model-parse tests, 4 `MealHistoryScreen` widget tests, 4 `TodaySummaryScreen` widget tests. All 34 Flutter tests pass. `flutter analyze` clean.
- Not done: gateway routes for the new endpoints, `AddFoodScreen` widget tests (add/search flow needs an integration test against the server), `MealDetailScreen` widget tests (delete confirmation needs a fuller stub). One entry per piece of work. Numbers come from the files named beside them. Entries before 2026-10-15 were written afterwards from the git log (repo work, commit hash given) and from `CONTEXT.md` section 4 and `_curation\CLEANING_NOTES.md` (work outside git); those not backed by a commit or a file are marked [UNVERIFIED].

## 2026-10-16: Meal history, food search and table importers (backend)

- New tables `meal` and `meal_item` (migration `c3e5a1b7d2f4`, after `78ab001a889d`). A meal item stores the nutrients of the logged portion (a snapshot), so later changes to the food table never rewrite history. Unknown nutrients are `null`, never 0. No image, no patient identifier and no model confidence is stored or returned. Demo data only (ethical clearance rule).
- New endpoints (`api/history.py`): `GET /v1/foods?q=`, `POST /v1/meals` (201), `GET /v1/meals?limit=&offset=`, `GET /v1/meals/summary?day=&utc_offset_minutes=`, `GET` and `DELETE /v1/meals/{id}`. Items are either a stored `food_id` (nutrients scaled from the per-100 g values) or a free entry (`name` and optional `nutrients`, for example from a scan result). A total is `null` when any item's value for that nutrient is unknown.
- The `MriSriLankaImporter` and `UsdaFdcImporter` stubs now read their rows from `data/c1/c1_foods_combined.csv` through `CompositionTableLookup`, so the same checks apply (`food_100me` header rejected, blank is unknown, only allowed sources). Importing twice updates instead of duplicating. CLI: `uv run python -m c1_food_nutrition.db.import_cli --source mri_sl --path data/c1/c1_foods_combined.csv`.
- `db/session.py`: SQLite engines allow use from worker threads; in-memory SQLite uses one shared connection (tests). `INVALID_METADATA` is now used only for form errors on `/meals/analyze`; JSON body errors elsewhere are `VALIDATION_ERROR`.
- Not yet run by the owner at the time of writing: ruff and ruff format passed on a copy; mypy and pytest are for the owner to run. Not done: Flutter screens, gateway routes for the new endpoints, `c1` schema.

## 2026-10-16: Nutrition values from the combined table (opt-in)

- New `CompositionTableLookup` (`services/nutrition.py`), enabled by `NUTRITION_TABLE_PATH` (the file `data/c1/c1_foods_combined.csv`, not committed). It loads only the Sri Lankan FCDB (`MRI_SL_FCDB`) and USDA (`USDA_FDC`) rows (473 of 2,716) and skips the 2,243 regional rows, because `AGENTS.md` and the contract enum allow only those two sources (A1 is still open). Header check (a `food_100me` header is rejected), blank cell is `null`, bad or negative numbers fail with file and row. Contract fields: energy, carbohydrate (available carbohydrate), fibre, protein, fat, sodium; sugars always unknown.
- Matching is per class, not per broad concept (the concept `curry_dish` would have given every curry the values of Sweet Potato Curry). `ml/data/class_concepts.csv` got the columns `food_id`, `match`, `note`; I reviewed the 48 classes of the shipped model against the table: 15 exact, 4 close, 12 partial (31 get values), 17 none. `food_code` is now the matched table entry (or `null`). A model class with no reviewed entry cannot be loaded. List without values in `docs/NUTRITION_MATCHES.md`.
- Responses: close and partial matches add a note to `meta.warnings`; a food with no entry adds a warning that its nutrients and the meal totals are unknown. `RecognizedFood` has an optional `match_note`.
- Checked the chosen rows in the real table: validation status ok, no flags on the nutrients used, energy within 14% of 4P+9F+4C+2fibre, no duplicated values. Found a data error: Fried Noodles (SL_32) has the same six values as Carrot Curry (SL_74); it is not used (OPEN_ITEMS B).
- Real service over HTTP with the trained model and the real table, 5 dataset photos: kiribath, hoppers and pizza got values (pizza with a partial-match note); the two rice-and-curry plates returned `basmati_rice` and `vegetable_salad` with values and `dhal_curry` and `meat_curry` with `null` and a warning, so their totals were `null`. Still `is_mock: true` because portions are mock (values are per 100 g).
- Checks: ruff, ruff format, mypy (128 files) clean; pytest 199 passed, 23 skipped in the project environment, 221 passed, 1 skipped in the server environment. `uv.lock` and all shared files unchanged. New tests use made-up fixture rows only; one test checks every matched class against the real table and skips where the table is absent (CI).
- Not done: the owner's choices for `dhal_curry`, `fish_curry`, `meat_curry`, `noodles`; regional fallback; the database importers; the gateway route; Flutter.

## 2026-10-16: Trained model wired into the service (opt-in); relish labels fixed

Relabelling (owner decisions, 2026-10-15):
- Owner: the dark relish is lunu sambol / seeni sambol, the red one is lunu miris; the 20 photos I was unsure about are red. New tool `c1_training.relabel` (decision CSV, dry run, backup, 9 tests). Applied `_curation\label_review\lunu_relabel.csv`: 71 rows changed (68 to `lunu_miris`, 3 given both labels), 6 unchanged. Backup `processed_manifest_before_relabel_2026-10-15.csv`. The set became 48 classes (`lunu_sambol`, now only 3 scenes, left); leak audit still 0 of 209 test photos with a copy at 30 or less.
- Retrained three seeds at 256 px (`--tag rl256`): test mAP 0.929 / 0.918 / 0.909 (mean 0.919, SD 0.010), valid 0.942 / 0.930 / 0.948. Not comparable with the earlier rows. `lunu_miris` is still weak (AP 0.454 / 0.521 / 0.608, 6 test photos).

Service (new code in `src/c1_food_nutrition/ml/`):
- `torch_recognizer.py` (`TorchFoodRecognizer`, loads a model bundle with `weights_only=True`, CPU by default, lock around the forward pass), `bundle.py` (format, errors, network builder; no OpenCV), `inference_input.py` (image to model input as in training), `labels.py` and `data/class_concepts.csv` (150 classes to concept ids; loading fails on an unmapped class).
- Settings `RECOGNIZER` (`mock` default, `torch`), `MODEL_PATH` (required for `torch`), `MODEL_DEVICE`. `api/deps.py` loads the model once per process.
- Pipeline: recognition runs in a worker thread; the mock warning now names which stages are mock (the all-mock text is unchanged); an empty result adds "No food was recognised in the image."
- `c1_training.export`: Stage 2 run to model bundle; the threshold (0.85) is chosen on the validation photos only. Bundle: `runs/stage2_mobilenet_v3_large_imagenet_seed2_rl256_bundle.pt`, 17.3 MB, seed 2 chosen for the best validation mAP (0.948).
- README and API doc updated; `training/README.md` has the export and server setup steps.

Checks:
- Project environment: ruff, ruff format, mypy (127 files) clean; pytest 183 passed, 20 skipped (PyTorch tests skip). `uv.lock` and all shared files unchanged.
- Server environment (`D:\RESEARCH PROJECT\c1_server_env`, CPU PyTorch 2.14.1, torchvision 0.29.1, built outside the repo from the frozen lock, about 200 MB download): pytest 202 passed, 1 skipped (scikit-learn not installed). Training environment: 53 passed, 1 skipped.
- A train, export and load round trip test, and tests with random-weight bundles for loading, thresholds, concept ids, bad bundles and the HTTP endpoint.
- Real data: the service recogniser reproduces the training report exactly on the 209 test photos (mAP 0.9090); on full-size originals mAP 0.9047. Real service over HTTP with a public-dataset photo: 200 with items; no image 422, text file named .jpg 415, corrupt JPEG 422, bad meal type 422, 11 MB file 413, `/health` 200. See `EXPERIMENTS.md`.
- Not checked: `MODEL_DEVICE=cuda`, the gateway route, Flutter, concurrent requests, the PNG path with a real food photo.

## 2026-10-15: 256 px default; lunu_sambol labels reviewed

- Owner decision: Stage 2 default input size is now 256 px (`--size`, was 224). New test checks the default. Checks: ruff, ruff format, mypy clean; pytest 157 passed, 6 skipped; 42 of 42 in the training environment. Earlier reports and the baseline numbers in `CONTEXT.md` remain 224 px unless tagged `s256`.
- Owner identified the two flagged photos: one is lunu sambol / seeni sambol, the other lunu miris. Contact sheets of all `lunu_sambol` (77) and `lunu_miris` (11) photos in `_curation\label_review\` show that `lunu_sambol` mixes a red relish (lunu miris) and a dark brown one (seeni sambol). No labels changed. Owner chose to sort by colour; a proposal file for the 77 photos was written to `_curation\label_review\lunu_proposal.csv` (48 red, 6 dark brown, 3 both, 20 unsure) and waits for the owner's check.

## 2026-10-15: Weak classes studied

- Looked at the seven weakest classes (data counts, datasets, test positives, photos). Most are side dishes on mixed plates (100% of their photos have several foods); `lunu_miris` has 7 training photos; test positives are 2 to 8 per class, so per-class scores are noisy.
- Two training changes, `--tag` keeping the baseline files: 25 epochs (3 seeds) made no difference (+0.000, std error 0.011); input 256 px (5 seeds, plus baseline seeds 3 and 4 for pairing) gave +0.009 test mAP (std error 0.004), better on all 5 seeds, mean AP of the seven weak classes 0.668 to 0.715. Suggestive, not proven; the weak classes remain weak.
- Photos reviewed: `lunu_sambol` is a red relish on kiribath and one test photo shows none; `lunu_sambol` and `lunu_miris` look alike (confusion not checked); a flipped pittu copy sits in train. Logged in `OPEN_ITEMS.md`.
- Stage 2 reports now record `size`, `batch_size`, `lr` and `tag` (the 10 runs of this study predate that; the size is taken from the command). Checks: ruff, ruff format, mypy clean; pytest 156 passed, 6 skipped; 41 of 41 in the training environment.
- Default settings unchanged. No data or labels were changed.
- Owner decision: `lunu_sambol` and `lunu_miris` are two different foods. Confusion check (seed 0 checkpoints, 224 and 256 px): the model never scores one on the other's photos. Its five `lunu_sambol` false alarms are hoppers and kiribath test photos; two of them seem to show the relish without the label (logged in `OPEN_ITEMS.md` B for the owner to check).
- EfficientNetV2-S, with the owner's approval of the download (82.7 MB): at batch 32 it filled the 6 GB card and ran at about 210 s per epoch, so that run was stopped. At batch 16 (3 seeds) test mAP 0.925 / 0.875 / 0.909, mean 0.903, against 0.914 for MobileNetV3 at batch 16 (paired −0.010, std error 0.010). Better on the seven weak classes (0.770 against 0.685), worse on the other 42 (0.929 against 0.958). MobileNetV3-Large stays.

## 2026-10-15: Cleaning and training code moved into the repo

- New package `src/c1_training/` (typed, mypy strict): `paths` (`C1_DATA_DIR` / `--data-dir`), `manifest`, `metrics` (numpy AP, mAP, micro-F1), `fingerprint`, `leak`, `leak_audit`, `leak_fix`, `cleaning`, `preprocess`, `model`, `stage1`, `stage2`, `check_setup`. Pillow and PyTorch are imported inside functions; neither is a service dependency, and `uv.lock` is unchanged. The C1 `pyproject.toml` now builds both packages.
- `training/README.md` (setup, commands, differences from the old scripts) and `training/requirements.txt` (training environment only).
- 41 tests in `training/tests/` on small generated images. Repo environment: 35 pass, 6 skip (they need Pillow, scikit-learn or PyTorch). Training environment: 41 pass, including a 1-epoch Stage 2 smoke test and a check that the numpy metrics equal scikit-learn's.
- Full repo checks: ruff, ruff format and mypy clean; pytest 156 passed, 6 skipped (121 before).
- Real-data checks against the old scripts: same manifest set (2,113 images, 49 classes); clean-manifest roles identical for all 9,217 rows; resized copies byte-identical for 40 of 40 sampled; leak-audit distance and closest photo identical for all 471 valid/test images.
- Full Stage 2 run with the repo code (ImageNet start, seed 0, clean-49, into a scratch folder): test mAP 0.906, micro-F1 0.868, against 0.910 / 0.872 from the old script. The first epochs already differed slightly (GPU non-determinism), so this is within normal run-to-run variation.
- Behaviour changes: `--out-dir` and `--tag` for Stage 1 and 2; Stage 1 is seeded (`--seed`, default 0); `leak_audit --min-scenes`; `preprocess` keeps rows dropped by the leak fix; Stage 2 reports record the manifest path.
- Not moved: `build_curation.py`, `make_class_map.py`, `process_food101.py`. The old scripts outside git were left in place.
- Installed pytest (about 1 MB) in `.venv311` to run the tests there.

## 2026-10-15: Out-of-date docs fixed

- `SKILL.md`: torchvision instead of timm, MobileNetV3-Large baseline, JSON reports instead of MLflow, DVC marked as not set up, the folder layout as it is, the reconstructed Food-101 split, the Sri Lankan sets and their size, the approach as built with the Stage 1 comparison, the repaired nutrition table, and a note that the draft contract names differ from the code.
- `docs/ROADMAP.md`: status table for 2026-10-15; the model item rewritten as built; old-branch banner replaced.
- `training/configs/README.md`: old-branch banner removed; status of each folder.
- Still open in `OPEN_ITEMS.md` E: the contract names (`SKILL.md` section 4), Albumentations and Pillow mentions.

## 2026-10-15: Task playbooks and experiment log

- Added `docs/tasks/` with a README and seven playbooks: Stage 2 experiment, leak audit and fix, weak classes, moving training into the repo, wiring the recogniser, nutrition importers, portion estimation.
- Rebuilt `EXPERIMENTS.md` from the report files in `runs/`, `runs_backup_2026-10-15/` and `runs_quicktest_py311/`; Stage 1 values have no report file and are marked unverified.
- Found while writing: `_curation\scripts\preprocess_images.py` rebuilds `processed_manifest.csv` and would undo the leak fix; the code's source codes and portion methods differ from `SKILL.md`. Logged in `OPEN_ITEMS.md`.

## 2026-10-15: Fair comparison, Food-101 start against ImageNet start

- Ran Stage 2 with `--stage1 runs\stage1_mobilenet_v3_large.pt --min-scenes 5`, seeds 0, 1, 2, on the cleaned 49-class split (same split and settings as the re-run baseline). 310 of 312 tensors loaded from Stage 1 (only the final layer skipped).
- Test mAP 0.913 / 0.892 / 0.889, mean 0.898 (SD 0.013), against 0.916 (SD 0.006) for the ImageNet start. Micro-F1 mean 0.896 against 0.892. The Food-101 start did not improve test mAP.
- The old 78-class Food-101-start files in `runs\` were overwritten; copies are in `runs_backup_2026-10-15\`.

## 2026-10-15: Leak audit and fix

- `leak_audit.py` on the `--min-scenes 5` set: 20 of 223 test images (9%) and 36 of 278 valid images had a train photo at fingerprint distance ≤ 30; the reference for different-scene train pairs was 2%. All 20 test pairs were checked by eye: real copies (19 Kaggle-26, 1 sl_meal).
- Added `_curation\training\leak_fix.py` (outside git). With the owner's approval, applied it at ≤ 30: 65 train rows set to `leak_dropped` (62 Kaggle-26, 3 sl_meal). Backup `processed_manifest_before_leakfix_2026-10-15.csv`. Set is now 51 classes, 2,221 images (1,720 / 278 / 223); `pumpkin_curry` fell below 5 train scenes.
- Re-audit: 0 test and 0 valid images at ≤ 30, but copies remained at 31–48 (checked by eye); above about 49 the matches were mostly different foods.
- Second pass, approved by the owner: distance ≤ 48 and same labels, 37 more train rows `leak_dropped` (35 Kaggle-26, 2 food_detect). Backup `processed_manifest_before_leakfix48_2026-10-15.csv`. `fanta` and `iced_coffee` fell below 5 train scenes. Set is now 49 classes, 2,113 images (1,642 / 262 / 209). Manifest: 6,780 `keep`, 138 `leak_dropped`. Re-audit: 0 of 209 test at ≤ 30, 1 at ≤ 40.
- Re-ran the three ImageNet baselines on the cleaned split: test mAP 0.910 / 0.922 / 0.915, mean 0.916 (previous leaky 52-class mean 0.942). Old reports kept in `runs_backup_2026-10-15\`.

## 2026-10-15: Python 3.11 training environment

- Built `.venv311` in `_curation\training\` (Python 3.11.17, torch 2.14.1+cu126, torchvision 0.29.1+cu126, numpy 2.4.6, scikit-learn 1.9.1, pillow 12.3.0). The torch download was 2,602.8 MB.
- `check_setup.py`: GPU OK (RTX 3050 6 GB), 2,286 Sri Lankan images in 52 classes, 0 missing files, Food-101 split lists found (`setup_result.txt`).
- Quick tests: Stage 1 top-1 0.111, 0.140, 0.101 over three runs (3.13 reference 0.155; Stage 1 is unseeded); Stage 2 test mAP 0.561 (3.13 reference 0.552). See `EXPERIMENTS.md`.
- Backed up `runs\` before the quick tests because they overwrite real run files; restored the originals and checked all 13 by hash.
- Closed: "Re-run the quick tests on Python 3.11". Opened: Stage 1 selects its epoch on the test set, Stage 1 is unseeded, quick tests overwrite real runs, Food-101-start runs will overwrite the 78-class reports, clean-up of old folders.
- `CONTEXT.md`, `DATA.md`, `GLOSSARY.md` and `OPEN_ITEMS.md` written; `AGENTS.md` and `CLAUDE.md` each gained one line pointing to `docs/CONTEXT.md`.

## 2026-10-14: Windows GPU training, Stage 1 and first Stage 2 runs (outside git)

- Training set up on Python 3.13 with GPU support.
- Stage 1 full run on Food-101, 8 epochs: top-1 0.828 [UNVERIFIED: no report file; weights `runs\stage1_mobilenet_v3_large.pt` dated 2026-10-14].
- Stage 2 ImageNet start, 52 classes, seeds 0 to 2: test mAP 0.955 / 0.945 / 0.925. Stage 2 Food-101 start, 78 classes, seeds 0 to 2: 0.917 / 0.908 / 0.901. Reports now in `runs_backup_2026-10-15\`. Both later found to be on a leaky split.

## 2026-10-13: Image cleaning, preprocessing, Food-101 (outside git)

- From `_curation\CLEANING_NOTES.md`: 2 FoodBD rows `missing_file`, 1 veg-cooking photo `unreadable`, 36 rows `leak_dropped` (14 scene groups in more than one split; the valid/test copy kept); 46 images converted to RGB. All `keep` rows resized (short side 256 px).
- Food-101 processed with a reconstructed 75/25 split by scene group (counts in `CONTEXT.md` section 7, from `_curation\food101_report.json` [UNVERIFIED: not re-read]).

## 2026-10-13: Meal Scan screen and portion editing (repo)

- `48a0407` Add Meal Scan screen (C1); merged in PR #3 (`c291bac`).
- `71c2e01` Add portion editing and update the meal result view.

## 2026-10-10: Image curation (outside git)

- Manifest, duplicate detection and class map built (`_curation\image_manifest.csv`, `duplicates_report.csv`, `class_map.csv`) [UNVERIFIED: dates from file times].

## 2026-10-08: Monorepo, C1 service and docs (repo)

- `6aaf73a` C1 to C4 service skeletons; `02ca0bb` useful code brought over from the old `c1_kavithi` branch; `5c6d2fc` `AGENTS.md`, `SKILL.md` and `CLAUDE.md` for C1.
- Sri Lankan nutrition tables built and repaired; ADR 0002 (secondary datasets only) [nutrition work outside git; UNVERIFIED].
- `CONTEXT.md` gives 2026-10-03 for the scaffold and roadmap; the git log shows 2026-10-08 for the repo commits [dates differ, UNVERIFIED which is right].
