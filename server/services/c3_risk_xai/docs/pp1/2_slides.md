# C3 individual part: exactly 2 slides

Rajapaksha R.M.L.I · IT23315846 · J26-IT-352 · Multi-Factor Diabetic Risk Profiling & Explainable AI

---

## Slide A: What I built and why

**Sub-problem.** Diabetic patients need one clear, explained picture of many risk factors
(blood pressure, weight, history, activity, smoking, medication, cholesterol, kidney/liver),
not food alone, and not a black-box score.

**User requirements addressed (proposal IDs)**
- F1 prediction: estimated risk band, calibrated (FR6), no band without critical data (FR12)
- F2 explanation: SHAP (FR7), LIME + fit (FR8), SHAP-LIME agreement (FR9), plain-language summary (NFR7)
- Diabetic Health Score 0-100, adaptive (FR10), template recommendations, never medicine changes (FR11, NFR11)
- History, model + schema versions, deletion, audit log (FR13, FR15, FR16, NFR12); pseudonymous ID only (NFR4)

**Architecture.** Flutter app → API gateway (FastAPI, :8000) → C3 service (FastAPI, :8003)
→ ML model + SHAP/LIME + DHS → PostgreSQL schema `c3`

**My contribution.** Data pipeline on public South Asian data, 3-model comparison, calibration,
SHAP/LIME, DHS, recommendation rules, C3 API + database, all Module 3 Flutter screens, tests.

---

## Slide B: Evidence and next steps

**Results (public DiaBD data, real held-out test set of 1,058 people never used in training)**
- ROC-AUC **0.78** without glucose (95% CI 0.72–0.84) · **0.85** with glucose (95% CI 0.80–0.90)
- SHAP-LIME top-5 agreement **80%** (target 60%)
- Speed: server median **2.22 s** per full assessment (target 2 s, missed slightly); in the browser, click to result
  **1.6–2.1 s** (median of 5, four runs): about 2 s, reported honestly

**Testing.** **85** server tests (77 for C3), **43** Flutter tests (42 for C3), **68 of 70** Playwright browser
tests at phone and desktop size (1 test-server timeout under load, 1 skipped by design), lint and strict typing clean;
the three demo presets match the Python model exactly through the gateway.

**Feedback and data access.** Supervisors: demo must be in Flutter (done). National Hospital
(Aug: discussion, proposal + permission letters) and KDU (Sep: could not share that much data).
Ethics application submitted 21/09/2026, **not approved yet**: demo data only, no patient data.

**Next (PP2).** Real Sri Lankan lifestyle data after ethics approval · clinician review of DHS
weights and recommendation wording · connect C1 nutrition and C2 forecast.
