# PP1 day card (C3, 2 minutes, 2 slides)

PowerShell, always first: `cd C:\Users\ALFARES\Desktop\c3-risk-profiling`

## Start (in this order, 30 min before)
1. Close other apps. Plug in the charger.
2. Servers + phone window (one command):
   `.\server\services\c3_risk_xai\scripts\demo_phone.ps1`
   Wait for `All good`. Keep the **C3** and **Gateway** windows open.
3. Emulator instead (optional, boots in 1-3 min, needs ~10 GB free on C:):
   `& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd C3_Demo -no-snapshot -gpu swiftshader_indirect -no-boot-anim`
   Once: `& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r client\mobile_app\build\app\outputs\flutter-apk\app-release.apk`
4. App: **Risk Profile** tab → **Connected** → long-press the **Connected** chip → Settings → **Example answers** → run **Higher-risk example** once, Back twice.

## The 2-minute demo (click → say)
1. Long-press **Connected** → **Higher-risk example** → "His answers go through the team gateway to my C3 service."
2. Result → "F1: High band, health score 58, provisional, referral note."
3. **Why this score** → "F2: SHAP and LIME agree on 4 of 5 factors; contributions, not causes."
4. **What you can do** → "Templates for things he can change; never his medicines."
5. Close with evidence → "0.78 / 0.85 ROC-AUC on 1,058 unseen people, 85 server + 43 Flutter + 68/70 browser tests, saved in PostgreSQL.
   Ethics submitted 21 September, not approved, so demo data only."

## If something fails
| Problem | Do this |
|---|---|
| App: **Not connected** | `.\server\services\c3_risk_xai\scripts\demo.ps1 -Research` → **Check again** |
| "Port already in use" | `.\server\services\c3_risk_xai\scripts\demo.ps1 -Action stop`, then start again |
| Emulator offline / frozen | Close it; use the phone window (`demo_phone.ps1`) |
| Disk full | Close the emulator; empty the Recycle Bin; never build while the emulator runs |
| Wi-Fi down | Nothing needed: everything runs on this laptop (127.0.0.1) |
| Everything fails | Play the backup video; show `http://127.0.0.1:8003/docs` |

## Backup video
Not recorded yet. Record it now: click the app window, **Win + Alt + R** to start and stop.
It is saved in `C:\Users\ALFARES\Videos\Captures`. Follow the click order above.

## Three answers to know by heart
1. **Label:** "The model learned 'diagnosed diabetes' from public Bangladesh data, so it gives an
   estimated risk profile, not a prediction of future diabetes. I asked my supervisors how to word it."
2. **No real patient data:** "Ethics was submitted on 21 September and is not approved; KDU could not
   share data. So I use public South Asian data and demo examples only."
3. **Synthetic / provisional:** "Synthetic data is only a pipeline check, never evidence. The health
   score weights are provisional until a clinician reviews them."

## After
`.\server\services\c3_risk_xai\scripts\demo_phone.ps1 -Action stop`
