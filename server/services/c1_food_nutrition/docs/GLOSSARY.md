# Glossary

| Term | Meaning |
|---|---|
| **Scene / `group_id`** | One real meal photographed once, plus its flips, crops and burst shots. Splits are made by scene so copies never sit in both train and test. |
| **Leak** | The same scene appearing in train and in valid or test. It makes scores look better than they are. |
| **Manifest** | A CSV with one row per image: dataset, label, role, group, split. `processed_manifest.csv` is the one training reads. |
| **Role** | `keep` is used. `mirror_copy`, `exact_duplicate`, `augmented_copy`, `near_duplicate`, `cross_class_duplicate`, `missing_file`, `unreadable`, `leak_dropped` are skipped. |
| **Multi-label** | One plate can contain several foods, so each class is a yes/no output. |
| **Train / valid / test** | Train teaches the model, valid picks the best epoch, test is looked at once for the final score. |
| **mAP** | Mean of the per-class average precision (AP); 1.0 is perfect. Good for rare classes. |
| **micro-F1** | One F1 score over all class decisions together; dominated by common classes. |
| **top-1** | The share of images where the model's first guess is right (single-label, used for Food-101). |
| **Stage 1 / Stage 2** | Stage 1 teaches general food knowledge on Food-101. Stage 2 fine-tunes on Sri Lankan dishes. |
| **Pretraining** | Starting from weights that already learned something (ImageNet, or Stage 1) instead of random ones. |
| **Seed** | A number that fixes the randomness. Three seeds show how much a score moves by chance. |
| **`--min-scenes N`** | Drops classes with fewer than N train scenes. 5 gives 52 classes, 1 gives 78. Only compare runs with the same value. |
| **Reconstructed split** | A 75/25 split we made ourselves for Food-101 because the official lists are missing. |
| **Per 100 g** | All nutrition values are per 100 g of food; a portion is scaled by grams / 100. |
| **Available carbohydrate** | Carbohydrate without fibre. This is what `carbohydrate_g` means in the nutrition table. |
| **`null` vs `0`** | `null` means unknown ("Not available"); `0` means measured as zero. Never mix them. |
| **Reference card** | A bank-card-sized object (85.60 x 53.98 mm) placed next to the plate to measure scale. |
| **FCDB** | Food composition database, here the Sri Lankan one. **FDC** is USDA FoodData Central. |
