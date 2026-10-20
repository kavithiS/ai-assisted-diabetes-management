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

## 2b. Run on a phone emulator (PP1 demo)

Use the **C3_Demo** emulator (Pixel 6 shape, Android 16 *Google APIs* image, 2 GB RAM),
created 2026-10-19. The older Pixel_9 uses a *Play Store* image, which blocks adb with an
"Allow USB debugging?" dialog until someone clicks Allow inside the emulator.

```powershell
# 1. Servers (one window each, warm-up included)
.\server\services\c3_risk_xai\scripts\demo.ps1 -Research

# 2. Emulator: cold boot, no snapshot (about 3 minutes; keeps the nearly full C: drive safe)
& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd C3_Demo -no-snapshot -gpu swiftshader_indirect -no-boot-anim
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" devices     # wait for: emulator-5554  device

# 3a. Installed app (fastest, no build): the release APK
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r client\mobile_app\build\app\outputs\flutter-apk\app-release.apk

# 3b. Or build and run in debug from source (slower first time)
cd client\mobile_app
flutter run -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

The emulator's `10.0.2.2` is the laptop's `127.0.0.1`, so the gateway can keep listening
on 127.0.0.1 (no firewall change). The app has the INTERNET permission and allows plain
`http` (the local gateway has no HTTPS yet).

Type on the laptop keyboard into the emulator (C3_Demo has `hw.keyboard = yes`).
Before the panel: open the Risk Profile tab, press **Warm up the model**, run one preset.

If the emulator misbehaves: close it, start it again with the same command (cold boot).
Free disk space matters: keep at least 5 GB free on C:.

## 2c. Phone-sized window without an emulator (fallback)

```powershell
.\server\services\c3_risk_xai\scripts\demo_phone.ps1            # servers + 412 x 915 app window
.\server\services\c3_risk_xai\scripts\demo_phone.ps1 -C3Only    # opens straight on C3
.\server\services\c3_risk_xai\scripts\demo_phone.ps1 -Action stop
```

It opens Chrome in app mode with its own temporary profile (your normal Chrome profile is
not touched). Second option, by hand: open the app in Chrome, press **F12**, then
**Ctrl+Shift+M** (device toolbar) and choose a phone such as "Pixel 7" or "iPhone 14".

## 2d. Real phone on the same Wi-Fi (release APK)

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

## 4. Record a 2-minute backup video

- **Any window (emulator or phone window):** click the window, press **Win + Alt + R**
  (Xbox Game Bar) to start and stop. The video goes to `Videos\Captures`.
- **Inside the emulator only:** in the emulator's side bar, `...` (Extended controls) >
  **Record and Playback** > Start recording; or from PowerShell:
  `adb shell screenrecord --time-limit 150 /sdcard/c3_demo.mp4` then
  `adb pull /sdcard/c3_demo.mp4 .`
- Record the story: Risk Profile tab > Higher-risk example > result (DHS 58, High) >
  Understand my risk > Recommendations > What-if (High activity, Estimate) > back > Past results.

## 5. Disk space and speed (this laptop)

- The C: drive was 99% full. The emulator keeps a ~9 GB temporary disk while it runs, and a
  release APK build needs several GB: never build the APK while the emulator is running.
- Keep at least 10 GB free on PP1 day; close VS Code, browsers and other apps during the demo
  (the 4-core laptop runs the ML service, the gateway and the emulator together).
