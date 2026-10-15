# C1 training

Data cleaning, leak checks and model training for C1. The code is the `c1_training` package in
`../src/c1_training/`; the tests are in `tests/`; `configs/` holds dataset configs for the
service.

Research prototype: results are estimates on a small held-out test set, not clinical claims.

## What is where

| Module | Does | Needs |
|---|---|---|
| `paths` | Finds the data folder (`C1_DATA_DIR` or `--data-dir`) | — |
| `manifest` | Reads the manifest into items; `--min-scenes` class filter | — |
| `metrics` | Average precision, mAP, micro-F1 (same as scikit-learn) | numpy |
| `fingerprint`, `leak` | Near-copy fingerprints; leak audit and fix logic | numpy (+ Pillow to read images) |
| `cleaning` | `image_manifest.csv` → `image_manifest_clean.csv` | Pillow |
| `preprocess` | Resized RGB copies → `processed_manifest.csv` (keeps leak-fix drops) | Pillow |
| `leak_audit`, `leak_fix` | Commands for the leak check (`../docs/tasks/leak-audit-and-fix.md`) | Pillow |
| `model`, `stage1`, `stage2` | Training | PyTorch, torchvision, Pillow |
| `check_setup` | Checks the environment and the data | — |

The service's `uv sync` installs only numpy-level dependencies. The modules that need Pillow or
PyTorch import them inside functions, so the repo's tests and type checks run without them; the
tests that need them are skipped there.

## One-time setup (Windows)

The existing environment is
`D:\RESEARCH PROJECT\Foods datasets for training\Images Datasets\_curation\training\.venv311`
(Python 3.11.17, torch 2.14.1+cu126). To build a new one, see `requirements.txt` (the GPU
build is about 2.6 GB).

## Every session (Command Prompt)

```
"D:\RESEARCH PROJECT\Foods datasets for training\Images Datasets\_curation\training\.venv311\Scripts\activate"
set C1_DATA_DIR=D:\RESEARCH PROJECT\Foods datasets for training\Images Datasets
set PYTHONPATH=D:\ai-assisted-diabetes-management\server\services\c1_food_nutrition\src
python -m c1_training.check_setup
```

## Commands

```
python -m c1_training.stage2 --min-scenes 5 --seed 0
python -m c1_training.stage2 --min-scenes 5 --seed 0 --stage1 "%C1_DATA_DIR%\_curation\training\runs\stage1_mobilenet_v3_large.pt"
python -m c1_training.stage1 --epochs 8
python -m c1_training.leak_audit
python -m c1_training.leak_fix --max-dist 30
python -m c1_training.cleaning
python -m c1_training.preprocess
```

Weights and reports go to `%C1_DATA_DIR%\_curation\training\runs` unless you pass `--out-dir`.
**A run with the same name overwrites the earlier one.** For quick tests use
`--out-dir <another folder>` or `--tag test`. Add `--workers 0` if you see a multiprocessing
error.

## Tests

Repo checks (no PyTorch needed):

```
uv run pytest server/services/c1_food_nutrition/training
```

All tests, including the PyTorch smoke test, in the training environment (from
`server\services\c1_food_nutrition`, after the "Every session" lines):

```
python -m pytest training/tests -p no:cacheprovider
```

## Differences from the old scripts in `_curation\scripts` and `_curation\training`

Checked on the real data on 2026-10-15 (see `../docs/CHANGELOG.md`): same manifest set, same
clean-manifest roles, byte-identical resized images on a sample of 40, and the same leak-audit
distances for all 471 valid/test images.

- Paths come from `C1_DATA_DIR` / `--data-dir` instead of the script location.
- `--out-dir` and `--tag` for Stage 1 and Stage 2, so tests need not overwrite real runs.
- Stage 1 now sets a random seed (`--seed`, default 0). It still selects its epoch on the test
  set (no validation split yet).
- Metrics are computed in numpy; they match scikit-learn (tested).
- `leak_audit` takes `--min-scenes`.
- `preprocess` keeps rows that `leak_fix` dropped, so a re-run no longer undoes the leak fix.
- Stage 2 reports also record the manifest path.
- Not moved yet: `build_curation.py`, `make_class_map.py`, `process_food101.py`.
