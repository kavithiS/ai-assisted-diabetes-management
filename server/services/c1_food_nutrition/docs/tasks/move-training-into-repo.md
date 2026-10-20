# Move the cleaning and training scripts into the repo

**Goal:** the data and training scripts live in `server/services/c1_food_nutrition/training/`, typed and tested, with the data folder set by `C1_DATA_DIR`, so anyone can re-run the work from the repo.

**State (2026-10-15): done for the cleaning, leak and training scripts.** They are now the package `src/c1_training/` (tests in `training/tests/`, how-to and the list of differences in `training/README.md`). Still outside: `build_curation.py`, `make_class_map.py`, `process_food101.py`; follow the same pattern for them. The old scripts are in `D:\RESEARCH PROJECT\Foods datasets for training\Images Datasets\_curation\`:

| Folder | Scripts |
|---|---|
| `scripts\` | `build_curation.py`, `make_class_map.py`, `make_clean_manifest.py`, `preprocess_images.py`, `process_food101.py` |
| `training\` | `common.py`, `model.py`, `stage1_pretrain_food101.py`, `stage2_finetune_srilankan.py`, `leak_audit.py`, `leak_fix.py`, `check_setup.py`, `setup_training*.bat` |

`training\` also holds `*.bak_*` copies; do not move those.

## Constraints

- **PyTorch must not become a default dependency.** CI would download about 2.6 GB (the torch 2.14.1+cu126 wheel alone was 2,602.8 MB). Keep it optional (an extra or a separate requirements file) and ask the owner which.
- `mypy --strict` runs over all of `server/`, and pytest collects all of `server/`. Code that imports torch must pass mypy without torch installed, and its tests must skip (`pytest.importorskip("torch")`) when torch is missing.
- The root `pyproject.toml` is shared. A mypy override there needs a team PR; prefer a per-file solution inside the C1 folder.
- Images, manifests, weights and reports stay out of git.

## Steps

1. Show the owner the file plan (new modules, what moves, what stays) and wait for approval.
2. Torch-free parts first (`common.py`, the manifest and split logic, the fingerprint and leak logic, cleaning scripts): add type hints, read paths from `C1_DATA_DIR`, keep the command-line arguments the same.
3. Tests on small generated images (Pillow, a few pixels, written to `tmp_path`): manifest loading and `--min-scenes` filtering, split by scene group, fingerprint and mirror matching, leak fix dry run and apply with backup.
4. Torch parts (`model.py`, Stage 1, Stage 2): typed, imported only when torch is present; a 1-epoch smoke test on a tiny generated set, skipped without torch.
5. Fix the known script issues while moving, each with the owner's agreement:
   - Stage 1 picks its best epoch on the **test** set and sets no seed;
   - quick tests overwrite real run files (add an output-name option);
   - `leak_audit.py` has `--min-scenes 5` fixed;
   - `preprocess_images.py` rebuilds `processed_manifest.csv` and undoes the leak fix.
6. Check that a re-run from the repo gives the same split sizes (2,113 images, 49 classes, 1,642 / 262 / 209) and, for one seed, a test mAP close to the old one.

## Checks

```
uv run ruff check .
uv run ruff format --check .
uv run mypy server
uv run pytest server/services/c1_food_nutrition
uv run pytest
```

## Done when

All checks pass without torch installed, the torch tests pass with it, and the split sizes match.

## Record

`CONTEXT.md` sections 3, 9 and 13 (new locations), `OPEN_ITEMS.md` section D, `CHANGELOG.md`.
