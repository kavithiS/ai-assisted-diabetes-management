# Leak audit and fix

**Goal:** make sure no valid or test photo has a near-copy in the training photos. A copy lets the model remember the answer and inflates the score.

**State (2026-10-15):** done for the `--min-scenes 5` set. Two passes dropped 102 train rows; 0 of 209 test photos have a train copy at distance ≤ 30. The `--min-scenes 1` set (78 classes before the fix) has **not** been audited.

## How it works

The audit (`c1_training.leak_audit`) makes a 256-bit fingerprint of each photo (and its mirror image) and, for every valid/test photo, finds the closest train photo. Distance 0 is identical; up to about 30 is almost always the same shot; 60 and above are different pictures. It writes `leak_audit.csv` (every valid/test photo with its closest train photo, closest first).

The fix (`c1_training.leak_fix`) sets `role = leak_dropped` on train photos within `--max-dist` of a valid/test photo. The valid/test photo is kept. No image file is touched. It is a dry run unless you add `--apply`, and it backs up `processed_manifest.csv` before writing.

## Steps

Set up the session as in `training/README.md` (activate `.venv311`, set `C1_DATA_DIR` and `PYTHONPATH`).

1. Run the audit:
   ```
   python -m c1_training.leak_audit --min-scenes 5
   ```
   Look at "TEST images with a near-identical training photo". Compare with the reference line (different-scene train pairs, about 1 to 2%).
2. **Look at the pairs** before changing anything. The fingerprint is not perfect: copies can sit above 30, and different foods with the same layout (white cups of different drinks) can sit below 50. Open the two photos named in each row of `leak_audit.csv`.
3. Dry run, then apply, only with the owner's approval:
   ```
   python -m c1_training.leak_fix --max-dist 30
   python -m c1_training.leak_fix --max-dist 30 --apply
   ```
   For a wider pass, require equal labels so look-alike foods are not dropped:
   ```
   python -m c1_training.leak_fix --max-dist 48 --same-labels
   python -m c1_training.leak_fix --max-dist 48 --same-labels --apply
   ```
   The backup file name includes the distance; the script refuses to overwrite an existing backup.
4. The script prints classes that fell under `--min-scenes`. Tell the owner: those classes leave the training set.
5. Run the audit again and check the result.
6. Re-run the baselines on the cleaned split (see `run-stage2-experiment.md`). Old scores are no longer comparable.

## Traps

- **The old `_curation\scripts\preprocess_images.py` rebuilds `processed_manifest.csv` and undoes this fix.** Use `python -m c1_training.preprocess`, which keeps the leak-fix drops. If the old one was run, apply both passes again and re-audit.
- The audit and fix only look at the classes kept by `--min-scenes` (default 5). Both commands take `--min-scenes`; the old `leak_audit.py` does not.
- Kaggle-26 scene groups do not match real scenes, so most copies come from there.

## Done when

The audit shows 0 test photos at ≤ 30, the pairs just above 30 have been looked at, and the baselines have been re-run.

## Record

Audit and fix numbers in `CONTEXT.md` section 7 and 10, one `EXPERIMENTS.md` row per audit, `CHANGELOG.md`, `OPEN_ITEMS.md`.
