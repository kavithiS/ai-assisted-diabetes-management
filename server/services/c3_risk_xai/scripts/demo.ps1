<#
.SYNOPSIS
  One command to run the C3 demo: C3 service + API gateway, health check, warm-up.

.DESCRIPTION
  Starts C3 (port 8003) and the gateway (port 8000) in their own windows, waits until the
  gateway answers, sends one warm-up assessment (loads SHAP/LIME), and prints the status.
  Uses 127.0.0.1, not localhost: on Windows "localhost" costs about 2 s per hop.
  Does not touch scripts/dev.ps1 (shared) and needs no database for this phase.

.EXAMPLE
  .\server\services\c3_risk_xai\scripts\demo.ps1               # start, wait, warm up
  .\server\services\c3_risk_xai\scripts\demo.ps1 -Chrome       # ... and open the app in Chrome
  .\server\services\c3_risk_xai\scripts\demo.ps1 -Action check # health check only
  .\server\services\c3_risk_xai\scripts\demo.ps1 -Action stop  # stop C3 and the gateway
#>
param(
    [ValidateSet("start", "check", "stop")]
    [string]$Action = "start",
    # Lets the hidden Researcher view show the probability (never on patient screens).
    [switch]$Research,
    # Gateway listens on all interfaces so a phone on the same Wi-Fi can reach it.
    [switch]$Phone,
    # Also run the Flutter app in Chrome (development only: web security is turned off
    # because the gateway has no CORS yet, see docs/pr_notes/gateway_note.md).
    [switch]$Chrome,
    # Run the services without windows, logging to data/c3/outputs/logs (used for tests).
    [switch]$Hidden
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Gateway = "http://127.0.0.1:8000"
$C3 = "http://127.0.0.1:8003"
$Ports = @(8000, 8003)

function Test-Url([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return @{ Ok = $true; Body = $response.Content }
    } catch {
        return @{ Ok = $false; Body = $_.Exception.Message }
    }
}

function Show-Check {
    $checks = [ordered]@{
        "C3 service    $C3/health"                  = "$C3/health"
        "C3 models     $C3/v1/risk/status"          = "$C3/v1/risk/status"
        "Gateway       $Gateway/health"             = "$Gateway/health"
        "Gateway -> C3 $Gateway/api/v1/risk/status" = "$Gateway/api/v1/risk/status"
    }
    $allOk = $true
    foreach ($name in $checks.Keys) {
        $result = Test-Url $checks[$name]
        $mark = if ($result.Ok) { "OK  " } else { "FAIL"; $allOk = $false }
        Write-Host ("[{0}] {1}  {2}" -f $mark, $name, $result.Body)
    }
    if ($allOk) { Write-Host "All good. App URL: $Gateway" -ForegroundColor Green }
    else { Write-Host "Something is not running. Start it with: $PSCommandPath" -ForegroundColor Yellow }
    return $allOk
}

function Stop-Demo {
    foreach ($port in $Ports) {
        $owners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($id in $owners) {
            Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
            Write-Host "Stopped process $id on port $port"
        }
    }
}

function Start-Uvicorn([string]$Name, [string]$Module, [int]$Port, [string]$HostName, [hashtable]$Env) {
    $envLines = ($Env.GetEnumerator() | ForEach-Object { "`$env:$($_.Key) = '$($_.Value)';" }) -join " "
    $run = "& '$Python' -m uvicorn $Module --host $HostName --port $Port"
    if ($Hidden) {
        $logs = Join-Path $RepoRoot "data\c3\outputs\logs"
        New-Item -ItemType Directory -Force -Path $logs | Out-Null
        $command = "$envLines $run *> '$logs\$Name.log'"
        Start-Process powershell -WorkingDirectory $RepoRoot -WindowStyle Hidden `
            -ArgumentList "-NoProfile", "-Command", $command | Out-Null
    } else {
        $command = "`$Host.UI.RawUI.WindowTitle = '$Name ($Port)'; $envLines $run"
        Start-Process powershell -WorkingDirectory $RepoRoot -ArgumentList "-NoExit", "-Command", $command | Out-Null
    }
    Write-Host "Starting $Name on port $Port"
}

if ($Action -eq "check") { if (Show-Check) { exit 0 } else { exit 1 } }
if ($Action -eq "stop") { Stop-Demo; exit 0 }

if (-not (Test-Path $Python)) {
    throw "No Python environment at $Python. Create it first (uv sync, see the C3 README)."
}
foreach ($port in $Ports) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Run: $PSCommandPath -Action stop"
    }
}

$c3Env = @{ C3_RESEARCH_MODE = $(if ($Research) { "true" } else { "false" }) }
$gatewayEnv = @{
    C1_URL = "http://127.0.0.1:8001"
    C2_URL = "http://127.0.0.1:8002"
    C3_URL = $C3
    C4_URL = "http://127.0.0.1:8004"
}
Start-Uvicorn "C3 risk_xai" "c3_risk_xai.main:app" 8003 "127.0.0.1" $c3Env
Start-Uvicorn "Gateway" "diacare_gateway.main:app" 8000 $(if ($Phone) { "0.0.0.0" } else { "127.0.0.1" }) $gatewayEnv

Write-Host "Waiting for the gateway and C3 (up to 90 s)..."
$deadline = (Get-Date).AddSeconds(90)
while (-not (Test-Url "$Gateway/api/v1/risk/status").Ok) {
    if ((Get-Date) -gt $deadline) { throw "Gateway/C3 did not start. Look at their windows or data\c3\outputs\logs." }
    Start-Sleep -Seconds 2
}

Write-Host "Warming up the model (first SHAP/LIME call)..."
$body = '{"age": 29, "sex_male": 0, "bmi": 21.5, "systolic_bp": 112, "diastolic_bp": 72}'
$watch = [Diagnostics.Stopwatch]::StartNew()
try {
    Invoke-WebRequest -Uri "$Gateway/api/v1/risk/assess" -Method Post -Body $body `
        -ContentType "application/json" -UseBasicParsing -TimeoutSec 60 | Out-Null
    Write-Host ("Warm-up done in {0:N1} s" -f $watch.Elapsed.TotalSeconds)
} catch {
    Write-Host "Warm-up failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

Show-Check | Out-Null
if ($Phone) {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -eq "Dhcp" } |
        Select-Object -First 1).IPAddress
    Write-Host "Phone URL: http://${ip}:8000 (allow port 8000 in the firewall once, see docs/flutter_demo.md)"
}

if ($Chrome) {
    Push-Location (Join-Path $RepoRoot "client\mobile_app")
    try {
        flutter run -d chrome --dart-define=API_BASE_URL=$Gateway --web-browser-flag "--disable-web-security"
    } finally {
        Pop-Location
    }
}
