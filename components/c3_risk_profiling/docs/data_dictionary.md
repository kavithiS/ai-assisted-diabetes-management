# Data dictionary - South Asian dataset (PP1)

Built by `src/south_asia_dataset.py` from two Bangladesh datasets (CC BY 4.0):
**DiaBD** (Mendeley m8cgwxs9s6) for training and testing, and **Narsingdi hospital**
(Mendeley rn9m3zb7nt) as a second site. Missingness per site is in
`outputs/reports/south_asia_schema.csv`.

| # | Field | Type | Unit / values | DiaBD source | Narsingdi source | Preprocessing | Schema factor |
|---|---|---|---|---|---|---|---|
| 1 | target | binary | 0 not diabetic, 1 diabetic | diabetic (Yes/No) | Type-2 Diabetic | none | TARGET |
| 2 | age | continuous | years | age | Age | valid 18-100 | 1. Demographic |
| 3 | sex_male | binary | 0 female, 1 male | gender | not recorded | none | 1. Demographic |
| 4 | bmi | continuous | kg/m² | **recomputed** from weight / height² | BMI | outside 12-70 set to missing | 2. Anthropometric |
| 5 | systolic_bp | continuous | mmHg | systolic_bp | BP(Systolic) | outside 70-260 set to missing | 7. Clinical |
| 6 | diastolic_bp | continuous | mmHg | diastolic_bp | BP(Diastolic) | outside 40-150 set to missing | 7. Clinical |
| 7 | pulse_rate | continuous | beats/min | pulse_rate | not recorded | outside 35-200 set to missing | 7. Clinical |
| 8 | glucose_mmol | continuous | mmol/L | glucose | Glucose ÷ 18 (mg/dL) | outside 1.5-40 set to missing; optional input | 7. Clinical |
| 9 | family_history_diabetes | binary | 0 / 1 | family_diabetes | DiabetesPedigreeFunction > 0 (assumed count of relatives) | none | 5. Family history |
| 10 | family_history_hypertension | binary | 0 / 1 | family_hypertension | not recorded | none | 5. Family history |
| 11 | hypertensive | binary | 0 / 1 | hypertensive | not recorded | none | 5. Medical history |
| 12 | cardiovascular_disease | binary | 0 / 1 | cardiovascular_disease | not recorded | none | 5. Medical history |
| 13 | stroke | binary | 0 / 1 | stroke | not recorded | none | 5. Medical history |

## Data-quality findings

- Narsingdi: 1,065 rows but only **496 unique**. The 569 exact duplicates were removed.
- The Pabna file (vxnyysk9vc) is entirely contained in the Narsingdi file, so it was not used.
- DiaBD: a few impossible values (BMI 574, height 0.36 m, pulse 5). These were set to missing, not trusted.
- The DiaBD label is a diagnosis, not a glucose cut-off: 246 people with glucose ≥ 11.1 are
  labelled "No". So glucose is a legitimate optional feature, and both models are reported.

## Coverage against the eight-factor schema in the proposal

| Schema factor | Coverage | Gap to close in PP2 |
|---|---|---|
| 1. Demographic | Good | Age and sex only |
| 2. Anthropometric | Partial | BMI only; no waist circumference or weight change |
| 3. Lifestyle / activity | **Absent** | Sri Lankan questionnaire (after ethics approval) |
| 4. Diet / nutrition | **Absent** | Component 1 supplies nutrition data |
| 5. Medical / family history | Good | Family history of diabetes and BP, hypertension, CVD, stroke |
| 6. Medication / behaviour | **Absent** | Questionnaire: medication, adherence, smoking, alcohol |
| 7. Clinical / lab | Partial | BP, pulse, glucose; no HbA1c, lipids, kidney or liver markers |
| 8. Glycemic forecast | Absent | Component 2 supplies this |

No open South Asian dataset contains groups 3, 4 or 6. State this openly at PP1.
