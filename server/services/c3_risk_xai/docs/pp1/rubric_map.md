# PP1 rubric map (C3)

| Criterion (weight) | My evidence | Where the panel sees it |
|---|---|---|
| Proven gap / proof of concept (10%) | Working end-to-end flow: app → gateway → C3 → model → database | Live demo; `docs/pp1/2_slides.md` slide A |
| Knowledge pillars + technologies (25%) | ML (logistic regression / random forest / XGBoost), calibration, SHAP, LIME, FastAPI, PostgreSQL + SQLAlchemy + Alembic, Flutter | Slide A; code in `src/c3_risk_xai/ml`, `db/`, Flutter feature |
| Design (part of 40%) | Layered service (api → services → ml / db), contract proposal, architecture test | `docs/architecture.md`, `docs/contract_proposal.md`, `tests/test_architecture.py` |
| Completion (part of 40%) | F1 + F2 working, DHS, recommendations, history, deletion, 7 Module 3 screens | Live demo |
| Standards / best practice (part of 40%) | ruff, mypy --strict, 85 server (77 C3) + 37 Flutter automated tests, Conventional Commits, CI | GitHub branch `c3_lochana`; `tests/` |
| User / functional requirements (part of 40%) | FR6-FR16, NFR4/7/11/12 mapped to features | Slide A; `docs/pp1/requirements_status.md` |
| Risk mitigation (part of 40%) | Risk register with owners; demo fallbacks (phone window, video) | `docs/pp1/risk_register.md`, `docs/pp1/demo_checklist.md` |
| Communication (15%) | 2 slides + 2-minute scripted story; Q&A sheet | `docs/pp1/script_2min.md`, `docs/pp1/qa_sheet.md` |
| Commercialisation (10%) | Persona, who pays, cost recovery | `docs/pp1/commercialisation.md` |
