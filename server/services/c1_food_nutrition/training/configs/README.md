# configs/

YAML configuration for ML work, read by `src/c1_food_nutrition/ml/data/registry.py`.

C1 uses secondary datasets only (ADR 0002). The training scripts do not read these files yet:
they take command-line arguments and record the settings they used in each run's JSON report
(see `docs/CONTEXT.md` section 9). MLflow is not used.

| Folder   | Purpose                                                     | Status (2026-10-15)         |
|----------|-------------------------------------------------------------|-----------------------------|
| `data/`  | Dataset source definitions, selected by `kind`              | `food101.yaml` only (candidate; loading not implemented) |
| `model/` | Backbone settings (MobileNetV3-Large, EfficientNetV2-S, torchvision) | Not created          |
| `train/` | Seeds, hyperparameters, augmentation                         | Not created                 |

No dataset sizes, class counts or results are recorded here until they have been measured.
