# Start C1 with a separately shared model bundle and nutrition table.
# See ../docs/MODEL_HANDOFF.md before using this on another machine.
# Override C1_PYTHON, MODEL_PATH and NUTRITION_TABLE_PATH as needed.

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path

if (-not $env:C1_PYTHON) { $env:C1_PYTHON = Join-Path $repo ".venv\Scripts\python.exe" }
if (-not $env:MODEL_PATH) { $env:MODEL_PATH = Join-Path $repo "data\c1\c1_model_bundle.pt" }
if (-not $env:NUTRITION_TABLE_PATH) { $env:NUTRITION_TABLE_PATH = Join-Path $repo "data\c1\c1_foods_combined.csv" }
if (-not $env:MODEL_DEVICE) { $env:MODEL_DEVICE = "cpu" }
$env:RECOGNIZER = "torch"

foreach ($entry in @{ C1_PYTHON = $env:C1_PYTHON; MODEL_PATH = $env:MODEL_PATH; NUTRITION_TABLE_PATH = $env:NUTRITION_TABLE_PATH }.GetEnumerator()) {
    if (-not (Test-Path -LiteralPath $entry.Value -PathType Leaf)) {
        throw "$($entry.Key) not found: $($entry.Value). See server/services/c1_food_nutrition/docs/MODEL_HANDOFF.md"
    }
}

Set-Location $repo
Write-Host "C1: trained model + nutrition table, http://0.0.0.0:8001"
& $env:C1_PYTHON -m uvicorn c1_food_nutrition.main:app --host 0.0.0.0 --port 8001
