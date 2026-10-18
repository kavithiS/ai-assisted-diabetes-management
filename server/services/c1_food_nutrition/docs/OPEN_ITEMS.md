# C1 open items

**Last updated:** 2026-10-18. Remove an item when it is closed and log it in `CHANGELOG.md`. Add new ones here.

## A. Decisions needed from someone else

| # | Item | Who | Why it matters |
|---|---|---|---|
| A1 | Use the regional nutrition tables (Bangladesh, Malaysia, FAO, Nepal ...) as fallbacks | Supervisors | `AGENTS.md` section 4 allows only the Sri Lankan table and USDA. The `nutrition_source` enum in the contract would need to change. **Not used since 2026-10-16**: the lookup skips all regional rows. 1 of the model's 22 food concepts (`sweets_traditional`: asmi, kokis, konda kewum, mun kewum) has only a regional row, so those 4 foods stay unknown. |
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
- **Relish relabelling done (2026-10-15)**: `lunu_sambol` (dark seeni sambol) and `lunu_miris` (red relish) are two classes; 71 photos were relabelled (`CONTEXT.md` section 3). Left over: (a) `lunu_sambol` has only 6 photos from 3 scenes, so it is **not in the model**; seeni sambol needs more photos (new source: licence check, ADR 0002) or a decision to drop it; (b) `lunu_miris` is still the second-weakest class (AP 0.53, 6 test photos) because it mixes a relish on kiribath with a side relish on rice plates; consider whether those are two classes; (c) the two test photos the owner identified (`a41516090fb3d349.jpg` seeni sambol with hoppers, `a4de1d8be084b534.jpg` lunu miris with kiribath) are labelled `hoppers` and `kiribath` only; add the relish labels if wanted.
- A flipped copy of the same pittu picture sits in train (seen in the weak-class review). Other flipped copies inside train may exist; they do not leak into valid/test but count twice in training.
- Licences not verified: FoodBD, Kaggle-26 (not stated on its page), veg-cooking (dataset licence). PUST's DOI is not filled in. Do not redistribute any dataset.
- Food-101 official split lists (`meta/train.txt`, `meta/test.txt`) are missing. The reconstructed split is used. Download the official lists if you want benchmark-comparable numbers.
- About 20 mirror pairs in Kaggle-26 were not detected, so some folders keep 51 or 52 images instead of 50.
- Kaggle-26 scene groups (`#gNN`) do not match real scenes: the same cup, cutlet or pizza appears in several groups, so copies cross splits. The leak audit found 19 of its 176 test photos with a train copy at ≤ 30.
- Short-eats has labels only in its train annotation file.
- Few photos per class: only 23 classes have 30 or more scenes and 5 have 50 or more. 33 of the 118 food concepts have no images. More distinct Sri Lankan photos would help the weak classes most.
- The nutrition table has **no sugars column**: `sugars_g` is always `null` in responses.
- **Data errors in the Sri Lankan table, for the publisher:** `SL_32` Fried Noodles has exactly the same six values as `SL_74` Carrot Curry (so it is never matched); `SL_13` Sandwich Bread equals `SL_14` White Bread; `SL_114` and `SL_116` also share values. Zeros in the table may mean "not measured".
- FoodBD `gl_reported` is unreliable and must not be used.
- `veg_cooking` is excluded from training by default (use `--also`).

## C. Experiments

- **Extra datasets (2026-10-18):** veg_cooking, pust and FoodBD added as train-only photos did not improve the 48-class test mAP (see `EXPERIMENTS.md`); the model is unchanged. The owner treats FoodBD's licence as fine, but nothing trained with it is in use. The Food-101 start at 256 px (A3 experiment 5, about 1 to 1.5 h of GPU) is **not run yet**: waiting for the owner's answer.
- **Seed averaging (2026-10-18):** averaging the 3 seed models gave test mAP 0.936 against 0.919 for single models, and also better valid mAP. To use it the service must load three bundles (about three times the inference time) and the threshold from validation is 0.65, not 0.85. Training a final model on train plus valid (A6) needs the epochs and the threshold fixed beforehand, because no validation photos remain. Waiting for the owner's decision.
- The Food-101 start did not beat the ImageNet start (0.898 against 0.916 test mAP, 3 seeds each). Decide whether two-stage training stays in the plan, or try it differently (for example a lower learning rate or a frozen backbone for the first epochs in Stage 2); ask the supervisors how to report it.
- The leak fix was checked only on the `--min-scenes 5` set; audit the `--min-scenes 1` set too before using it.
- `pumpkin_curry`, `fanta` and `iced_coffee` dropped out of the `--min-scenes 5` set after the leak fix (under 5 train scenes). They need more distinct photos to come back.
- The fingerprint audit only catches near-identical framing; a stronger check (for example image embeddings) could find cropped or rotated copies.
- Inspect weakest classes in each `runs/*_report.json` (per-class AP, with test positives).
- Stage 1 keeps the epoch with the best **test** top-1 (there is no validation split), so its 0.828 is slightly optimistic. Consider a validation split taken from train.
- Same seed is not the same result on the GPU (`cudnn.benchmark` is on): the repo version's first epochs differed from the old script's in the third decimal. Report means over seeds, not single runs.
- Weak classes: 25 epochs did nothing; input 256 px gave +0.009 test mAP over 5 seeds (suggestive). **256 px is now the Stage 2 default** (owner, 2026-10-15); use the same size at inference (`tasks/wire-recognizer.md`). The Food-101 comparison at 256 px is not run yet: wait for the `lunu_sambol` relabelling, which changes the scores anyway. EfficientNetV2-S was tried (batch 16, 3 seeds): not better overall (0.903 against 0.914), so MobileNetV3-Large stays. Not tried: longer training together with 256 px; EfficientNetV2-S with more epochs or a lower learning rate (its validation mAP suggests it was under-trained).

## D. Engineering

- Move the remaining curation scripts into `c1_training` (`build_curation.py`, `make_class_map.py`, `process_food101.py`). The cleaning and training scripts were moved on 2026-10-15.
- Stage 1 has no validation split: it still keeps the epoch with the best **test** top-1.
- Once the owner is happy with the repo version, remove or archive the old scripts in `_curation\training\` and `_curation\scripts\` (outside git).
- Database importers (USDA, MRI) are implemented and populated (2026-10-16): 241 MRI SL + 232 USDA rows in the database. The analyze endpoint still reads nutrition from the CSV, not the database: decide whether to switch it to a database-backed lookup.
- **Nutrition matches (2026-10-18):** the owner chose `dhal_curry` SL_54, `fish_curry` SL_146, `meat_curry` SL_158, `noodles` SL_33, and three USDA SR Legacy rows: `milkshake` US_170884, `submarine` US_170309, `patty` US_167660 (`docs/NUTRITION_MATCHES.md`). 38 of the 48 model foods now get values; 10 stay unknown (`asmi`, `brinjal_dish`, `cutlet`, `kokis`, `konda_kewum`, `lunu_miris`, `mun_kewum`, `pappadam`, `shrimp_curry`, `watalappam`). Still to review: the other `partial` and `close` matches. The running service must be restarted to read the new map and table.
- **USDA Foundation rows are thin:** of the 232 rows in the combined table, 158 have no `energy_kcal` and 107 no `carbohydrate_g` (Foundation Foods store energy under the Atwater ids, which the table builder did not read). Any food matched to such a row would show unknown energy. Decide whether to rebuild those rows from the USDA download (energy from the Atwater ids, carbohydrate by difference minus fibre).
- **Contract wording (C2, C3):** the schema text for `carbohydrate_g` says "Total carbohydrate", but the table value is **available carbohydrate (fibre excluded)**. Tell C2 and C3, and fix the wording through a contract PR.
- Totals are `null` as soon as one food on the plate is unknown (existing rule). Decide with C2, C3 and the app whether partial totals with a warning would be better.
- Nutrient values are per 100 g because the portion estimator is still a fixed 100 g mock.
- **Trained model in the service: done, opt-in (2026-10-16).** Still open: (1) PyTorch is not in `uv.lock` (the server environment `D:\RESEARCH PROJECT\c1_server_env` was built by hand); making it an official optional dependency changes the shared lock and needs a team PR; (2) ~~the model loads on the first request~~ done 2026-10-17 (loads at startup; start with `scripts/start_c1.ps1`); (3) false alarms (for example `mallum` and `white_rice` on a string-hoppers close-up at threshold 0.85): consider per-class thresholds chosen on the validation set; (4) a real nutrition lookup (importers) so nutrients stop being `null`; (5) `MODEL_DEVICE=cuda` is untested; (6) the CI never runs the PyTorch tests (they skip), so they only run in the server environment; (7) `.env.example` (shared) does not list `RECOGNIZER`, `MODEL_PATH`, `MODEL_DEVICE`.
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
