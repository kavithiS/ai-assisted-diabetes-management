# C3 browser QA: bug report

Found with the Playwright suite in this folder (Flutter web release build of
`c3_standalone.dart`, installed Chrome, 412x915 and 1280x800), on throwaway servers
(C3 8013, gateway 8010) with throwaway device IDs. Every fix is in
`client/mobile_app/lib/features/risk_profile/**` and is covered by the test named under it.

Severity: Major = a user can lose data, get duplicated data or get stuck; Minor = works,
but confusing or harder for screen-reader users.

| ID | Severity | Status |
|----|----------|--------|
| B1 | Major | FIXED |
| B2 | Minor | FIXED |
| B3 | Minor | FIXED |
| B4 | Major | FIXED |
| B5 | Major | FIXED |
| B6 | Major | FIXED |
| B7 | Minor | FIXED |

## B1. "Open connection settings" was not a button

- **Steps:** Home -> tap "Open connection settings" at the bottom.
- **Expected:** Settings opens.
- **Actual:** Nothing happened. It was plain text; Settings only opened on a long-press of
  the "Connected" chip, which nobody would guess.
- **Fix:** `risk_profile_screen.dart`: a real text button (48 dp target) that opens Settings.
- **Proof:** `tests/01-home-presets.spec.mjs` (home), `tests/04-history-settings.spec.mjs`
  (all Settings tests open Settings through it).

## B2. Connection chip: wrong screen-reader label and role

- **Steps:** Home with a screen reader (semantics tree).
- **Expected:** One button "Connected. Tap to check again."
- **Actual:** The heading was merged into the button label ("Your health score Connected
  Tap to check again.") and the chip was also announced as a checkbox.
- **Fix:** `widgets/risk_widgets.dart`: the chip is its own semantics container, with tap
  and long-press actions, and the inner chip's semantics are hidden.
- **Proof:** `tests/01-home-presets.spec.mjs` ("Check again" test presses it by that label).

## B3. Saved past checks could not be opened

- **Steps:** Do two checks -> Past checks -> tap a saved check.
- **Expected:** The saved check opens.
- **Actual:** Nothing happened (no tap action).
- **Fix:** `risk_history_screen.dart`: tapping opens a short summary (band and date). The
  server keeps only the band, date and status of a saved check (no answers, by design), so
  the full result cannot be rebuilt from it; opening the full past result is planned for PP2.
- **Proof:** `tests/04-history-settings.spec.mjs` ("lists server results and opens an old one").

## B4. Out-of-range answer higher up the form: no visible feedback

- **Steps:** Health check -> Weight 500 -> scroll down -> "Save & recalculate".
- **Expected:** The problem is shown.
- **Actual:** Nothing visible happened: the message was off screen at the top. The form was a
  lazy list, so a field scrolled far away could also be skipped by the check.
- **Fix:** `risk_questionnaire_screen.dart`: every field stays built (so every field is
  checked); on Save the first problem scrolls into view and a message says
  "Please check the answers marked in red."
- **Proof:** `tests/02-health-check-form.spec.mjs` (all invalid-value tests) and the Flutter
  test "an out-of-range answer far up the form is shown and explained on Save".

## B5. A fast double tap sent and saved the same check twice

- **Steps:** Home -> double-click "Higher-risk example" (or double-tap on a phone).
- **Expected:** One check, one saved result.
- **Actual:** Two requests and two saved results (measured: requests=2, saved=2).
- **Fix:** `c3_theme.dart` `c3Push`: a screen opens only if the current screen is still on
  top, so the second tap is ignored. Used by every button that opens a screen.
- **Proof:** `tests/05-edge-cases.spec.mjs` ("double-click on an example saves only one
  result") and the Flutter test "a fast double tap on an example sends and saves the check
  only once".

## B6. First check without a glucose value after a server start failed

- **Steps:** Start C3 without the demo warm-up -> health check with no glucose value.
- **Expected:** A result (the first one may be slower).
- **Actual:** "We couldn't finish this check. Could not connect." The server answered after
  about 17 s (one-time start-up of the explanation step for that path; measured 16.9 s, then
  0.28 s for the next calls), but the app gave up after 10 s.
- **Fix:** `data/risk_api.dart`: an assessment may take up to 30 s; status, history and
  delete keep 10 s. `demo.ps1` already sends a no-glucose warm-up, so the demo itself was
  not affected.
- **Proof:** `tests/02-health-check-form.spec.mjs` ("optional answers"), the Flutter test
  "an assessment may take up to 30 s (cold start); other calls keep 10 s".

## B7. "Test connection" result not given to screen readers

- **Steps:** Settings -> Test connection (screen reader on).
- **Expected:** "Connection successful." (or the failure) is announced.
- **Actual:** The text appeared on screen but was missing from the screen-reader tree.
- **Fix:** `risk_settings_screen.dart`: the result is a live region with its own label.
- **Proof:** `tests/04-history-settings.spec.mjs` ("Settings: invalid URL rejected, test
  connection works, saved URL survives a reload").

## Checked and found working (no bug)

- One normal click sends exactly one request (measured).
- "Update health information" opens the form with the previous answers (the web input box
  shows no value to scripts until focused; the screenshot and the BMI line confirm it).
- "Try a change": every option gives the score the server computes for it (Higher-risk
  answers: activity low/moderate/high = 58/63/68; with high activity, cholesterol
  normal/high = 71/65), and nothing is saved.
- A gateway address typed with a trailing "/" works.
- Server 500/503, a dropped connection and a stopped database all give a friendly message
  with Retry or an offline note; no technical text reaches the screen.

## Final run (2026-10-21)

| Suite | Tests | Passed | Failed | Skipped |
|-------|-------|--------|--------|---------|
| Playwright, phone 412x915 + desktop 1280x800 | 70 | 68 | 1 | 1 |

- Skipped: the timing test runs at phone size only (by design).
- Failed: "Past checks: database stopped..." at desktop size only: the test server took
  more than 2 minutes to restart while the laptop was heavily loaded (that run took 46 min
  instead of 14). The same test passed at phone size in that run and in a separate rerun.
  Not an app defect; status OPEN (test harness, slow restart under load).

Time to first result (click "Higher-risk example" -> band on screen, median of 5): four full
runs on the fixed build gave 1.62 s, 1.81 s, 1.83 s and 2.09 s. Around the 2 s target
(NFR1): under it in 3 of 4 runs, just over it in the busiest run. Latest raw runs in
`results/latency_e2e.json`.

Bugs: 7 found, 7 fixed, 0 open.
