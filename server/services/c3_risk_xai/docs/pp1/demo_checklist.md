# Demo checklist (PowerShell, folder `C:\Users\ALFARES\Desktop\c3-risk-profiling`)

## Before the panel
1. Close other apps (the laptop runs the model, the gateway and the app together).
2. Backend + phone window, one command:
   `.\server\services\c3_risk_xai\scripts\demo_phone.ps1`
   Wait for `All good`. Keep the **C3** and **Gateway** windows open.
3. Emulator instead (optional, 1-3 min boot):
   `& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd C3_Demo -no-snapshot -gpu swiftshader_indirect -no-boot-anim`
   then open **DiaCare AI** on it.
4. In the app: **Risk Profile** tab → chip says **Connected** → **Warm up the model**.
5. Run **Higher-risk example** once (High, DHS 58), go back.

## During the demo
| Click | Say |
|---|---|
| Higher-risk example | "Answers go through the gateway to C3." |
| (result) | "F1: High band, DHS 58, provisional, referral note." |
| Understand my risk | "F2: SHAP and LIME, agree on 4 of 5, not medical causes." |
| View recommendations | "Templates for modifiable factors, never medicines." |
| Explore what-if (High activity → Estimate) | "The score changes; the band does not, the model doesn't use lifestyle yet." |
| Past results | "Saved in PostgreSQL with model and schema versions." |

## If something goes wrong
| Problem | Do this |
|---|---|
| App says **Not connected** | `.\server\services\c3_risk_xai\scripts\demo.ps1 -Research`, then **Check again** |
| "Port 8000 is already in use" | `.\server\services\c3_risk_xai\scripts\demo.ps1 -Action stop`, then start again |
| Emulator freezes or dies | Close it; use the phone window: `demo_phone.ps1` |
| First result is slow | **Warm up the model**, wait, tap the preset again |
| Everything fails | Play the backup video; show `http://127.0.0.1:8003/docs` and the code in `src/c3_risk_xai/` |

## Backup video
Click the app window, press **Win + Alt + R** to start/stop (saved in `Videos\Captures`).
Record the same click order as above.

## After
`.\server\services\c3_risk_xai\scripts\demo_phone.ps1 -Action stop`
