# C3 browser checks (Playwright)

End-to-end checks of the C3 Flutter web build in the installed Google Chrome (no browser
download), at phone size (412x915) and desktop size (1280x800). The suite starts its own
throwaway servers (C3 on 8013, gateway on 8010, the web build on 5192), never the demo
ports 8000/8003, uses throwaway device IDs (starting `e2e0`) and deletes their rows at the end.

## Run (PowerShell, from the repo root)

```powershell
# 1. Build the C3 web app for the test gateway (about 2 min).
cd client\mobile_app
flutter build web -t lib/features/risk_profile/c3_standalone.dart --dart-define=API_BASE_URL=http://127.0.0.1:8010 -o build/web_e2e
git checkout -- analysis_options.yaml   # flutter adds an analyzer block; do not commit it
cd ..\..

# 2. Install once (no browser download), then run.
cd server\services\c3_risk_xai\e2e
$env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = "1"; npm ci
npx playwright test                     # both sizes, about 25 min
npx playwright test --project=phone     # phone size only
```

Results: `test-results/results.json`; a screenshot and trace for every failure in
`test-results/`; time to first result in `results/latency_e2e.json`.

The screen-reader (semantics) tree is switched on only inside the test browser, the way
a screen reader does it; nothing in the app changes for the tests.

`npm run shots` takes the PP1 screenshots (needs the screenshot harness build; see
`screenshots.mjs`).

Defects found and fixed: `bug_report.md`.
