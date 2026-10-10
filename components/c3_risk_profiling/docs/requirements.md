# User and functional requirements - Component 3

## Users

| User | Needs from this component |
|---|---|
| Patient (primary) | A risk estimate they can understand, the reasons behind it, and clear limits on what it means |
| Clinician / dietitian | A transparent, reviewable risk assessment with contributing factors |
| Researcher / developer | A reproducible pipeline, versioned schema and documented data provenance |

## Functional requirements

| ID | Requirement | PP1 status |
|---|---|---|
| FR1 | The system shall accept a patient risk-factor record as structured input | Implemented |
| FR2 | The system shall reject impossible values and report any missing fields rather than silently defaulting them | Implemented |
| FR2a | The system shall return an insufficient-data status, with no risk band, when age, BMI or blood pressure is missing | Implemented |
| FR3 | The system shall preprocess inputs using the same transformations (training medians) applied during training | Implemented |
| FR4 | The system shall output a calibrated diabetes risk probability between 0 and 1 | Implemented |
| FR5 | The system shall map the probability to a Low / Moderate / High band using cut-offs chosen from training data | Implemented (cut-offs pending clinical review) |
| FR5a | The system shall use a glucose-aware model only when a glucose result is provided | Implemented |
| FR5b | The system shall add a referral note to every High-band result | Implemented |
| FR6 | The system shall generate SHAP contributions for an individual prediction | Implemented |
| FR7 | The system shall generate LIME local explanations, with local fit (R²), for the same prediction | Implemented |
| FR8 | The system shall report the agreement between SHAP and LIME and flag weak explanations | Implemented |
| FR9 | The system shall produce a plain-language explanation separating modifiable from non-modifiable factors | Implemented |
| FR10 | The system shall display a disclaimer stating the output is not a diagnosis | Implemented |
| FR11 | The system shall compute an adaptive Diabetic Health Score (0-100) | PP2 |
| FR12 | The system shall track DHS trends over time | PP2 |
| FR13 | The system shall consume nutrition features from Component 1 | PP2 |
| FR14 | The system shall consume glycemic-forecast features from Component 2 | PP2 |
| FR15 | The system shall expose results through a versioned REST API | PP2 |
| FR16 | The system shall map risk factors to clinician-reviewed recommendations | PP2 |

## Non-functional requirements

| Category | Requirement | PP1 evidence |
|---|---|---|
| Performance | Prediction returns in under 2 seconds; explanation under 10 seconds | Timed during the demo |
| Reliability | Invalid or incomplete input returns a handled response, never a crash | `tests/test_pipeline.py` |
| Explainability | Every prediction is accompanied by ranked contributing factors | Function 2 output |
| Safety | Every output carries a non-diagnostic disclaimer | UI, API response and slides |
| Privacy | No patient-level data is committed to the repository | `.gitignore` |
| Reproducibility | Fixed random seeds; config-driven settings; pinned dependency versions | `config.yaml`, `requirements.txt` |
| Usability | Non-technical users can read the explanation without ML knowledge | Plain-language field names |
| Maintainability | Modular `src/` package; no hard-coded paths or parameters | Repository structure |
