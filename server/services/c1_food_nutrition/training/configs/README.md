# configs/

> **TODO(c1):** copied from the old `c1_kavithi` branch. Paths in this file predate the
> monorepo move: the service now serves `/v1/meals/analyze` (the gateway exposes it as
> `/api/v1/meals/analyze`), `/docs` and `/openapi.json`. Docker is no longer used (ADR 0003),
> and C1 uses secondary datasets only (ADR 0002).

YAML configuration for ML work. Every MLflow run must log the exact config files it used.

| Folder   | Purpose                                                     | Status (Phase 0)            |
|----------|-------------------------------------------------------------|-----------------------------|
| `data/`  | Dataset source definitions, selected by `kind`              | Candidate sources only      |
| `model/` | Backbone configs (EfficientNetV2, MobileNetV3 via timm)      | Empty, added in Phase 1     |
| `train/` | Seeds, hyperparameters, augmentation                         | Empty, added in Phase 1     |

No dataset sizes, class counts or results are recorded here until they have been measured.
