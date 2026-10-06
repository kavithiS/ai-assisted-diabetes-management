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
| BRFSS 2015 (UCI) | PP1 development and benchmarking | In use |
| NHANES | PP2 - links diet and clinical data per participant, needed for the ablation | To obtain |
| WHO STEPS Sri Lanka 2021 | PP2 - Sri Lankan validation | Request pending |
| SLHAS | PP2 - HbA1c and medication adherence | Request pending |

BRFSS is **US self-reported survey data**. It must never be described as
Sri Lankan data. Sri Lankan validation is PP2 work.
