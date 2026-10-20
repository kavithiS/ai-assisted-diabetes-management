# Starts C1 with the trained food recogniser and the real nutrition table.
# Plain `uv run uvicorn ...` starts the mock recogniser and mock nutrition instead,
# because PyTorch is not in uv.lock (OPEN_ITEMS D, item 56).
#
# Usage (from anywhere):  powershell -ExecutionPolicy Bypass -File server\services\c1_food_nutrition\scripts\start_c1.ps1
# Override any path by setting the variable before running, e.g.  $env:MODEL_PATH = "..."

$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")

if (-not $env:C1_PYTHON) { $env:C1_PYTHON = "D:\RESEARCH PROJECT\c1_server_env\Scripts\python.exe" }
if (-not $env:MODEL_PATH) {
    $env:MODEL_PATH = "D:\RESEARCH PROJECT\Foods datasets for training\Images Datasets\_curation\training\runs\stage2_mobilenet_v3_large_imagenet_seed2_rl256_bundle.pt"
}
if (-not $env:NUTRITION_TABLE_PATH) { $env:NUTRITION_TABLE_PATH = Join-Path $repo "data\c1\c1_foods_combined.csv" }
$env:RECOGNIZER = "torch"

foreach ($p in @($env:C1_PYTHON, $env:MODEL_PATH, $env:NUTRITION_TABLE_PATH)) {
    if (-not (Test-Path $p)) { throw "Not found: $p" }
}

Set-Location $repo
Write-Host "C1: trained model + nutrition table, http://0.0.0.0:8001"
& $env:C1_PYTHON -m uvicorn c1_food_nutrition.main:app --host 0.0.0.0 --port 8001
