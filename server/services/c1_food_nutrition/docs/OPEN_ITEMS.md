# C1 open items

**Last updated:** 2026-10-15. Remove an item when it is closed and log it in `CHANGELOG.md`. Add new ones here.

## A. Decisions needed from someone else

| # | Item | Who | Why it matters |
|---|---|---|---|
| A1 | Use the regional nutrition tables (Bangladesh, Malaysia, FAO, Nepal ...) as fallbacks | Supervisors | `AGENTS.md` section 4 allows only the Sri Lankan table and USDA. The `nutrition_source` enum in the contract would need to change. |
| A2 | Vitamin B12 (looks 1,000x too high) and vitamin D (implausible values) in the Sri Lankan export | Publisher of the database (Opatha et al., 2025) | Both columns are blanked until confirmed. The original values are in `value_flags.csv`. |
| A3 | Final `reference_object` format | C4 | Breaking change to the request contract (ADR 0004). |
| A4 | Approval of `meal_nutrition` v1 | C2 and C3 | They consume C1's output. |
| A5 | Evaluation targets | Supervisors | The TAF sets none, so no target may be written into code or docs. |
| A6 | Show patients a band ("High", "Medium") instead of a percentage? | Supervisors | Affects the UI. |
| A7 | Use Nutrition5k? | Supervisors | Not confirmed. |
| A8 | GitHub usernames for `CODEOWNERS` | All members | The file is still commented out. |
| A9 | C3's request to add a mypy override to the root `pyproject.toml` | Owner | Status [UNVERIFIED]. It touches a shared file. |

## B. Data issues

- 4 class labels are unclear: `spunchi`, `vorta`, `burinda`, `kabab`.
- Licences not verified: FoodBD, Kaggle-26 (not stated on its page), veg-cooking (dataset licence). PUST's DOI is not filled in. Do not redistribute any dataset.
- Food-101 official split lists (`meta/train.txt`, `meta/test.txt`) are missing. The reconstructed split is used. Download the official lists if you want benchmark-comparable numbers.
- About 20 mirror pairs in Kaggle-26 were not detected, so some folders keep 51 or 52 images instead of 50.
- Kaggle-26 scene groups (`#gNN`) do not match real scenes: the same cup, cutlet or pizza appears in several groups, so copies cross splits. The leak audit found 19 of its 176 test photos with a train copy at ≤ 30.
- Short-eats has labels only in its train annotation file.
- Few photos per class: only 23 classes have 30 or more scenes and 5 have 50 or more. 33 of the 118 food concepts have no images. The TAF targets (50+ categories, 10,000+ images) are not met by the Sri Lankan sets.
- The nutrition table has **no sugars column**.
- FoodBD `gl_reported` is unreliable and must not be used.
- `veg_cooking` is excluded from training by default (use `--also`).

## C. Experiments

- The Food-101 start did not beat the ImageNet start (0.898 against 0.916 test mAP, 3 seeds each). Decide whether two-stage training stays in the plan, or try it differently (for example a lower learning rate or a frozen backbone for the first epochs in Stage 2); ask the supervisors how to report it.
- The leak fix was checked only on the `--min-scenes 5` set; audit the `--min-scenes 1` set too before using it.
- `pumpkin_curry`, `fanta` and `iced_coffee` dropped out of the `--min-scenes 5` set after the leak fix (under 5 train scenes). They need more distinct photos to come back.
- The fingerprint audit only catches near-identical framing; a stronger check (for example image embeddings) could find cropped or rotated copies.
- Inspect weakest classes in each `runs/*_report.json` (per-class AP, with test positives).
- Stage 1 keeps the epoch with the best **test** top-1 (there is no validation split), so its 0.828 is slightly optimistic. Consider a validation split taken from train.
- Same seed is not the same result on the GPU (`cudnn.benchmark` is on): the repo version's first epochs differed from the old script's in the third decimal. Report means over seeds, not single runs.
- Decide on longer training, a bigger model or more data for thin classes.

## D. Engineering

- Move the remaining curation scripts into `c1_training` (`build_curation.py`, `make_class_map.py`, `process_food101.py`). The cleaning and training scripts were moved on 2026-10-15.
- Stage 1 has no validation split: it still keeps the epoch with the best **test** top-1.
- Once the owner is happy with the repo version, remove or archive the old scripts in `_curation\training\` and `_curation\scripts\` (outside git).
- Implement the USDA and MRI importers (the MRI importer must reject a header of `food_100me`).
- Wire the trained model behind `FoodRecognizer`; map classes to nutrition rows; add a test that every class maps.
- Portion estimation (reference card), replacing the mock estimator.
- Optional: emulator or device integration tests for the Meal Scan screen.
- `AGENTS.md` mentions DVC; it is not set up.
- **The old `_curation\scripts\preprocess_images.py` undoes the leak fix** if re-run (it rebuilds `processed_manifest.csv`). Use `python -m c1_training.preprocess` instead, which keeps the leak-fix drops.
- An untracked junk file sits in the repo root (a mangled PowerShell command in its name). Delete it when convenient.
- Clean-up outside git, in `_curation\training\`, once the owner agrees: the old Python 3.13 `.venv`, `runs_backup_2026-10-15\` (copy of `runs\` before the 3.11 quick tests) and `runs_quicktest_py311\` (quick-test outputs), plus the `*.bak_*` script copies. Keep the two manifest backups (`_curation\processed_manifest_before_leakfix_2026-10-15.csv`, `..._before_leakfix48_2026-10-15.csv`) until the owner is sure the fix is final.

## E. Docs that are out of date (fix, do not trust)

Fixed on 2026-10-15: `SKILL.md` sections 1, 2, 3, 6 and 8, `docs/ROADMAP.md` and `training/configs/README.md` (see `CHANGELOG.md`). Still open:

| File | Says | Reality |
|---|---|---|
| `SKILL.md` section 4 | `nutrition_source` is `SL_FCDB` or `USDA_FDC`; `portion_method` is `reference_card`, `default_serving` or `user_edited` | The code (`schemas/nutrition.py`, `schemas/meal_analysis.py`) uses `MRI_SL_FCDB`, `USDA_FDC`, `MOCK` and `mock`, `reference_object`, `model`. Which one is intended is open (contract change needs C2 and C3) |
| `SKILL.md` sections 2 and 5 | Albumentations for augmentation; Pillow for decoding | Training uses torchvision transforms; the service decodes with OpenCV (`ml/preprocessing.py`) |
