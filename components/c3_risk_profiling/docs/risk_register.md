# Risk register - Component 3

Levels: probability x impact. Update the status column weekly; an unchanged
register is a register nobody is using.

| ID | Risk | Prob. | Impact | Level | Mitigation | Contingency | Status |
|---|---|---|---|---|---|---|---|
| R1 | Sri Lankan datasets (STEPS, SLHAS, SLDCS) not granted in time; no open Sri Lankan data exists | High | High | **High** | Requests sent early with supervisor CC; South Asian (Bangladesh) data already working | Present Bangladesh results, never as Sri Lankan; Sri Lankan validation in PP2 | Open |
| R2 | Class imbalance (6.5% diabetic in DiaBD) harms recall and makes accuracy misleading | High | Medium | **High** | class_weight="balanced" / scale_pos_weight; model chosen by PR-AUC; calibration; data-driven bands | Report PR-AUC, recall and the band table, never accuracy alone | Mitigated |
| R3 | Data leakage inflates results | Medium | High | **High** | Scaling inside a Pipeline; split before any fitting; no outcome-derived features | Re-run with a clean split and report both | Mitigated |
| R4 | Schema groups missing from all open South Asian data (lifestyle, diet, medication, labs) | High | Medium | **Medium** | Coverage table in the data dictionary; C1/C2 and the Sri Lankan questionnaire fill them in PP2 | State the gap openly at PP1 | Open |
| R5 | C1 / C2 outputs unavailable before PP1 | High | Low | **Medium** | Component works standalone; API contract agreed with placeholders | Demonstrate C3 alone; show the contract as evidence of design | Mitigated |
| R6 | SHAP and LIME disagree on top factors | Medium | Medium | **Medium** | Agreement ratio computed and reported in the output | Present disagreement as a research finding with the stability analysis | Mitigated |
| R7 | Model mistaken for a diagnostic tool | Medium | High | **High** | Disclaimer in the UI, the API response and every slide | Add explicit scope warnings; emphasise clinician review | Mitigated |
| R8 | Ethics approval delayed, blocking the user study | Medium | High | **High** | Application prepared early with the supervisor | Expert review only for PP1; user study in PP2 | Open |
| R9 | Live demo fails during the presentation | Medium | High | **High** | Rehearse; pre-warm the model; recorded backup video | Switch to the recorded demo plus saved screenshots | Mitigated |
| R10 | Poor model performance on an unseen population | High | Medium | **High** | Second-site check run: DiaBD model drops to ROC-AUC ~0.55 on Narsingdi without glucose | Report the transfer gap; recalibrate on Sri Lankan data in PP2 | Open - evidence collected |
| R11 | Timeline slips against the five-week plan | Medium | Medium | **Medium** | Weekly Planner review; scope frozen in Week 1 | Drop "should have" items; protect the two key functions | Open |
| R12 | Cannot explain AI-assisted code at Q&A | Low | High | **High** | AI usage log; walk through every file before PP1 | Remove any code you cannot defend | Open |
| R13 | Poor-quality public data (569 duplicate rows in Narsingdi, impossible values in DiaBD) | High | Medium | **Medium** | Duplicates removed; plausibility ranges set values to missing; findings documented | Exclude a source if quality cannot be verified | Mitigated |
| R14 | Synthetic data mistaken for real evidence | Medium | High | **High** | Generator fitted on training rows only; test set 100% real; real-only results reported alongside | Report synthetic results only as augmentation experiments | Mitigated |
| R15 | Risk-band cut-offs not clinically validated | High | Medium | **Medium** | Cut-offs chosen from training data (90% sensitivity / 90% specificity), not equal thirds | Clinician review of cut-offs in PP2; labelled "pending clinical review" | Open |
