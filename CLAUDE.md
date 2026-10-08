# CLAUDE.md — shared rules for every member's AI assistant

DiaCare AI (J26-IT-352): Personalized AI Diabetes Care System for Sri Lankan Patients.
Source of truth, in priority order: the official TAF, then team and supervisor decisions in
`docs/SETUP_PROMPT.md` and `docs/adr/`.

## Rules

- This is a research prototype. Use "estimated" and "prediction", never "diagnosis". Make no
  clinical-validation claims.
- Never invent data, results, metrics, citations or participants. Write `[INFORMATION REQUIRED]`
  instead.
- Work only inside your own component folder. Changes to `contracts/`, `server/shared/`, the
  gateway or the client need a PR reviewed by the affected owner.
- Never show raw model confidence values in patient-facing UI.
  - **C3 note:** Risk % output includes a risk percentage. Should patients see only the risk band
    (low/medium/high) and DHS, or the % as well? Flag this with supervisors.
- No primary data from patients may be collected before ethical clearance.
- Follow the tech stack in `docs/SETUP_PROMPT.md` section 3. Ask before adding a new framework.
  - **C3 note:** Can Streamlit be used for PP1 demo only?
- Follow the workflow: understand → inspect → implement → lint → test → report.

## Commands

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy server
uv run pytest
cd client/mobile_app && flutter analyze && flutter test
```
