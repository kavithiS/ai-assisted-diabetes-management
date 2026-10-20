<#
.SYNOPSIS
  C3 demo in a phone-sized window on this laptop (no emulator needed).

.DESCRIPTION
  1. Starts C3 + gateway with demo.ps1 (skipped if they already answer).
  2. Builds the Flutter web app once (release, into client\mobile_app\build\web_phone).
  3. Serves it on http://127.0.0.1:5180 and opens Chrome in app mode, phone-sized
     (412 x 915), with a separate temporary profile and web security off. Your normal
     Chrome profile is never touched. Web security is off only because the gateway has
     no CORS yet (docs/pr_notes/gateway_note.md); this window is for the local demo only.

.EXAMPLE
  .\server\services\c3_risk_xai\scripts\demo_phone.ps1            # start everything, open the phone window
  .\server\services\c3_risk_xai\scripts\demo_phone.ps1 -C3Only    # open straight on the C3 screens
  .\server\services\c3_risk_xai\scripts\demo_phone.ps1 -Rebuild   # rebuild the web app after code changes
  .\server\services\c3_risk_xai\scripts\demo_phone.ps1 -Action stop
#>
param(
    [ValidateSet("start", "stop")]
    [string]$Action = "start",
    [switch]$C3Only,
    [switch]$Rebuild,
    [int]$Width = 412,
    [int]$Height = 915
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$App = Join-Path $RepoRoot "client\mobile_app"
$Web = Join-Path $App "build\web_phone"
# Not 5060: Chrome blocks it (ERR_UNSAFE_PORT, reserved for SIP).
$Port = 5180
$Chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$Profile = Join-Path $env:TEMP "c3-phone-demo-profile"
$Demo = Join-Path $PSScriptRoot "demo.ps1"

function Stop-Port([int]$p) {
    Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
}

if ($Action -eq "stop") {
    Stop-Port $Port
    & $Demo -Action stop
    Write-Host "Phone demo stopped."
    exit 0
}

# 1. Servers (C3 + gateway), unless they already answer.
$up = $false
try {
    Invoke-WebRequest "http://127.0.0.1:8000/api/v1/risk/status" -UseBasicParsing -TimeoutSec 5 | Out-Null
    $up = $true
} catch { }
if ($up) { Write-Host "C3 and the gateway are already running." }
else { & $Demo -Research }

# 2. Web build (once; -Rebuild after code changes).
$entry = if ($C3Only) { "lib/features/risk_profile/c3_standalone.dart" } else { "lib/main.dart" }
$marker = Join-Path $Web "c3_entry.txt"
$builtFor = if (Test-Path $marker) { Get-Content $marker } else { "" }
if ($Rebuild -or -not (Test-Path (Join-Path $Web "index.html")) -or $builtFor -ne $entry) {
    Write-Host "Building the web app ($entry), about 1-2 minutes..."
    Push-Location $App
    try {
        flutter build web --release -t $entry --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-web-resources-cdn -o build/web_phone
        if ($LASTEXITCODE -ne 0) { throw "flutter build web failed" }
        Set-Content -Path $marker -Value $entry
    } finally {
        Pop-Location
    }
}

# Fit the window on this screen (a 864 px laptop screen cut off the bottom tab bar).
Add-Type -AssemblyName System.Windows.Forms
$work = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
if ($Height -gt $work.Height - 30) { $Height = $work.Height - 30 }

# 3. Serve the build and open the phone-sized window.
Stop-Port $Port
Start-Process $Python -ArgumentList "-m", "http.server", "$Port", "--bind", "127.0.0.1", "--directory", "`"$Web`"" -WindowStyle Hidden
Start-Sleep -Seconds 2
Start-Process $Chrome -ArgumentList @(
    "--app=http://127.0.0.1:$Port/",
    "--window-size=$Width,$Height",
    "--window-position=40,0",
    "--user-data-dir=`"$Profile`"",
    "--disable-web-security",
    "--no-first-run",
    "--no-default-browser-check"
)
Write-Host "Phone window opened ($Width x $Height). Stop everything with: $PSCommandPath -Action stop"
