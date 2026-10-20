# C1 scan handoff for another team member

Git contains the C1 service, training/export code and class-to-food mapping, **not** the
trained weights or composition table. The model and table must be transferred through a
team-approved private location after checking their redistribution terms. Do not add either
file to Git, and do not send an `.env` file or credentials with them.

## Files verified on the C1 owner's machine (2026-10-20)

| File to share | Current local source | Size | SHA-256 |
|---|---|---:|---|
| Trained bundle | `D:\RESEARCH PROJECT\Foods datasets for training\Images Datasets\_curation\training\runs\stage2_mobilenet_v3_large_imagenet_seed2_rl256_brinjal_t050_bundle.pt` | 17,284,313 bytes | `DD631D3011F384AE612FFD1C90714869A4C2D23CD9EF65D1464EA3A4C302A881` |
| Composition table | `data/c1/c1_foods_combined.csv` | 656,216 bytes | `FAD17EAC176609AB0CA0ABBCFB6D9A29879EF37936B2FF1F94F9431028995062` |

The verified bundle is `c1-recognizer/v1`, MobileNetV3-Large, 48 classes, 256-pixel
input, global threshold 0.85 and `brinjal_dish` threshold 0.50. These settings and the
class list are **inside the bundle**; no separate model-config file is needed. The table
has 2,720 rows, including 241 Sri Lankan, 232 USDA Foundation and 4 USDA SR Legacy
rows. The other regional rows are present but ignored by the current lookup pending
supervisor approval. The C1 portion estimator is still a fixed 100 g research-prototype
placeholder; a successful scan is not a measured portion.

The table includes third-party composition data. Confirm that the approved private
sharing route and each source's terms permit this transfer. If not, the owner must give
the teammate the source/import instructions instead of uploading the combined table.

## Recipient setup (Windows PowerShell)

1. Merge the reviewed C1 handoff changes. Put the transferred bundle at
   `data/c1/c1_model_bundle.pt` and the CSV at `data/c1/c1_foods_combined.csv`, or set
   `MODEL_PATH` and `NUTRITION_TABLE_PATH` to their actual paths. `data/c1/` is ignored
   by Git; verify `git status` does not include the files.
2. Use a Python 3.11 environment with the C1 package, PyTorch, torchvision and the
   service dependencies installed (see `training/README.md`). Set `C1_PYTHON` to that
   environment's `python.exe`. The repository's default `uv` environment does not
   include PyTorch.
3. From the repo root, verify the transfer and start the service:

   ```powershell
   $env:C1_PYTHON = 'C:\path\to\c1-server-env\Scripts\python.exe'
   Get-FileHash -Algorithm SHA256 -LiteralPath 'data\c1\c1_model_bundle.pt'
   Get-FileHash -Algorithm SHA256 -LiteralPath 'data\c1\c1_foods_combined.csv'
   & $env:C1_PYTHON -c 'import torch, torchvision, c1_food_nutrition'
   powershell -ExecutionPolicy Bypass -File .\server\services\c1_food_nutrition\scripts\start_c1.ps1
   ```

   Both hashes must match the values above. The script sets `RECOGNIZER=torch`,
   `MODEL_PATH`, `NUTRITION_TABLE_PATH` and `MODEL_DEVICE=cpu` (unless overridden).
   It fails early if a required file is missing. A plain `uv run uvicorn ...` without
   these settings uses the mock recognizer and mock nutrition lookup.
4. Check `http://localhost:8001/health` and the startup log for
   `Food recogniser ready.` Then test `/v1/meals/analyze` with a generated or permitted
   non-patient JPEG/PNG through the authenticated gateway. `/health` alone does not
   prove that a scan works. Keep the gateway's `INTERNAL_TOKEN` aligned with C1, but
   share that secret separately through the team's credential channel.

## Integration caveats

- The current `integration/c1-c2` branch has the older class map: `brinjal_dish` and
  `pappadam` have no nutrition match there. The reviewed C1 changes to
  `ml/data/class_concepts.csv` and the loader must be merged as well. The latest
  bundle's brinjal-specific threshold is ignored by the older loader.
- C1 is reached at `localhost:8001` only when C1 and the gateway run on the same
  machine. A teammate cannot reach the owner's `localhost` by copying database
  credentials. Configure the gateway's C1 URL to the actual reachable service.
- The C1 CSV is used for scan nutrition lookup; a PostgreSQL export is a separate
  matter for saved meal history. Do not assume sharing database credentials transfers
  either the model or the CSV.
