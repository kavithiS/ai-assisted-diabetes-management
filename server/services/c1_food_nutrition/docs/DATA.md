# C1 data card

All image data and model files stay **out of git**. This file describes them; it holds none of them. Do not redistribute any dataset. Counts come from `preprocess_report.json`, `food101_report.json`, `summary.json` and the dataset READMEs.

## Location

On the owner's PC: `D:\RESEARCH PROJECT\Foods datasets for training\`. Planned setting for scripts: `C1_DATA_DIR` (not implemented yet).

```
Foods datasets for training/
  Images Datasets/
    <raw dataset folders>        originals, never edited
    _curation/                   manifests, reports, scripts/, training/
    _processed/<dataset>/        resized RGB copies (short side 256 px)
  c1_sri_lanka_food_data/        nutrition tables (see below)
```

## Image datasets

| Key | Dataset | Used for | Licence |
|---|---|---|---|
| food_detect | Roboflow, 11 Sri Lankan dishes | Stage 2 | CC BY 4.0 |
| shorteats | Roboflow, Sri Lankan short eats | Stage 2 | CC BY 4.0 |
| sl_meal | Roboflow, rice-and-curry plates with polygons | Stage 2 | CC BY 4.0 |
| kaggle_sl26 | Kaggle, 26 Sri Lankan classes (mostly mirror copies) | Stage 2 | **not stated** |
| veg_cooking | Kaggle, vegetable cooking states (8 classes) | off by default (`--also`) | **dataset licence not verified** |
| pust | PUST Cafeteria (Bangladesh) | optional (`--also pust`) | CC BY 4.0 intended; DOI not filled in |
| foodbd | FoodBD (Bangladesh), polygons and nutrition | optional (`--also foodbd`) | **not verified** |
| Food-101 | 101 classes x 1,000 images | Stage 1 | see the dataset page |

Processed (kept) images per dataset: food_detect 766, foodbd 3,518, kaggle_sl26 1,320, pust 720, shorteats 129, sl_meal 107, veg_cooking 322; total 6,882. Food-101 kept 100,895 of 101,000.

Source links are in `_curation/README.md`.

## Manifest columns (`processed_manifest.csv`)

The clean manifest columns plus `processed_rel_path`, `orig_w`, `orig_h`, `orig_mode`, `proc_w`, `proc_h`, `proc_note`, `proc_error`. Key columns: `image_id`, `dataset`, `rel_path`, `role` (use `keep` only), `role_original`, `clean_note`, `group_id`, `group_size`, `split_provided`, `suggested_split` (train / valid / test), `classes` (clean class names, several joined with `|`), `concept_ids`, `licence`, `source_url`. Food-101 has its own `food101_manifest.csv` and `food101_split/{classes,train,test}.txt`.

## Rules for using the data

1. Split by `group_id`. Use rows with `role == keep`. Flip images during training instead of using stored mirror copies.
2. Use processed copies for classification only; box and polygon annotations refer to original sizes.
3. Never use FoodBD `gl_reported`.
4. Food-101 split is reconstructed (75/25 by scene group); official lists are missing.

## Rebuild order (all scripts skip finished work)

From `_curation/`: `scripts/build_curation.py` then `scripts/make_class_map.py`, `scripts/make_clean_manifest.py`, `scripts/preprocess_images.py` (add `--datasets pust foodbd` for the Bangladeshi sets), then `scripts/process_food101.py --workers 4` (and `--finalize`). Needs Python and Pillow. `BUDGET=<n>` runs in short rounds.

## Nutrition tables (`c1_sri_lanka_food_data/`, copy in `data/c1/`)

- Use **`c1_foods_combined.csv`**: 2,716 foods per 100 g, 36 columns (241 Sri Lankan, 2,475 related). Lookup: find the food's concept in `food_concepts.csv` (118 concepts), then take the lowest `lookup_priority_in_concept` in `food_metadata.csv`.
- `carbohydrate_g` is **available** carbohydrate (fibre excluded); `fibre_g` is dietary fibre only; `vitamin_a_ug` is RAE only.
- Blanked: vitamin B12 and vitamin D in the Sri Lankan table (see `OPEN_ITEMS.md` A2). 77 foods are listed in `excluded_foods.csv`. Every changed value is in `value_flags.csv`.
- The export has no blank cells, so a 0 in a vitamin column may mean "not measured".
- There is no sugars column.
