# C1 changelog

Newest first. One entry per piece of work. Numbers come from the files named beside them. Entries before 2026-10-15 were written afterwards from the git log (repo work, commit hash given) and from `CONTEXT.md` section 4 and `_curation\CLEANING_NOTES.md` (work outside git); those not backed by a commit or a file are marked [UNVERIFIED].

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
