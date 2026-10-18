# Starts the backend the app needs: C1 (port 8001) and the gateway (port 8000), one window each.
# From anywhere:  .\server\services\c1_food_nutrition\scripts\start_backend.ps1
# A service whose port is already in use is left alone. PostgreSQL must already be running.

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
function Test-PortInUse([int]$Port) {
    $null -ne (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Start-Window([string]$Title, [string]$Command) {
    $Full = "`$Host.UI.RawUI.WindowTitle = '$Title'; $Command"
    Start-Process powershell -WorkingDirectory $RepoRoot -ArgumentList "-NoExit", "-Command", $Full
}

if (Test-PortInUse 8001) {
    Write-Host "C1 already running on 8001"
} else {
    # start_c1.ps1 turns on the trained model and the nutrition table; plain uvicorn would run the mock.
    Start-Window "C1 (8001)" "& '$PSScriptRoot\start_c1.ps1'"
    Write-Host "Started C1 on http://localhost:8001"
}

if (Test-PortInUse 8000) {
    Write-Host "Gateway already running on 8000"
} else {
    Start-Window "Gateway (8000)" "uv run uvicorn diacare_gateway.main:app --host 0.0.0.0 --port 8000 --app-dir server/gateway/src"
    Write-Host "Started gateway on http://localhost:8000"
}

Write-Host "C1 takes about 10 seconds to load its model. Then check http://localhost:8000/health"
Write-Host "(status 'degraded' is normal: C2-C4 are not built yet.)"
