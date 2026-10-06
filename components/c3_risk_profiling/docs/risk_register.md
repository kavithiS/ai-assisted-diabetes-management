# Risk register - Component 3

Levels: probability x impact. Update the status column weekly; an unchanged
register is a register nobody is using.

| ID | Risk | Prob. | Impact | Level | Mitigation | Contingency | Status |
|---|---|---|---|---|---|---|---|
| R1 | Sri Lankan datasets (STEPS, SLHAS) not granted in time | High | High | **High** | Requests sent early with supervisor CC; BRFSS already working | Present BRFSS results and state Sri Lankan validation as PP2 scope | Open |
| R2 | Severe class imbalance (prediabetes ~1.8%) harms minority recall | High | Medium | **High** | Binary target for PP1; class_weight="balanced"; report PR-AUC not accuracy | Report per-class recall and discuss the limitation openly | Mitigated |
| R3 | Data leakage inflates results | Medium | High | **High** | Scaling inside a Pipeline; split before any fitting; no outcome-derived features | Re-run with a clean split and report both | Mitigated |
| R4 | Key variables missing (family history, HbA1c, medications) | High | Medium | **Medium** | Documented in the data dictionary; acknowledged in the proposal | Obtain NHANES, which carries these for the same participants | Open |
| R5 | C1 / C2 outputs unavailable before PP1 | High | Low | **Medium** | Component works standalone; API contract agreed with placeholders | Demonstrate C3 alone; show the contract as evidence of design | Mitigated |
| R6 | SHAP and LIME disagree on top factors | Medium | Medium | **Medium** | Agreement ratio computed and reported in the output | Present disagreement as a research finding with the stability analysis | Mitigated |
| R7 | Model mistaken for a diagnostic tool | Medium | High | **High** | Disclaimer in the UI, the API response and every slide | Add explicit scope warnings; emphasise clinician review | Mitigated |
| R8 | Ethics approval delayed, blocking the user study | Medium | High | **High** | Application prepared early with the supervisor | Expert review only for PP1; user study in PP2 | Open |
| R9 | Live demo fails during the presentation | Medium | High | **High** | Rehearse; pre-warm the model; recorded backup video | Switch to the recorded demo plus saved screenshots | Mitigated |
| R10 | Poor model performance on an unseen population | Medium | Medium | **Medium** | Compare three models; report calibration (Brier) | Report honestly and plan recalibration on local data | Open |
| R11 | Timeline slips against the five-week plan | Medium | Medium | **Medium** | Weekly Planner review; scope frozen in Week 1 | Drop "should have" items; protect the two key functions | Open |
| R12 | Cannot explain AI-assisted code at Q&A | Low | High | **High** | AI usage log; walk through every file before PP1 | Remove any code you cannot defend | Open |
