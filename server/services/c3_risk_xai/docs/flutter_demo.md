# Running the C3 Flutter demo (v1 model)

PowerShell, from the repository root. The app talks only to the gateway (port 8000), which
forwards `/api/v1/risk/*` to C3 (port 8003).

## 1. One command: start C3 + gateway, wait, warm up, health check

```powershell
.\server\services\c3_risk_xai\scripts\demo.ps1 -Research          # services only
.\server\services\c3_risk_xai\scripts\demo.ps1 -Research -Chrome  # ... and the app in Chrome
.\server\services\c3_risk_xai\scripts\demo.ps1 -Action check      # health check
.\server\services\c3_risk_xai\scripts\demo.ps1 -Action stop       # stop both
```

It opens one window per service, uses 127.0.0.1 (localhost costs ~2 s per hop on Windows)
and sends one warm-up assessment: the first SHAP/LIME call took 11.2 s, longer than the
app's 10 s timeout. `-Research` only lets the hidden Researcher view show the probability.
It uses the repository's `.venv` Python, so `uv` itself is not needed.

## 2a. Chrome (development, supervisor demo)

The gateway has no CORS yet (`pr_notes/gateway_note.md`), so Chrome runs without web
security (`-Chrome` does this). That Chrome profile is separate and local only; never
browse with it. Manual equivalent:

```powershell
cd client\mobile_app
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000 --web-browser-flag "--disable-web-security"
# C3 only (fallback if another tab breaks):
flutter run -d chrome -t lib/features/risk_profile/c3_standalone.dart --dart-define=API_BASE_URL=http://127.0.0.1:8000 --web-browser-flag "--disable-web-security"
```

If the gateway is down, the app shows "Not connected" with this command and a
"Check again" button (checked in Chrome on 2026-10-19).

## 2b. Android emulator

```powershell
flutter emulators --launch Pixel_9
cd client\mobile_app
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

The emulator's `10.0.2.2` is the laptop's `127.0.0.1`, so the gateway command above works.

## 2c. Phone on the same Wi-Fi, or release APK (PP1 fallback)

```powershell
ipconfig                      # note the laptop's IPv4 address, e.g. 192.168.1.20
# Gateway with --host 0.0.0.0, then allow port 8000 once (admin PowerShell):
New-NetFirewallRule -DisplayName "DiaCare gateway 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private
cd client\mobile_app
flutter build apk --release --dart-define=API_BASE_URL=http://192.168.1.20:8000
# APK: client\mobile_app\build\app\outputs\flutter-apk\app-release.apk
```

The URL can also be changed in the app: long-press the connection status, Settings.

## 3. Demo check (must match Python)

| Preset | Expected (v1, verified 2026-10-19 through the gateway) |
|---|---|
| Higher-risk example | High band, referral shown, with-glucose model (random forest) |
| Lower-risk example | Low band, no referral |
| Missing BMI example | "We need a few more answers", no band, BMI listed |

Press "Warm up the model" once first: the first call loads SHAP/LIME and took 9.7 s.
Long-press the result title for the Researcher view (probability 0.5657 for the
higher-risk example). Patient screens never show it.
