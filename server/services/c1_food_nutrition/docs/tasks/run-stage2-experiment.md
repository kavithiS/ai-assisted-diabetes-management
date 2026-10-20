# Run a Stage 2 experiment

**Goal:** train the Sri Lankan multi-label model with one change (a setting, an architecture, a start point) and compare it fairly with the current baseline.

**Current baseline (2026-10-15):** ImageNet start, `--min-scenes 5`, cleaned split (49 classes, 1,642 / 262 / 209), 15 epochs: test mAP 0.910 / 0.922 / 0.915, mean 0.916. Source: `runs/stage2_mobilenet_v3_large_imagenet_seed{0,1,2}_report.json`.

## Before you start

- Set up the session as in `training/README.md`: activate `.venv311`, set `C1_DATA_DIR` and `PYTHONPATH`.
- Change **one** thing at a time. A run is comparable with the baseline only if the classes, split and every other setting match.
- **Run names can collide.** Names are `stage2_<arch>_<imagenet|food101>_seed<N>`. A run with only a different `--epochs`, `--lr` or `--min-scenes` gets the same name as the baseline and **overwrites it**. Always give a change its own `--tag` (for example `--tag ep25`) or its own `--out-dir`.

## Steps

1. Check the environment: `python -m c1_training.check_setup`.
2. Quick test of the change first (about 2 minutes), into a scratch folder. Add your change to:
   ```
   python -m c1_training.stage2 --epochs 1 --min-scenes 5 --workers 2 --out-dir %TEMP%\c1_quick
   ```
3. Full runs, three seeds:
   ```
   python -m c1_training.stage2 --min-scenes 5 --seed 0 --tag <name> <your change>
   python -m c1_training.stage2 --min-scenes 5 --seed 1 --tag <name> <your change>
   python -m c1_training.stage2 --min-scenes 5 --seed 2 --tag <name> <your change>
   ```
   On an RTX 3050 a MobileNetV3 run takes about 3 to 5 minutes. `--arch efficientnet_v2_s` has not been run yet; expect it to be slower [UNVERIFIED].
4. If you see a multiprocessing error, add `--workers 0`.
5. With `--stage1`, check the console says `loaded 310 backbone tensors` (MobileNetV3). A much smaller number means the Stage 1 weights did not load.

## Reading the result

Open each `runs\<tag>_report.json`. Use `test_mAP`, `test_microF1`, `best_valid_mAP`, `n_classes`, `n_images`, and `per_class` (weakest first, with `test_positives`).

- Check `n_classes` and `n_images` match the baseline. If not, the runs are **not comparable**.
- Report each seed, the mean and the sample standard deviation.
- With three seeds, a difference smaller than about two standard deviations is not evidence of a change. Say "no clear difference".
- Do not choose settings using the test score. Use `best_valid_mAP` to choose, and report test once.

## Done when

- Three report files exist for the change, with the same `n_classes` and `n_images` as the baseline.
- The baseline files in `runs\` are untouched, or backed up.

## Record

- `EXPERIMENTS.md`: one row per seed, with the report file as source.
- `CONTEXT.md` section 10: a results row and one sentence on what it means. Section 3 if the baseline changes.
- `CHANGELOG.md` entry, and close or add items in `OPEN_ITEMS.md`.
