# Data folder

**Nothing in `raw/` or `processed/` is committed to Git.** See `.gitignore`.
Health data does not belong in a public repository, even when it is public-use.

## How to obtain the PP1 dataset

**CDC Diabetes Health Indicators (BRFSS 2015)** - 253,680 rows, 21 features,
3-class target (0 = no diabetes, 1 = prediabetes, 2 = diabetes).

Official source: <https://archive.ics.uci.edu/dataset/891/cdc+diabetes+health+indicators>

Option A - Python:
```bash
pip install ucimlrepo
python -c "from ucimlrepo import fetch_ucirepo; d=fetch_ucirepo(id=891); \
d.data.features.join(d.data.targets).to_csv('data/raw/diabetes_012_health_indicators_BRFSS2015.csv', index=False)"
```

Option B - download the CSV from the UCI page and save it to
`data/raw/diabetes_012_health_indicators_BRFSS2015.csv`.

Verify with `python -m src.data_loader`. You should see 253,680 rows and 22 columns.

## Dataset status

| Dataset | Role | Status |
|---|---|---|
| BRFSS 2015 (UCI) | Original PP1 benchmark (US) | Superseded by South Asian data |
| DiaBD, Bangladesh (Mendeley m8cgwxs9s6, CC BY 4.0, Data in Brief 2025) | Main real data: 5,288 adults, 6.5% diabetic | In use - `src/external_data.py` |
| Narsingdi hospital, Bangladesh (Mendeley rn9m3zb7nt, CC BY 4.0) | Second site: 1,065 rows, only 496 unique after removing 569 exact duplicates | In use |
| Synthetic (Gaussian copula fitted on the DiaBD training split) | Training augmentation only; never in the test set | In use - `src/synthetic.py` |
| Pabna, Bangladesh (Mendeley vxnyysk9vc) | Rejected: every row is already in the Narsingdi file | Not used |
| "Diabetes Risk Prediction", Bangladesh (Mendeley xv25yjbzkm) | Rejected: 20,000 rows with hard-clipped ranges, uniform ages and 8-decimal BMI look generated, not measured | Not used |
| Early-stage symptoms, Sylhet (UCI 529) | Rejected: symptoms of diabetes, not risk factors | Not used |
| CKD in diabetics, Bangladesh (Mendeley hjkzgbxgv5) | Rejected: every patient is diabetic, so there is no diabetes label | Not used |
| WHO STEPS Sri Lanka 2021, SLHAS, SLDCS | Sri Lankan validation | Not openly available - request pending |

No open individual-level Sri Lankan dataset exists. The real data is from
Bangladesh, the closest open South Asian population. It must never be described
as Sri Lankan data.

## South Asian experiment (real + synthetic)

```bash
python -m src.external_data          # download both Bangladesh files, writes manifest.json
python -m src.south_asia_dataset     # harmonise into data/processed/c3_south_asia.csv
python -m src.experiment_south_asia  # real vs real+synthetic vs synthetic-only, second site, pooled
```

Feature-to-schema mapping and missingness: `outputs/reports/south_asia_schema.csv`.
Results: `outputs/reports/south_asia_experiment.json`.

Every result is reported without and with glucose: glucose is a blood test that a
questionnaire-only user would not have. Impossible values (for example BMI 574 or
height 0.36 m in DiaBD) are set to missing, not trusted.
