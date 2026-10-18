# C1 experiments

One row per run, oldest first. Values are copied from the file in the Source column. A run with no file is marked **[UNVERIFIED]** and its value comes from `CONTEXT.md`, not from a file.

All paths are relative to `D:\RESEARCH PROJECT\Foods datasets for training\Images Datasets\_curation\training\`. Architecture is `mobilenet_v3_large` throughout. Stage 2 runs use 15 epochs, batch 32, lr 5e-4, 224 px, no extra datasets. "Split" names the data version:

- **leaky-52**: `--min-scenes 5` before the 2026-10-15 leak fix, 52 classes, train / valid / test 1,785 / 278 / 223.
- **leaky-78**: `--min-scenes 1` before the leak fix, 78 classes, 1,807 / 287 / 226.
- **clean-49**: `--min-scenes 5` after the leak fix, 49 classes, 1,642 / 262 / 209.
- **relish-48**: clean-49 after the 2026-10-15 relabelling of 71 relish photos (`lunu_sambol` left the set), 48 classes, same split sizes 1,642 / 262 / 209. These runs use 256 px input (the new default).

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
| 2026-10-15 | clean-49 | ImageNet | 15 | 3 | 0.916 | 0.904 | 0.945 | `runs/stage2_mobilenet_v3_large_imagenet_seed3_report.json` (baseline, 224 px, 15 epochs) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 4 | 0.887 | 0.883 | 0.916 | `runs/stage2_mobilenet_v3_large_imagenet_seed4_report.json` (baseline, 224 px, 15 epochs) |
| 2026-10-15 | clean-49 | ImageNet | 25 | 0 | 0.923 | 0.905 | 0.954 | `runs/stage2_mobilenet_v3_large_imagenet_seed0_ep25_report.json` (A: 25 epochs) |
| 2026-10-15 | clean-49 | ImageNet | 25 | 1 | 0.902 | 0.906 | 0.948 | `runs/stage2_mobilenet_v3_large_imagenet_seed1_ep25_report.json` (A: 25 epochs) |
| 2026-10-15 | clean-49 | ImageNet | 25 | 2 | 0.924 | 0.900 | 0.934 | `runs/stage2_mobilenet_v3_large_imagenet_seed2_ep25_report.json` (A: 25 epochs) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 0 | 0.913 | 0.879 | 0.954 | `runs/stage2_mobilenet_v3_large_imagenet_seed0_s256_report.json` (B: input 256 px) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 1 | 0.938 | 0.905 | 0.939 | `runs/stage2_mobilenet_v3_large_imagenet_seed1_s256_report.json` (B: input 256 px) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 2 | 0.917 | 0.900 | 0.933 | `runs/stage2_mobilenet_v3_large_imagenet_seed2_s256_report.json` (B: input 256 px) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 3 | 0.937 | 0.908 | 0.951 | `runs/stage2_mobilenet_v3_large_imagenet_seed3_s256_report.json` (B: input 256 px) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 4 | 0.889 | 0.890 | 0.924 | `runs/stage2_mobilenet_v3_large_imagenet_seed4_s256_report.json` (B: input 256 px) |

| 2026-10-15 | clean-49 | ImageNet | 15 | 0 | 0.925 | 0.893 | 0.891 | `runs/stage2_efficientnet_v2_s_imagenet_seed0_bs16_report.json` (C: EfficientNetV2-S, batch 16) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 1 | 0.875 | 0.853 | 0.875 | `runs/stage2_efficientnet_v2_s_imagenet_seed1_bs16_report.json` (C: EfficientNetV2-S, batch 16) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 2 | 0.909 | 0.873 | 0.900 | `runs/stage2_efficientnet_v2_s_imagenet_seed2_bs16_report.json` (C: EfficientNetV2-S, batch 16) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 0 | 0.924 | 0.897 | 0.940 | `runs/stage2_mobilenet_v3_large_imagenet_seed0_bs16_report.json` (C-ref: MobileNetV3, batch 16) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 1 | 0.905 | 0.905 | 0.946 | `runs/stage2_mobilenet_v3_large_imagenet_seed1_bs16_report.json` (C-ref: MobileNetV3, batch 16) |
| 2026-10-15 | clean-49 | ImageNet | 15 | 2 | 0.912 | 0.893 | 0.941 | `runs/stage2_mobilenet_v3_large_imagenet_seed2_bs16_report.json` (C-ref: MobileNetV3, batch 16) |

| 2026-10-15 | relish-48 | ImageNet | 15 | 0 | 0.929 | 0.896 | 0.942 | `runs/stage2_mobilenet_v3_large_imagenet_seed0_rl256_report.json` (256 px) |
| 2026-10-15 | relish-48 | ImageNet | 15 | 1 | 0.918 | 0.900 | 0.930 | `runs/stage2_mobilenet_v3_large_imagenet_seed1_rl256_report.json` (256 px) |
| 2026-10-15 | relish-48 | ImageNet | 15 | 2 | 0.909 | 0.898 | 0.948 | `runs/stage2_mobilenet_v3_large_imagenet_seed2_rl256_report.json` (256 px) |

The three relish-48 rows are not comparable with the clean-49 rows (different labels and classes). Seed 2 (valid 0.948) was exported as the model for the service; its test score is the lowest of the three.

Rows for A and B were run with `--epochs 25 --tag ep25` and `--size 256 --tag s256`. Their reports do not record the input size (it was added to the report afterwards, in the same session); the setting is taken from the command.

The last row checks the repo version of the code against the old script (0.910 for the same seed). Same seed does not give the same result on the GPU, so a difference of this size is expected.

Summary (mean, sample SD over seeds, test mAP): clean-49 ImageNet, seeds 0 to 2, 0.916 (0.006); the same with seeds 0 to 4, **0.910 (0.013)**; clean-49 Food-101, seeds 0 to 2, 0.898 (0.013); leaky-52 ImageNet 0.942 (0.015). Only clean-49 rows with the same seeds and settings are comparable.

Weak-class changes (clean-49, ImageNet start; from the report files):

| Variant | Seeds | Test mAP mean (SD) | Valid mAP mean | Paired test difference from baseline, same seeds | Mean AP of the 7 weakest classes |
|---|---|---|---|---|---|
| Baseline (224 px, 15 epochs) | 0 to 4 | 0.910 (0.013) | 0.936 | – | 0.668 |
| A: 25 epochs | 0 to 2 | 0.916 (0.013) | 0.945 | +0.000 (std error 0.011) | 0.683 |
| B: input 256 px | 0 to 4 | 0.919 (0.020) | 0.940 | +0.009 (std error 0.004); +0.003 / +0.016 / +0.002 / +0.020 / +0.002 | 0.715 |

| C: EfficientNetV2-S, batch 16 | 0 to 2 | 0.903 (0.026) | 0.889 | −0.010 (std error 0.010) against MobileNetV3 at batch 16 | 0.770 |
| C-ref: MobileNetV3, batch 16 | 0 to 2 | 0.914 (0.010) | 0.942 | −0.002 (std error 0.009) against batch 32 | 0.685 |

EfficientNetV2-S was run at batch 16 because at batch 32 it needed 5.6 of the 6 GB on the RTX 3050, spilled into shared memory and took about 210 s per epoch (stopped after 4 epochs, not kept); at batch 16 it took about 28 s per epoch. MobileNetV3 at batch 16 is the like-for-like reference. EfficientNetV2-S was better on the weak classes but worse on the other 42 (0.929 against 0.958) and on validation mAP, with a wider spread over seeds. Weights download for EfficientNetV2-S: 82.7 MB (`efficientnet_v2_s-dd5fe13b.pth`).

The 7 weakest classes are lunu_sambol, fish_curry, lunu_miris, vegetable_salad, pol_sambol, pittu and dhal_curry; they have 2 to 8 test positives each, so their means are noisy. The other 42 classes: 0.957 (baseline), 0.962 (A), 0.958 (B).

## Extra image datasets and test-time options (2026-10-18)

Reports are in `runs/` of the data folder (backup of `runs\` before these runs: `runs_backup_2026-10-18\`). Logs, the scripts and `a5_results.json` are in `_curation\training\logs_2026-10-18\`. All runs: MobileNetV3-Large, ImageNet start, 256 px, 15 epochs, batch 32, lr 5e-4, `--min-scenes 5`, seeds 0 to 2, `--extras-train-only`: the extra datasets add **train photos only**; the best epoch is chosen on the 262 Sri Lankan valid photos (48 classes) and the test numbers below are for the same 209 Sri Lankan test photos and 48 classes as the baseline rows (relish-48, `..._rl256_report.json`). The extra datasets' valid and test photos are not used for choosing or scoring the 48 classes. Test mAP is on the 48 baseline classes; micro-F1 is at 0.5. FoodBD: licence not verified, owner said on 2026-10-18 to treat it as fine; **no run was kept, so no FoodBD-trained model is in the service**.

| Date | Split | Start | Epochs | Seed | Test mAP (48 classes) | Test micro-F1 | Best valid mAP | Source |
|---|---|---|---|---|---|---|---|---|
| 2026-10-18 | relish-48 + veg_cooking (train photos only; 56 classes) | ImageNet | 15 | 0 | 0.931 | 0.919 | 0.936 | `runs/stage2_mobilenet_v3_large_imagenet_seed0_xveg_report.json` (8 new classes: test mAP 0.841 on 48 photos of the extra datasets) |
| 2026-10-18 | relish-48 + veg_cooking (train photos only; 56 classes) | ImageNet | 15 | 1 | 0.918 | 0.901 | 0.931 | `runs/stage2_mobilenet_v3_large_imagenet_seed1_xveg_report.json` (8 new classes: test mAP 0.848 on 48 photos of the extra datasets) |
| 2026-10-18 | relish-48 + veg_cooking (train photos only; 56 classes) | ImageNet | 15 | 2 | 0.905 | 0.871 | 0.948 | `runs/stage2_mobilenet_v3_large_imagenet_seed2_xveg_report.json` (8 new classes: test mAP 0.867 on 48 photos of the extra datasets) |
| 2026-10-18 | relish-48 + pust (train photos only; 62 classes) | ImageNet | 15 | 0 | 0.924 | 0.886 | 0.952 | `runs/stage2_mobilenet_v3_large_imagenet_seed0_xpust_report.json` (14 new classes: test mAP 0.888 on 108 photos of the extra datasets) |
| 2026-10-18 | relish-48 + pust (train photos only; 62 classes) | ImageNet | 15 | 1 | 0.917 | 0.869 | 0.914 | `runs/stage2_mobilenet_v3_large_imagenet_seed1_xpust_report.json` (14 new classes: test mAP 0.819 on 108 photos of the extra datasets) |
| 2026-10-18 | relish-48 + pust (train photos only; 62 classes) | ImageNet | 15 | 2 | 0.916 | 0.872 | 0.948 | `runs/stage2_mobilenet_v3_large_imagenet_seed2_xpust_report.json` (14 new classes: test mAP 0.868 on 108 photos of the extra datasets) |
| 2026-10-18 | relish-48 + foodbd (train photos only; 111 classes) | ImageNet | 15 | 0 | 0.958 | 0.907 | 0.931 | `runs/stage2_mobilenet_v3_large_imagenet_seed0_xfoodbd_report.json` (63 new classes: test mAP 0.671 on 351 photos of the extra datasets) |
| 2026-10-18 | relish-48 + foodbd (train photos only; 111 classes) | ImageNet | 15 | 1 | 0.951 | 0.920 | 0.948 | `runs/stage2_mobilenet_v3_large_imagenet_seed1_xfoodbd_report.json` (63 new classes: test mAP 0.676 on 351 photos of the extra datasets) |
| 2026-10-18 | relish-48 + foodbd (train photos only; 111 classes) | ImageNet | 15 | 2 | 0.882 | 0.895 | 0.939 | `runs/stage2_mobilenet_v3_large_imagenet_seed2_xfoodbd_report.json` (63 new classes: test mAP 0.662 on 351 photos of the extra datasets) |
| 2026-10-18 | relish-48 + pust, foodbd, veg_cooking (train photos only; 123 classes) | ImageNet | 15 | 0 | 0.934 | 0.900 | 0.957 | `runs/stage2_mobilenet_v3_large_imagenet_seed0_xall_report.json` (75 new classes: test mAP 0.693 on 507 photos of the extra datasets) |
| 2026-10-18 | relish-48 + pust, foodbd, veg_cooking (train photos only; 123 classes) | ImageNet | 15 | 1 | 0.930 | 0.908 | 0.935 | `runs/stage2_mobilenet_v3_large_imagenet_seed1_xall_report.json` (75 new classes: test mAP 0.682 on 507 photos of the extra datasets) |
| 2026-10-18 | relish-48 + pust, foodbd, veg_cooking (train photos only; 123 classes) | ImageNet | 15 | 2 | 0.900 | 0.900 | 0.946 | `runs/stage2_mobilenet_v3_large_imagenet_seed2_xall_report.json` (75 new classes: test mAP 0.680 on 507 photos of the extra datasets) |

Summary (seeds 0 to 2; mean, sample SD of test mAP on the 48 classes; paired difference from the baseline with the same seeds, with standard error; valid mAP difference):

| Variant | Test mAP mean (SD) | Paired test difference (SE) | Valid mAP difference | New classes, test mAP (on the extras' own test photos) |
|---|---|---|---|---|
| Baseline relish-48, 256 px (`..._rl256`) | 0.919 (0.010) | – | – | – |
| + veg_cooking | 0.918 (0.013) | -0.001 (0.002) | -0.002 | 0.841 / 0.848 / 0.867 (8 classes, 48 photos) |
| + pust | 0.919 (0.004) | +0.000 (0.004) | -0.002 | 0.888 / 0.819 / 0.868 (14 classes, 108 photos) |
| + foodbd | 0.930 (0.042) | +0.012 (0.020) | -0.001 | 0.671 / 0.676 / 0.662 (63 classes, 351 photos) |
| + pust, foodbd, veg_cooking | 0.921 (0.018) | +0.003 (0.006) | +0.006 | 0.693 / 0.682 / 0.680 (75 classes, 507 photos) |

Reading: **no extra dataset passes the keep rule** (better on validation and a paired test difference clearly above its standard error). FoodBD's +0.012 is 0.6 standard errors, with seeds from 0.882 to 0.958. Micro-F1 at 0.5 is lower only for the pust variant (0.876 against 0.898); the others are within the noise. The new-class scores are measured on different photos for each variant and cannot be compared with each other or with the 48-class score; FoodBD's new classes are the weakest (0.66 to 0.68), partly from coarse labels (`vegetable`, `vorta`, `kabab`). Per-class AP of `dhal_curry` (which gains photos from pust and FoodBD) moves between 0.67 and 0.92 across seeds with 1 to 5 test positives, without a consistent direction. The current model stays.

Test-time options on the baseline set (`logs_2026-10-18\a5_eval.py`, output `a5_results.json`; the 3 saved `..._rl256.pt` models; thresholds chosen on the valid photos only, grid 0.10 to 0.95; per-class thresholds only for classes with 3 or more valid positives):

| Option | Valid mAP | Test mAP | Test micro-F1 (global threshold from valid) | Paired difference over seeds 0 to 2 (SE) |
|---|---|---|---|---|
| Single model, seeds 0 / 1 / 2 | 0.942 / 0.930 / 0.948 | 0.929 / 0.918 / 0.909 | 0.907 / 0.921 / 0.926 (thresholds 0.75 / 0.80 / 0.85) | – |
| Flip test-time augmentation | 0.943 / 0.930 / 0.945 | 0.926 / 0.911 / 0.909 | 0.901 / 0.919 / 0.930 | test mAP -0.003 (0.002); valid mAP -0.001 (0.001); test F1 -0.001 (0.003) |
| Per-class thresholds (same scores) | – | – | 0.909 / 0.922 / 0.923 | test F1 -0.000 (0.002); false alarms +6 (2.0); misses -5 (1.0) |
| Average of the 3 seed models | 0.951 | 0.936 | 0.930 (threshold 0.65 from valid); micro-F1 at 0.5: 0.909 | against the 3 single models: valid mAP +0.011 (0.005), test mAP +0.017 (0.006), test F1 +0.012 (0.006); better on 3 of 3 seeds |
| Average of the 3 seed models, plus flip | 0.952 | 0.933 | 0.931 | not better than the plain average on test mAP |

Reading: flip augmentation and per-class thresholds do **not** help (the per-class thresholds only trade 5 fewer misses for 6 more false alarms). **Averaging the three seed models helps on both validation and test** (the single models are the three members of the average, so the three differences are not independent and the standard errors are rough). The test photos were scored for several variants, so these are not a single clean test; the choice is consistent with validation, which improved too. The cost is three times the inference work (single model about 15 ms per photo on the CPU; the average roughly 45 ms [estimate, not measured]) and three bundles in the service, which the service does not support yet (one `MODEL_PATH`).

## Leak audits

| Date | Data | Test with a train copy (≤ 30) | Valid with a train copy (≤ 30) | Source |
|---|---|---|---|---|
| 2026-10-15 | leaky-52 | 20 of 223 (9%) | 36 of 278 | console output; `leak_audit.csv` (since overwritten) |
| 2026-10-15 | after pass 1 (51 classes) | 0 of 223; 7 at 31–40 | 0 of 278 | console output; `leak_audit.csv` (since overwritten) |
| 2026-10-15 | clean-49 | 0 of 209; 1 at ≤ 40 | 0 of 262 | console output; `leak_audit.csv` |
| 2026-10-18 | relish-48 with pust, foodbd and veg_cooking train photos added (123 classes, 5,313 images) | 0 of 209; 1 at ≤ 40; none of the closest training photos at ≤ 48 is from an extra dataset | 0 of 262 | console output; `leak_audit_extras_2026-10-18.csv` |

## Service-path checks (2026-10-16)

One-off scripts, output not saved to a file; the model is the exported seed 2 of the relish-48 runs (bundle threshold 0.85, chosen on the validation photos).

| Check | Result |
|---|---|
| 209 test photos (stored 256 px copies) through the service recogniser, CPU | test mAP 0.9090, micro-F1 at 0.5 0.8983 (identical to `runs/stage2_mobilenet_v3_large_imagenet_seed2_rl256_report.json`); micro-F1 at 0.85 0.9262; about 15 ms per photo |
| The same 209 photos at original size (short side 640 to 3,024 px) | test mAP 0.9047, micro-F1 at 0.5 0.8927, at 0.85 0.9199; largest single-score change 0.554, mean change 0.0021 |
| Real service over HTTP, one string-hoppers photo | `string_hoppers`, `mallum`, `white_rice` returned (the last two wrong); 3.7 s for the first request |
