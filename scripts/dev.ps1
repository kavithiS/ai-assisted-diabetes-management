# Starts the DiaCare AI gateway and C1-C4 services locally, one PowerShell window each.
# From the repository root:  .\scripts\dev.ps1
# Requires: uv sync already run. PostgreSQL 16 and MLflow are started separately (see README).

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

$Services = @(
    @{ Name = "C1 food_nutrition";        Module = "c1_food_nutrition.main:app";       Port = 8001 },
    @{ Name = "C2 glycemic_forecasting";  Module = "c2_glycemic_forecasting.main:app"; Port = 8002 },
    @{ Name = "C3 risk_xai";              Module = "c3_risk_xai.main:app";             Port = 8003 },
    @{ Name = "C4 foot_monitoring";       Module = "c4_foot_monitoring.main:app";      Port = 8004 }
)

function Start-ServiceWindow {
    param([string]$Name, [string]$Module, [int]$Port, [string]$Prelude = "")
    $Command = "`$Host.UI.RawUI.WindowTitle = '$Name ($Port)'; $Prelude uv run uvicorn $Module --port $Port --reload"
    Start-Process powershell -WorkingDirectory $RepoRoot -ArgumentList "-NoExit", "-Command", $Command
    Write-Host "Started $Name on http://localhost:$Port"
}

foreach ($Service in $Services) {
    Start-ServiceWindow -Name $Service.Name -Module $Service.Module -Port $Service.Port
}

# Service URLs read by diacare_gateway.config.GatewaySettings (c1_url ... c4_url).
$GatewayEnv = @(
    "`$env:C1_URL = 'http://localhost:8001';",
    "`$env:C2_URL = 'http://localhost:8002';",
    "`$env:C3_URL = 'http://localhost:8003';",
    "`$env:C4_URL = 'http://localhost:8004';"
) -join " "

Start-ServiceWindow -Name "Gateway" -Module "diacare_gateway.main:app" -Port 8000 -Prelude $GatewayEnv

Write-Host "All services started. Check http://localhost:8000/health"
