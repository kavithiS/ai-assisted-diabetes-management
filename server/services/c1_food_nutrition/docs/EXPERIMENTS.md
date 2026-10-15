# C1 experiments

One row per run, oldest first. Values are copied from the file in the Source column. A run with no file is marked **[UNVERIFIED]** and its value comes from `CONTEXT.md`, not from a file.

All paths are relative to `D:\RESEARCH PROJECT\Foods datasets for training\Images Datasets\_curation\training\`. Architecture is `mobilenet_v3_large` throughout. Stage 2 runs use 15 epochs, batch 32, lr 5e-4, 224 px, no extra datasets. "Split" names the data version:

- **leaky-52**: `--min-scenes 5` before the 2026-10-15 leak fix, 52 classes, train / valid / test 1,785 / 278 / 223.
- **leaky-78**: `--min-scenes 1` before the leak fix, 78 classes, 1,807 / 287 / 226.
- **clean-49**: `--min-scenes 5` after the leak fix, 49 classes, 1,642 / 262 / 209.

Files under `runs_backup_2026-10-15/` are the reports as they were before 2026-10-15; the same names in `runs/` now hold the clean-49 runs.

## Stage 1 (Food-101, reconstructed split, 101 classes)

| Date | Run | Python | Epochs | Train per class | Seed | Result | Source |
|---|---|---|---|---|---|---|---|
| [UNVERIFIED date] | Stage 1 quick check | 3.13 | 3 | 300 | none | top-1 0.761 | **[UNVERIFIED]** no report file (Stage 1 writes none) |
| 2026-10-14 | Stage 1 full run | 3.13 | 8 | all | none | top-1 0.828 | **[UNVERIFIED]** no report file. Weights: `runs/stage1_mobilenet_v3_large.pt` (saved 2026-10-14 18:48) |
| [UNVERIFIED date] | Stage 1 quick test | 3.13 | 1 | 20 | none | top-1 0.155 | **[UNVERIFIED]** no report file |
| 2026-10-15 | Stage 1 quick test, run 1 | 3.11 | 1 | 20 | none | top-1 0.111 (606 test images) | console output |
| 2026-10-15 | Stage 1 quick test, run 2 | 3.11 | 1 | 20 | none | top-1 0.140 | console output |
| 2026-10-15 | Stage 1 quick test, run 3 | 3.11 | 1 | 20 | none | top-1 0.101 | console output |

Python 3.13 for the older rows is inferred from the timeline (the 3.11 environment did not exist before 2026-10-15). Stage 1 picks its saved epoch by test top-1 (no validation split), so these values are slightly optimistic.

## Stage 2 (Sri Lankan sets, multi-label)

| Date | Split | Start | Epochs | Seed | Test mAP | Test micro-F1 | Best valid mAP | Source |
|---|---|---|---|---|---|---|---|---|
| 2026-10-14 | leaky-52 | ImageNet | 15 | 0 | 0.955 | 0.914 | 0.935 | `runs_backup_2026-10-15/stage2_mobilenet_v3_large_imagenet_seed0_report.json` |
| 2026-10-14 | leaky-52 | ImageNet | 15 | 1 | 0.945 | 0.911 | 0.933 | `runs_backup_2026-10-15/stage2_mobilenet_v3_large_imagenet_seed1_report.json` |
| 2026-10-14 | leaky-52 | ImageNet | 15 | 2 | 0.925 | 0.907 | 0.955 | `runs_backup_2026-10-15/stage2_mobilenet_v3_large_imagenet_seed2_report.json` |
| 2026-10-14 | leaky-78 | Food-101 (Stage 1) | 15 | 0 | 0.917 | 0.897 | 0.916 | `runs_backup_2026-10-15/stage2_mobilenet_v3_large_food101_seed0_report.json` |
| 2026-10-14 | leaky-78 | Food-101 (Stage 1) | 15 | 1 | 0.908 | 0.887 | 0.915 | `runs_backup_2026-10-15/stage2_mobilenet_v3_large_food101_seed1_report.json` |
| 2026-10-14 | leaky-78 | Food-101 (Stage 1) | 15 | 2 | 0.901 | 0.905 | 0.880 | `runs_backup_2026-10-15/stage2_mobilenet_v3_large_food101_seed2_report.json` |
| [UNVERIFIED date] | leaky-52 | ImageNet | 1 (quick test) | 0 | 0.552 | – | – | **[UNVERIFIED]** report was overwritten by later runs; value from `CONTEXT.md` |
| 2026-10-15 | leaky-52 | ImageNet | 1 (quick test, Python 3.11) | 0 | 0.561 | 0.627 | 0.575 | `runs_quicktest_py311/stage2_mobilenet_v3_large_imagenet_seed0_report.json` |
| 2026-10-15 | clean-49 | ImageNet | 15 | 0 | 0.910 | 0.872 | 0.951 | `runs/stage2_mobilenet_v3_large_imagenet_seed0_report.json` |
| 2026-10-15 | clean-49 | ImageNet | 15 | 1 | 0.922 | 0.899 | 0.921 | `runs/stage2_mobilenet_v3_large_imagenet_seed1_report.json` |
| 2026-10-15 | clean-49 | ImageNet | 15 | 2 | 0.915 | 0.906 | 0.948 | `runs/stage2_mobilenet_v3_large_imagenet_seed2_report.json` |
| 2026-10-15 | clean-49 | Food-101 (Stage 1) | 15 | 0 | 0.913 | 0.892 | 0.956 | `runs/stage2_mobilenet_v3_large_food101_seed0_report.json` |
| 2026-10-15 | clean-49 | Food-101 (Stage 1) | 15 | 1 | 0.892 | 0.902 | 0.950 | `runs/stage2_mobilenet_v3_large_food101_seed1_report.json` |
| 2026-10-15 | clean-49 | Food-101 (Stage 1) | 15 | 2 | 0.889 | 0.895 | 0.939 | `runs/stage2_mobilenet_v3_large_food101_seed2_report.json` |

| 2026-10-15 | clean-49 | ImageNet (repo code `c1_training.stage2`, check run) | 15 | 0 | 0.906 | 0.868 | 0.941 | scratch folder of the session (not kept); console output |

The last row checks the repo version of the code against the old script (0.910 for the same seed). Same seed does not give the same result on the GPU, so a difference of this size is expected.

Summary (mean, sample SD over 3 seeds, test mAP): clean-49 ImageNet 0.916 (0.006); clean-49 Food-101 0.898 (0.013); leaky-52 ImageNet 0.942 (0.015). Only the two clean-49 rows are comparable with each other.

## Leak audits

| Date | Data | Test with a train copy (≤ 30) | Valid with a train copy (≤ 30) | Source |
|---|---|---|---|---|
| 2026-10-15 | leaky-52 | 20 of 223 (9%) | 36 of 278 | console output; `leak_audit.csv` (since overwritten) |
| 2026-10-15 | after pass 1 (51 classes) | 0 of 223; 7 at 31–40 | 0 of 278 | console output; `leak_audit.csv` (since overwritten) |
| 2026-10-15 | clean-49 | 0 of 209; 1 at ≤ 40 | 0 of 262 | console output; `leak_audit.csv` |
