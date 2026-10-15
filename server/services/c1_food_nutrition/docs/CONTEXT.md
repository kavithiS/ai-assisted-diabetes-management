# C1 context: start here

**Last updated:** 2026-10-15 · **Owner:** Thilakarathne K.S (IT23295742) · **Branch:** `c1-kavithi`

Read this file first in every new session, then `../AGENTS.md` (rules), then `OPEN_ITEMS.md`. Numbers come from report files and the source is named beside them. Anything marked **[UNVERIFIED]** was not re-checked when this was written. If a fact here disagrees with the code or a report file, trust the file and fix this page.

## 0. Using this file in VS Code Insiders

1. Open the repo folder `D:\ai-assisted-diabetes-management`.
2. Add the data folder to the same window (File > Add Folder to Workspace): `D:\RESEARCH PROJECT\Foods datasets for training`. Until the scripts are moved into the repo, the data scripts and training code live there, under `Images Datasets\_curation\`.
3. Start an agent session with the prompt in section 14, and end it with the checklist there.

## 1. What C1 is

Component 1 of DiaCare AI (J26-IT-352), a research prototype for Sri Lankan diabetes care. C1 takes a meal photo, recognises the foods (several can be on one plate), estimates each portion in grams, looks up nutrition (Sri Lankan composition data first, USDA as fallback) and returns a `meal_nutrition` JSON for C2, C3 and the app. The app is a **Flutter mobile app** (Android and iOS). There is no web app. Team: C1 (owner), C2 `c2_nethmi`, C3 `c3_lochana`, C4 `c4_guwindu`; the repo is `kavithiS/ai-assisted-diabetes-management`.

## 2. The owner and how to work with them

- New to model training. Wants plain words and step-by-step commands, one thing at a time. Windows 11 laptop (RTX 3050 6 GB), Command Prompt or PowerShell, **mobile data**: ask before any download over about 50 MB and say the size.
- **Never** commit, push or open pull requests. Give commit messages only. **Never** put any tool, vendor or AI attribution in commit messages, code or docs.
- Do not assume: ask when something is unclear. Never claim "ready" or "done" without running the check; say what was not checked.
- Work only in `server/services/c1_food_nutrition/`, `data/c1/` and the Meal Scan feature. Shared files (root `pyproject.toml`, `uv.lock`, `.env.example`, CI, `contracts/`, `server/shared/`, gateway) are not changed without being asked.

## 3. State at a glance

| Area | Status |
|---|---|
| Backend scaffold (FastAPI, schemas, DB models, migrations, mock recognizer, tests) | Done (Phase 0). Tests not re-run when this was written. |
| Nutrition importers (USDA, MRI Sri Lanka) | Stubs [UNVERIFIED since the ROADMAP, 2026-10-03] |
| Flutter Meal Scan screen and portion editing | Done and merged |
| Image dataset cleaning and preprocessing (7 datasets + Food-101) | Done |
| Nutrition table cleaning (2,716 foods) | Done; items awaiting the publisher and supervisors |
| Training environment | **Python 3.11 (`.venv311`) set up and checked on 2026-10-15**: torch 2.14.1+cu126, GPU OK, data loads, both quick tests run. Use `.venv311` from now on; the old 3.13 `.venv` is not deleted yet |
| Stage 1 (Food-101 pretraining) | Done: 82.8% top-1 |
| Leak audit and fix | **Done 2026-10-15.** 9% of test images had a train copy; two fix passes dropped 102 train copies; 0 test images left with a copy at ≤ 30. Set is now 49 classes |
| Stage 2 baseline (ImageNet start, 3 seeds) | **Re-run 2026-10-15 on the cleaned 49-class split**: test mAP 0.916 mean. The old 52-class numbers (0.942) were on the leaky split |
| Stage 2 with Food-101 start, same 49 classes, 3 seeds | **Done 2026-10-15**: test mAP 0.898 mean, against 0.916 for the ImageNet start. No sign that the Food-101 start helps at this setting |
| Training code in the repo | **Done 2026-10-15**: package `src/c1_training/` (typed), tests in `training/tests/`, how-to in `training/README.md`. PyTorch is not a service dependency. Checked against the old scripts on the real data. `build_curation.py`, `make_class_map.py`, `process_food101.py` not moved yet |
| Trained model wired into the API; portion estimation | Not started (playbooks in `docs/tasks/`) |
| Docs: task playbooks, experiment log, changelog | Done 2026-10-15 (`docs/tasks/`, `EXPERIMENTS.md`, `CHANGELOG.md`) |

## 4. Timeline

- 2026-10-03: monorepo scaffold, Phase 0 done; roadmap written.
- 2026-10-08: Sri Lankan nutrition tables built and repaired; ADR 0002 (secondary datasets only).
- 2026-10-10: image curation (manifest, duplicates, class map).
- 2026-10-13: broken files and leaking scene groups fixed (clean manifest); all images preprocessed; Food-101 processed.
- 2026-10-14: Windows GPU training set up; Stage 1 full run; Stage 2 baselines; first Stage 2 runs with the Food-101 start (78 classes).
- Meal Scan screen merged (PR #3), then portion editing (`71c2e01`).
- 2026-10-15: these docs written; Python 3.11 training environment built (`.venv311`) and checked with both quick tests.

## 5. Backend (`server/services/c1_food_nutrition/`)

- Port 8001. `GET /health`; `POST /v1/meals/analyze` (the gateway exposes `/api/v1/meals/analyze`). Recognition is a **mock** (`ml/mock.py`); responses carry `is_mock: true`.
- `services/` has `image_validation`, `nutrition`, `pipeline`; `schemas/` is a package; DB layer and Alembic migration `20261003_78ab001a889d` in `db/`; 11 test files in `tests/`.
- Rules: an unknown nutrient is `null`, never `0`; `recognition_score` is never shown to patients; the request contract is ADR 0004 (the `reference_object` format is still open with C4).

## 6. Flutter app (`client/mobile_app/lib/features/meal_scan/`)

- Screen, API client, models, result view, portion-edit dialog. 4 test files in `client/mobile_app/test/features/meal_scan/`. The owner ran the analyzer and tests earlier; re-run before relying on that.
- Decisions: portion scaling is done in the app (`newGrams / oldGrams`); unknown nutrient shows "Not available"; model confidence is never shown; totals are recomputed with `NutrientProfile.sum` after an edit.

## 7. Image data (outside git; details in `DATA.md`)

- 7 datasets (9,217 images) plus Food-101 (101,000). Originals untouched; derived files only.
- Clean manifest: 6,882 `keep` rows; 2 `missing_file`, 1 `unreadable`, 36 `leak_dropped` (14 scene groups had sat in more than one split; the test/valid copy was kept). All 6,882 preprocessed (RGB, short side 256 px, no upscaling), 0 errors.
- 2026-10-15 leak fix (`_curation\training\leak_fix.py`), two passes, both approved by the owner. Pass 1: 65 train rows set to `leak_dropped` (near-copies of a valid/test photo, fingerprint distance ≤ 30; 62 Kaggle-26, 3 sl_meal). Pass 2: 37 more (distance ≤ 48 **and** same labels; 35 Kaggle-26, 2 food_detect). Manifest now: 6,780 `keep`, 138 `leak_dropped`. Backups: `_curation\processed_manifest_before_leakfix_2026-10-15.csv` (before pass 1) and `..._before_leakfix48_2026-10-15.csv` (before pass 2). Only the `--min-scenes 5` set was checked.
- Food-101: 100,895 kept; 95 near-duplicates, 6 exact and 4 cross-class duplicates removed. Official split lists are missing, so a **reconstructed 75/25 split by scene group** is used: train 75,658, test 25,237.
- Sri Lankan training set (food_detect, shorteats, sl_meal, kaggle_sl26; 88 clean classes if veg_cooking is added): `--min-scenes 1` keeps **78 classes**, 2,320 images (train 1,807, valid 287, test 226). `--min-scenes 5` kept **52 classes**, 2,286 images (1,785 / 278 / 223) before the 2026-10-15 leak fix; after both passes, **49 classes**, 2,113 images (train 1,642 / valid 262 / test 209): `pumpkin_curry` (pass 1), `fanta` and `iced_coffee` (pass 2) fell under 5 train scenes. The `--min-scenes 1` counts after the fix are [UNVERIFIED].
- Thin data: only 23 classes have 30+ scenes and 5 have 50+. Kaggle-26 is mostly mirror copies (about 298 distinct scenes in 2,600 files).

## 8. Nutrition data

- `data/c1/c1_foods_combined.csv` (gitignored): 2,716 foods per 100 g, 36 columns (241 Sri Lankan, 2,475 related from 8 regional tables). The Sri Lankan export had every "na" replaced by "100"; repaired. B12 and vitamin D blanked pending the publisher. 77 self-contradictory foods excluded. **No sugars column.**
- `carbohydrate_g` is available carbohydrate (fibre excluded). Lookup: concept (`food_concepts.csv`, 118) then lowest `lookup_priority_in_concept` (`food_metadata.csv`).
- Conflict: `AGENTS.md` section 4 allows only the Sri Lankan table and USDA; using the regional tables needs supervisor sign-off (`OPEN_ITEMS.md` A1).

## 9. Training code

**Since 2026-10-15 the code is in the repo:** package `server/services/c1_food_nutrition/src/c1_training/`, tests in `training/tests/`, commands and setup in `training/README.md`. Run it in the training environment with `C1_DATA_DIR` set to the `Images Datasets` folder and `PYTHONPATH` set to the C1 `src` folder, for example `python -m c1_training.stage2 --min-scenes 5 --seed 0`. Differences from the old scripts are listed in `training/README.md` (`--out-dir`/`--tag`, a Stage 1 seed, numpy metrics, `leak_audit --min-scenes`, and `preprocess` no longer undoing the leak fix).

The old scripts below, in `Images Datasets\_curation\training\` and `_curation\scripts\`, still exist and still work; they are kept for reference until the owner removes them.

| Old file | Purpose |
|---|---|
| `common.py` | `load_manifest(datasets, min_train_scenes)` reads `processed_manifest.csv`; `SL_SETS = food_detect, shorteats, sl_meal, kaggle_sl26` |
| `model.py` | `build_model(arch, n_out, pretrained)`, `load_backbone(m, path)`; archs `mobilenet_v3_large` (used so far), `efficientnet_v2_s` (available, not yet run) |
| `stage1_pretrain_food101.py` | Food-101, 101 classes, cross-entropy with label smoothing 0.1, AdamW (lr 1e-3, wd 1e-4), OneCycle, batch 32, 224 px, default 5 epochs. Saves `runs/stage1_<arch>.pt` |
| `stage2_finetune_srilankan.py` | Multi-label: BCE with per-class `pos_weight`, AdamW lr 5e-4, OneCycle, 15 epochs, flips and colour jitter; best epoch by valid mAP; test scored once. Saves `runs/<tag>.pt` and `<tag>_report.json` (config, split sizes, mAP, micro-F1, per-class AP weakest first) |
| `leak_audit.py` | For each valid/test image, the distance to the closest train image (also mirrored); prints counts at 10/20/30/40 and the 8 closest pairs; writes `leak_audit.csv` |
| `leak_fix.py` | Sets `role = leak_dropped` on train photos within `--max-dist` of a valid/test photo (`--same-labels` to require equal labels). Dry run by default; `--apply` backs up `processed_manifest.csv` first |
| `check_setup.py`, `setup_training.bat`, `setup_training_py311.bat` | Environment check and setup (the second builds `.venv311`, about 2.5 GB download) |

Arguments: Stage 1 `--arch --epochs --per-class --bs --lr --size --workers`; Stage 2 `--arch --stage1 --also --min-scenes --epochs --bs --lr --size --workers --seed`. Run names look like `stage2_mobilenet_v3_large_<imagenet|food101>_seed<N>`; runs never overwrite each other (a later run with the same name does).

Timings on the RTX 3050: Stage 1 about 320 to 550 s per epoch on the full set (one epoch took 2,169 s when the PC was busy); Stage 2 about 9 s per epoch after a ~110 s first epoch, so 3 to 5 minutes per run.

Windows notes: `DataLoader` workers need the `if __name__ == "__main__"` guard (already in place); use `--workers 0` if a multiprocessing error appears. Weights (`runs\*.pt`) stay out of git.

## 10. Results so far

Test mAP on held-out scenes (mean of 3 seeds in brackets). Source: `runs/*_report.json`.

| Run | Classes | Seeds 0 / 1 / 2 | Notes |
|---|---|---|---|
| Stage 1, Food-101, 8 epochs, full | 101 | top-1 0.828 | 3-epoch quick test on 300 per class: 0.761 |
| **Stage 2, ImageNet start, cleaned split (current baseline)** | 49 (`--min-scenes 5`, after leak fix) | 0.910 / 0.922 / 0.915 (**0.916**, SD 0.006) | micro-F1 0.872 / 0.899 / 0.906 (0.892). Split 1,642 / 262 / 209 |
| **Stage 2, Food-101 start, cleaned split** | 49 (same split as above) | 0.913 / 0.892 / 0.889 (**0.898**, SD 0.013) | micro-F1 0.892 / 0.902 / 0.895 (0.896). 310 of 312 backbone tensors loaded from `runs/stage1_mobilenet_v3_large.pt` |
| Stage 2, ImageNet start, leaky split (superseded) | 52 (`--min-scenes 5`) | 0.955 / 0.945 / 0.925 (0.942, SD 0.015) | micro-F1 0.914 / 0.911 / 0.907. Reports kept in `runs_backup_2026-10-15/` |
| Stage 2, Food-101 start, leaky split (superseded) | 78 (`--min-scenes 1`) | 0.917 / 0.908 / 0.901 (0.909) | **Not comparable** (different classes, leaky split). Reports in `runs_backup_2026-10-15/` |

The drop from 0.942 to 0.916 mixes two effects: the copies were removed, and the class set and test set changed (52 to 49 classes, 223 to 209 test images; `fanta` and `iced_coffee`, the most copy-heavy, are gone). It cannot be split between the two. SD is the sample standard deviation over the 3 seeds, worked out from the report files.

Fair comparison (same 49 classes, split and settings): Food-101 start minus ImageNet start, per seed, test mAP +0.003 / −0.030 / −0.026 (mean −0.018); micro-F1 +0.020 / +0.003 / −0.011 (mean +0.004). With three seeds this is not a significant difference either way; the honest reading is that pre-training on Food-101 (reconstructed split, 8 epochs) **did not improve** test mAP here. Valid mAP was similar (0.956 / 0.950 / 0.939 against 0.951 / 0.921 / 0.948).

Quick tests, Python 3.13 (earlier) against Python 3.11 (2026-10-15):

| Quick test | 3.13 | 3.11 | Source of the 3.11 number |
|---|---|---|---|
| Stage 1 `--epochs 1 --per-class 20` (top-1, 606 test images) | 0.155 | 0.111 / 0.140 / 0.101 (three runs) | console output; Stage 1 writes no report file |
| Stage 2 `--epochs 1 --min-scenes 5 --workers 2` (test mAP, seed 0) | 0.552 | 0.561 (micro-F1 0.627) | `runs_quicktest_py311/stage2_mobilenet_v3_large_imagenet_seed0_report.json` |

Stage 1 sets no random seed, so 1-epoch runs vary by about 0.04 between runs on the same setup; the 3.13 value is inside that range. Read: the 3.11 environment behaves like the 3.13 one. The quick tests write to the same file names as the real runs, so `runs/` was backed up first (`runs_backup_2026-10-15/`), the quick-test files were moved to `runs_quicktest_py311/` and the originals restored (all 13 files checked identical by hash).

Leak audit (console output of `leak_audit.py`, details in `_curation\training\leak_audit.csv`):

| When | Set | Test with a train copy (≤ 30) | Valid with a train copy (≤ 30) | Reference: different-scene train pairs ≤ 30 |
|---|---|---|---|---|
| Before fix | 52 classes, 2,286 images | 20 of 223 (9%) | 36 of 278 | 2% |
| After pass 1 (≤ 30) | 51 classes, 2,221 images | 0 of 223 | 0 of 278 | 1% |
| After pass 2 (≤ 48, same labels) | 49 classes, 2,113 images | 0 of 209 (1 at ≤ 40) | 0 of 262 | 1% |

All 20 flagged test pairs were checked by eye and were real copies (19 Kaggle-26, 1 sl_meal). After pass 1, the 7 test pairs at 31–40 and the pairs at 41–48 were also copies; from about 49 up the closest matches are mostly different foods with a similar layout, which is why pass 2 also requires equal labels.

Caveats: the test set is small (209 images; the weakest classes have only 1 to 5 positives); the fingerprint audit can miss copies that are cropped or shifted more than it can see, so a small leak may remain; the Food-101 split is reconstructed, so do not compare with published numbers. Weakest classes on the cleaned split, ImageNet start (AP, test positives): seed 0 lunu_sambol 0.297 (3), fish_curry 0.593 (5), pol_sambol 0.611 (2); seed 1 submarine 0.2 (1), lunu_sambol 0.356 (3), lunu_miris 0.577 (3); seed 2 bean_curry 0.5 (1), pappadam 0.5 (1), lunu_miris 0.643 (3). With 1 to 5 positives these per-class values are very noisy.

## 11. Next steps, in order

1. ~~**Python 3.11 env.**~~ Done 2026-10-15 (see section 10).
2. ~~**Leak audit.**~~ Done 2026-10-15: two fix passes, baselines re-run (see section 10).
3. ~~**Fair comparison.**~~ Done 2026-10-15: Food-101 start 0.898 against ImageNet start 0.916 (see section 10).
4. Study the weakest classes; try longer training, `--arch efficientnet_v2_s`, or more photos for thin classes.
5. ~~Move the scripts into the repo.~~ Done 2026-10-15 (section 9); the three curation scripts are still outside.
6. Wire the model behind `FoodRecognizer`; map each class to a nutrition row (`class_map.csv` has concept ids; add a test that every class maps); then portion estimation.

## 12. Decisions already made

Secondary datasets only (ADR 0002). Split by scene group, never by file. Multi-label (sigmoid + BCE with positive weights). Two-stage training compared with and without Stage 1 over three seeds. Compare runs only when classes, split and settings match. Report mean and spread. `null` is not `0`. Confidence is never shown to patients. Portion scaling lives in the app. The UI is a mobile app, so no web build and no browser tests.

## 13. Where things live

| What | Where |
|---|---|
| Service code and tests | `server/services/c1_food_nutrition/` |
| Training and data code; its tests and how-to | `src/c1_training/`; `training/tests/`, `training/README.md` |
| This page, open items, data card, glossary, changelog, experiment log | `server/services/c1_food_nutrition/docs/` |
| Step-by-step playbooks per task | `server/services/c1_food_nutrition/docs/tasks/` |
| Decisions | `docs/adr/` here (0004) and at the repo root (0001 to 0003) |
| Flutter feature and tests | `client/mobile_app/lib/features/meal_scan/`, `client/mobile_app/test/features/meal_scan/` |
| Nutrition table (gitignored) | `data/c1/c1_foods_combined.csv` |
| Image data, manifests, old scripts, runs (outside git) | `D:\RESEARCH PROJECT\Foods datasets for training\Images Datasets\` (`_curation`, `_processed`) |
| Food tables and their README | `D:\RESEARCH PROJECT\Foods datasets for training\c1_sri_lanka_food_data\` |

## 14. Build, test and session routine

Definition of done (run what applies, paste the results):
```
uv sync
uv run ruff check . ; uv run ruff format --check . ; uv run mypy server ; uv run pytest
cd client/mobile_app ; flutter analyze ; flutter test
```
Data scripts: tests on small generated images, then a real-data check. Training code: a 1-epoch smoke test. UI: Flutter widget tests, then a manual run on an emulator or phone.

**Prompt to start a session:** "Read server/services/c1_food_nutrition/docs/CONTEXT.md, AGENTS.md and docs/OPEN_ITEMS.md. Tell me in five lines where we are and what you suggest next. Ask me before assuming anything. Do not commit or open PRs."

**End of session:** update section 3 and 10 here if state changed, move closed items out of `OPEN_ITEMS.md`, add a `CHANGELOG.md` entry and an `EXPERIMENTS.md` row for each run, then give commit messages (no attribution).
