# Q&A sheet (short, honest answers + where the evidence is)

## The five Lecture 9 questions

**1. What exactly did you build?**
C3: a FastAPI service with a calibrated risk model, SHAP and LIME explanations, a provisional
Diabetic Health Score, template recommendations and a PostgreSQL `c3` schema, plus all Module 3
Flutter screens. *Evidence:* `server/services/c3_risk_xai/`, `client/mobile_app/lib/features/risk_profile/`.

**2. Which requirement does it address?**
TAF tasks 1-4 and proposal FR6-FR16, NFR4, NFR7, NFR11, NFR12. Task 5 (expert review, user study)
waits for ethics approval. *Evidence:* `docs/pp1/requirements_status.md`.

**3. How does it connect to the rest?**
Flutter app → team gateway (`/api/v1/risk/*`) → C3 → model → PostgreSQL. C1 nutrition and C2
forecast join in PP2 through the contract. *Evidence:* `docs/contract_proposal.md`, live demo.

**4. What testing and feedback evidence?**
85 server tests (77 for C3), 43 Flutter tests (42 for C3), 68 of 70 browser tests, presets checked against Python through the gateway,
latency measured (median 2.22 s). Feedback: supervisors required Flutter (done); hospital and KDU
meetings on data access. *Evidence:* `tests/`, `client/mobile_app/test/`, `data/c3/outputs/reports/latency_pp1.json`.

**5. What proves you built it?**
Small regular commits on `c3_lochana`, the AI-use log, and I can walk through any file.
*Evidence:* GitHub history, `docs/ai_usage_log.md`, `docs/pp1/ai_use_log.md`.

## Hard questions

**What does the label mean, when your users already have diabetes?**
The model was trained on "diagnosed diabetes yes/no" (DiaBD, Bangladesh), so the output is an
estimated risk profile, not a prediction of future onset. I have asked my supervisors how to
word it. *Evidence:* `docs/pp1/supervisor_email.md`.

**Why no real patient data yet?**
I visited the National Hospital twice in August (discussion, then proposal and permission letters)
and went back in September; the ethics application was submitted on 21/09/2026 and is not approved
yet. Until then I use demo data and public datasets only. *Evidence:* `docs/pp1/risk_register.md`.

**Why not KDU data?**
I spent three days at KDU in September to request data; they said they cannot share that much data.
So the plan is our own questionnaire after ethics approval.

**Why South Asian (Bangladesh) data?**
No open Sri Lankan individual-level dataset exists; DiaBD and Narsingdi (Bangladesh) are the
closest open populations. *Evidence:* `docs/data_README.md`.

**Why synthetic data?**
Only as a pipeline check for the extra TAF factors. It is NOT evidence; every reported number is on
real people. *Evidence:* `config/synthetic_assumptions.yaml`.

**How did you avoid label leakage?**
Glucose is optional and reported separately (with/without). Kidney, liver and diabetes medicine are
never model inputs because they follow from having diabetes. *Evidence:* `config.yaml`, `ml/predict.py`.

**Is it calibrated?**
Yes: Platt scaling on cross-validated scores. Brier score improved from 0.068 to 0.051 (with
glucose). Band cut-offs come from training data, not the test set. *Evidence:* `docs/figures/calibration.png`.

**Why do SHAP and LIME sometimes disagree?**
They are different methods; the app reports the agreement (80% median) and shows a warning when it
is weak, instead of hiding it. *Evidence:* the AI Explanation screen.

**Why don't lifestyle answers change the risk band?**
There is no real training data for them yet, so they feed only the DHS and recommendations. A test
proves the band does not change. *Evidence:* `tests/test_dhs.py`.

**Why are the DHS weights provisional? Why did the DHS change between two examples?**
They are prototype values a clinician must review; the app labels them "provisional". The DHS is
adaptive: on the same device it blends with the previous score. *Evidence:* `config/dhs.yaml`.

**Is it fast enough?**
Median 2.22 s per full assessment against a 2 s target, so slightly missed; a proper load test is
planned for PP2. *Evidence:* `latency_pp1.json`.

**What is not done yet?**
Real lifestyle data and a v2 model, clinician review, C1/C2 connection, load test, login and HTTPS
(team level), user study: all planned for PP2 (`docs/pp1/pp2_plan.md`).
