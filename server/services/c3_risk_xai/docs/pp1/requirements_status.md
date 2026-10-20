# Requirements status at PP1 (proposal FR1-FR16, NFR1-NFR12)

Checked 2026-10-20. DONE = implemented and tested; PARTIAL = part is done; PLANNED = planned for PP2.
Test files are under `server/services/c3_risk_xai/tests/` and `client/mobile_app/test/features/risk_profile/`.

## Functional requirements

| ID | Requirement (short) | Status | Proof |
|---|---|---|---|
| FR1 | Receive versioned questionnaire data; invalid schema gives a documented error | DONE | `schema_version` 0.2 stored in `c3.risk_profiles`; 422 / `invalid_input` (`test_api.py`, `test_storage.py`) |
| FR2 | Receive C1 nutrition features | PLANNED for PP2 | Waits for the C1 contract |
| FR3 | Receive C2 forecast features | PLANNED for PP2 | Waits for the C2 contract; DHS glycemic part is empty |
| FR4 | Range/unit validation before storage | DONE | `ml/predict.py` validation; `test_pipeline.py` (impossible values) |
| FR5 | Complete / stale / missing / conflicting statuses | PARTIAL | Missing (`insufficient_data`) and imputed fields done; stale and conflicting PLANNED for PP2 |
| FR6 | Calibrated probability and category, model version, timestamp | DONE | Platt calibration (`calibration.png`); band + `model_version` in the response; time stored with the record |
| FR7 | SHAP global and local explanations | DONE | `shap_summary_*.png` (global); AI Explanation screen (local); `test_pipeline.py` |
| FR8 | LIME local explanation with fidelity and seed/config | PARTIAL | Factors, direction, fit R² returned; seed is in `config.yaml`, not yet in the response |
| FR9 | SHAP-LIME agreement status | DONE | `agreement` in every result; 80% median overlap (`explanation_quality.json`) |
| FR10 | Calculate and update the DHS | DONE (provisional weights) | `ml/dhs.py`, `config/dhs.yaml`; reproducible + adaptive (`test_dhs.py`) |
| FR11 | Reviewed recommendations from modifiable factors, citing triggers | PARTIAL | Template rule base with triggers (`ml/recommend.py`, `test_dhs.py`); clinician review PLANNED for PP2 |
| FR12 | Insufficient-evidence status | DONE | Missing BMI preset → no band (`test_pipeline.py`, live demo) |
| FR13 | Assessment history | DONE | `GET /v1/risk/history`, Past results screen (`test_storage.py`) |
| FR14 | FastAPI with OpenAPI and endpoint tests | DONE | `http://127.0.0.1:8003/docs`; `test_api.py` |
| FR15 | Model and schema versions on every record | DONE | `c3.assessments` columns (`test_storage.py`) |
| FR16 | Correction or deletion, logged | PARTIAL | Deletion + audit entry DONE (`test_storage.py`); correction PLANNED for PP2 |

## Non-functional requirements

| ID | Requirement (short) | Status | Proof |
|---|---|---|---|
| NFR1 | Median ≤ 2 s, p95 ≤ 5 s | **MISSED (median)** | Median **2.22 s**, max 2.58 s over 10 warm requests (`data/c3/outputs/reports/latency_pp1.json`); load test PLANNED for PP2 |
| NFR2 | ≥ 99% successful requests in integration testing | PARTIAL | All test and preset requests succeeded; formal test PLANNED for PP2 |
| NFR3 | Authentication, authorisation, transport encryption | PLANNED for PP2 | Team-level (gateway); PR notes written |
| NFR4 | No direct identifier in model features | DONE | Random device pseudonym only; names rejected (`test_storage.py`) |
| NFR5 | SUS ≥ 68 | PLANNED for PP2 | Needs ethics approval (submitted 21/09/2026, not approved) |
| NFR6 | WCAG 2.2 AA principles | PARTIAL | Labels + icons (not colour only), semantic labels, 48 dp buttons; no formal audit yet |
| NFR7 | Direction, rank, data date, quality status per assessment | DONE | AI Explanation screen; "Last assessed" date; quality warning |
| NFR8 | Automated tests, documented API/schema versions | DONE | 85 server (77 C3) + 37 Flutter tests; `docs/contract_proposal.md` |
| NFR9 | Load test at prototype concurrency | PLANNED for PP2 | |
| NFR10 | Dataset/code version, seed, parameters recorded | PARTIAL | Seeds and settings in `config.yaml`, pinned packages, model version in each bundle; raw-data checksum manifest to regenerate in PP2 |
| NFR11 | No automatic medication changes; reviewed referral wording for High | PARTIAL | No-medicine-change test DONE (`test_dhs.py`); referral shown for High; clinician review of wording PLANNED |
| NFR12 | Each assessment records pseudonym, versions, result, time | DONE | `c3.assessments` + `c3.audit_log` (actions and counts only) |
