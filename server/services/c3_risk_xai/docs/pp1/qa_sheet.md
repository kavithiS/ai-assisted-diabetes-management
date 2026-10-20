# Q&A sheet (short, honest answers + where the evidence is)

## The five Lecture 9 questions

**1. What exactly did you build?**
C3: a FastAPI service with a calibrated risk model, SHAP and LIME explanations, a provisional
Diabetic Health Score, template recommendations and a PostgreSQL `c3` schema, plus all Module 3
Flutter screens. *Evidence:* `server/services/c3_risk_xai/`, `client/mobile_app/lib/features/risk_profile/`.

**2. Which requirement does it address?**
TAF tasks 1-4 and proposal FR6-FR16, NFR4, NFR7, NFR11, NFR12. Task 5 (expert review, user study)
waits for ethics approval. *Evidence:* `docs/pp1/2_slides.md`, `docs/requirements.md`.

**3. How does it connect to the rest?**
Flutter app → team gateway (`/api/v1/risk/*`) → C3 → model → PostgreSQL. C1 nutrition and C2
forecast join in PP2 through the contract. *Evidence:* `docs/contract_proposal.md`, live demo.

**4. What testing and feedback evidence?**
85 server tests, 37 Flutter tests, presets checked against Python through the gateway, latency
measured (median 2.15 s). Supervisor feedback: Flutter required (done). No patient feedback yet:
ethics not approved. *Evidence:* `tests/`, `client/mobile_app/test/`, `docs/test_plan.md`.

**5. What proves you built it?**
Small regular commits on `c3_lochana`, the AI-use log, and I can walk through any file.
*Evidence:* GitHub history, `docs/ai_usage_log.md`, `docs/pp1/ai_use_log.md`.

## Hard questions

**What does the label mean, when your users already have diabetes?**
The model was trained on "diagnosed diabetes yes/no" (DiaBD, Bangladesh), so the output is an
estimated risk profile, not a prediction of future onset. I have asked my supervisors how to
word it. *Evidence:* `docs/pp1/supervisor_email.md`.

**Why South Asian (Bangladesh) data?**
No open Sri Lankan individual-level dataset exists; Bangladesh is the closest open population.
Sri Lankan questionnaire data comes after ethics approval. *Evidence:* `docs/data_README.md`.

**Why synthetic data?**
Only to test the pipeline for the extra TAF factors. It is never used as evidence, and every
reported number is on real people. *Evidence:* `config/synthetic_assumptions.yaml`.

**How did you avoid label leakage?**
Glucose is optional and reported separately (with/without). Kidney, liver and diabetes medicine
are never model inputs because they follow from having diabetes. *Evidence:* `config.yaml`, `ml/predict.py`.

**Is it calibrated?**
Yes: Platt scaling on cross-validated scores. Brier score improved from 0.068 to 0.051 (with
glucose). Band cut-offs come from training data, not the test set. *Evidence:* `docs/figures/calibration.png`.

**Why do SHAP and LIME sometimes disagree?**
They are different methods; the app reports the agreement (80% median) and shows a warning when it
is weak, instead of hiding it. *Evidence:* `explanation_quality.json`, the AI Explanation screen.

**Why don't lifestyle answers change the risk band?**
There is no real training data for them yet, so they feed only the DHS and recommendations. A test
proves the band does not change. *Evidence:* `tests/test_dhs.py`.

**Why are the DHS weights provisional?**
They are prototype values; a clinician must review them. The app labels the score "provisional".
*Evidence:* `config/dhs.yaml`.

**Ethics status?**
Not approved yet, so I use demo data only and no patient data is collected.

**What is not done yet?**
Real lifestyle data and a v2 model, clinician review, C1/C2 connection, load test, login and HTTPS
(team level), user study. All planned for PP2 (`docs/pp1/pp2_plan.md`).
