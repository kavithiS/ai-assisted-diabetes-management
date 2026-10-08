## Summary

<!-- What does this PR change, and why? -->

## Component

- [ ] C1 Food Recognition & Nutritional Analysis
- [ ] C2 Glycemic Prediction & Risk Forecasting
- [ ] C3 Multi-Factor Diabetic Risk Profiling & XAI
- [ ] C4 Mobile Platform & Foot Monitoring
- [ ] Shared (`contracts/`, `server/shared/`, gateway, client, infra, CI, docs)

## Checks

- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] `uv run mypy server` passes
- [ ] `uv run pytest` passes
- [ ] `flutter analyze` and `flutter test` pass (if `client/` changed)

## Shared areas

- [ ] This PR does not touch `contracts/`, `server/shared/`, the gateway or the client, **or** every affected owner is requested as a reviewer
- [ ] Any contract change updates `contracts/` and its version

## Research integrity

- [ ] No clinical diagnosis or validation claims ("estimated" / "prediction" wording only)
- [ ] No invented data, results, metrics, citations or participants
- [ ] No primary patient data collected without ethical clearance
- [ ] Any new framework or dataset decision is recorded in an ADR (`docs/adr/`)
