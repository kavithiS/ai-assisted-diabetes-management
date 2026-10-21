# Demo checklist (PowerShell, folder `C:\Users\ALFARES\Desktop\c3-risk-profiling`)

## Before the panel
1. Close other apps (the laptop runs the model, the gateway and the app together).
2. Backend + phone window, one command:
   `.\server\services\c3_risk_xai\scripts\demo_phone.ps1`
   Wait for `All good`. Keep the **C3** and **Gateway** windows open.
3. Emulator instead (optional, 1-3 min boot):
   `& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd C3_Demo -no-snapshot -gpu swiftshader_indirect -no-boot-anim`
   then once, to get the latest app (includes the warm-up fix):
   `& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r client\mobile_app\build\app\outputs\flutter-apk\app-release.apk`
   and open **DiaCare** on it.
4. In the app: **Risk Profile** tab → chip says **Connected** (`demo.ps1` already warmed up the server).
5. The examples are hidden from app users: long-press the **Connected** chip → Settings → **Example answers** → **Higher-risk example** once
   (High, score 58), then Back twice to home.

Note: the DHS is adaptive. If you run the lower-risk example right after the higher-risk one on
the same device, its score is blended with the previous one (seen: 79 instead of 100). That is
by design; say "the score evolves with the patient's history". For a clean 100, use Settings →
"Delete my saved results" first (Settings: long-press the **Connected** chip).

## During the demo
| Click | Say |
|---|---|
| Long-press **Connected** → **Higher-risk example** | "Answers go through the gateway to C3." |
| (result) | "F1: High band, DHS 58, provisional, referral note." |
| Why this score | "F2: SHAP and LIME, agree on 4 of 5, not medical causes." |
| What you can do | "Templates for modifiable factors, never medicines." |
| Try a change (High activity → Update estimate) | "The score changes; the band does not, the model doesn't use lifestyle yet." |
| Past checks | "Saved in PostgreSQL with model and schema versions." |

## If something goes wrong
| Problem | Do this |
|---|---|
| App says **Not connected** | `.\server\services\c3_risk_xai\scripts\demo.ps1 -Research`, then **Check again** |
| "Port 8000 is already in use" | `.\server\services\c3_risk_xai\scripts\demo.ps1 -Action stop`, then start again |
| Emulator freezes or dies | Close it; use the phone window: `demo_phone.ps1` |
| First result is slow | Wait: the first check after a server start can take up to ~17 s (the app waits 30 s); `demo.ps1` warms this up |
| Everything fails | Play the backup video; show `http://127.0.0.1:8003/docs` and the code in `src/c3_risk_xai/` |

## Backup video
Click the app window, press **Win + Alt + R** to start/stop (saved in `Videos\Captures`).
Record the same click order as above.

## After
`.\server\services\c3_risk_xai\scripts\demo_phone.ps1 -Action stop`
