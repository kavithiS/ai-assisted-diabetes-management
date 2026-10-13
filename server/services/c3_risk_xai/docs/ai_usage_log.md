# AI usage log - Component 3

University policy requires AI assistance to be recorded. Accountability stays
with you: **if you cannot explain, verify and defend it, do not present it.**

Add a row every time you use an AI tool. Fill it in as you go, not afterwards.

| Date | Tool | Purpose | Prompt summary | What I accepted | What I rejected | How I verified it | What I modified | Where it ended up |
|---|---|---|---|---|---|---|---|---|
| 2026-10-10 | Claude (Claude Code) | Git help | How to bring main into my branch and fix a merge conflict | Git commands; kept main's README in the conflict | - | Checked git status and git log myself | None | c3_lochana branch |
| 2026-10-10 | Claude (Claude Code) | Fix CI errors | Why CI failed and how to fix lint errors | Import order, formatting and 3 small code fixes | - | Ran ruff and pytest; CI turned green on GitHub | None | src/, app/, tests/ |
| 2026-10-10 | Claude (Claude Code) | Review my documents | Compare my proposal and PP1 rubric with my code | List of 12 gaps between proposal and code | - | Read the gap list against my proposal myself | None | My PP1 plan |
| 2026-10-10 | Claude (Claude Code) | Find datasets | Check my dataset links and find South Asian data | DiaBD and Narsingdi (Bangladesh); 5 datasets rejected with reasons | US data (NHANES) - I decided to use South Asian data only | Opened the Mendeley pages and CSV files myself | My decision: South Asian data only | data/README.md, src/external_data.py, src/south_asia_dataset.py |
| 2026-10-10 | Claude (Claude Code) | Synthetic data | Mix real and synthetic data (supervisor approved) | Gaussian copula generator; test set kept 100% real | - | Checked 0 copies of real people and results in the report | None | src/synthetic.py |
| 2026-10-10 | Claude (Claude Code) | Build and train component | Rebuild the full component on South Asian data | Training, calibration, risk bands, predict, explain, app, evidence figures | - | Ran every script, 17 tests passed, used the app myself | None | src/, app/, outputs/ |
| 2026-10-10 | Claude (Claude Code) | Documentation | Update docs and write a demo script | README, data dictionary, architecture, requirements, risk register, demo script | - | Read each document and checked numbers against outputs/reports | None | docs/ |
| 2026-10-11 | Claude (Claude Code) | Test plan help | How to fill the test plan | Format for the Actual and Status columns | - | Ran pytest and the app myself and took screenshots | I filled in the results | docs/test_plan.md |

## Before PP1 - self-check

Go through every file in `src/` and `app/` and confirm you can answer:

- [ ] What does this file do, in one sentence?
- [ ] Why does each function exist?
- [ ] Why this library rather than an alternative?
- [ ] What breaks if I delete this line?
- [ ] What would I change if the dataset changed?

Any line that fails this check should be rewritten by you or removed.
