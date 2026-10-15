# Study the weakest classes

**Goal:** find out why some foods score low and choose what to try next (longer training, a bigger model, more photos).

**Weakest classes on the cleaned split, ImageNet start (2026-10-15)**, AP with test positives in brackets, from `runs/stage2_mobilenet_v3_large_imagenet_seed{0,1,2}_report.json`:

| Seed | Weakest classes |
|---|---|
| 0 | lunu_sambol 0.297 (3), fish_curry 0.593 (5), pol_sambol 0.611 (2), vegetable_salad 0.646 (3), pittu 0.71 (3) |
| 1 | submarine 0.2 (1), lunu_sambol 0.356 (3), lunu_miris 0.577 (3), fish_curry 0.619 (5), pittu 0.756 (3) |
| 2 | bean_curry 0.5 (1), pappadam 0.5 (1), lunu_miris 0.643 (3), vegetable_salad 0.656 (3), fish_curry 0.665 (5) |

With 1 to 5 test positives, one photo changes the AP a lot. Treat a class as weak only if it is low in **all three** seeds. Below 0.8 in all three seeds (same report files):

| Class | Seed 0 | Seed 1 | Seed 2 |
|---|---|---|---|
| fish_curry | 0.593 | 0.619 | 0.665 |
| lunu_miris | 0.722 | 0.577 | 0.643 |
| pittu | 0.71 | 0.756 | 0.7 |
| vegetable_salad | 0.646 | 0.792 | 0.656 |

`lunu_sambol` is the lowest in seeds 0 and 1 (0.297, 0.356) but 0.778 in seed 2; `pol_sambol` is 0.611 / 0.833 / 0.7.

## Steps

1. For each class, collect AP and `test_positives` from all three report files of the run you study.
2. Count the train scenes and photos for each weak class (from `processed_manifest.csv`: rows with `role == keep`, `suggested_split == train`, the class in `classes`; scenes = distinct `group_id`).
3. Look at the test photos of the weak class. Is the food small on a mixed plate? Is it a side dish next to rice? Is the label itself consistent across datasets?
4. Choose one change and run it as in `run-stage2-experiment.md`:
   - more epochs (`--epochs 25`): cheap, try first;
   - `--arch efficientnet_v2_s`: slower, not run yet;
   - more photos for thin classes: needs a new secondary dataset, which needs a licence check and owner approval (ADR 0002).
5. Compare per-class AP across three seeds, not one.

## Done when

The weak classes are listed with their train scene counts, at least one change has been tried over three seeds, and the result is recorded.

## Record

`CONTEXT.md` section 10 (weakest classes), `EXPERIMENTS.md`, `CHANGELOG.md`, `OPEN_ITEMS.md` section C.
