# CI / shared-config PR note from C3

**For:** whoever owns the root `pyproject.toml`, `.env.example` and `uv.lock`.
Nothing below was edited by C3; these are requests for a reviewed PR.

## 1. mypy override (root `pyproject.toml`)

The new C3 server code (`services/`, `api/`, `schemas.py`, `settings.py`, `main.py`) is fully
typed and passes `mypy --strict`. The older ML, training, demo and test code does not (about
160 errors: untyped pandas/sklearn/SHAP/LIME code and missing annotations). Until that code
is typed, CI's `uv run mypy server` stays red on the C3 branch. Proposed block:

```toml
[[tool.mypy.overrides]]
# Files outside src/ are named by their folder (mypy explicit_package_bases).
module = [
    "c3_risk_xai.ml.*",
    "server.services.c3_risk_xai.training.*",
    "server.services.c3_risk_xai.demo.*",
    "server.services.c3_risk_xai.tests.conftest",
    "server.services.c3_risk_xai.tests.test_pipeline",
]
ignore_errors = true

[[tool.mypy.overrides]]
module = [
    "sklearn.*", "shap.*", "lime.*", "xgboost.*", "joblib.*", "yaml",
    "streamlit.*", "pandas.*", "scipy.*", "matplotlib.*",
]
ignore_missing_imports = true
```

Scope: only C3's legacy ML, training, demo and two test files. Nobody else's checks get
weaker. Checked on 2026-10-13: with this block, `uv run mypy server` reports
"Success: no issues found in 70 source files"; without it, about 156 errors, all in C3.

## 2. `uv.lock`

C3 adds its ML dependencies to `server/services/c3_risk_xai/pyproject.toml`
(pandas, numpy, scikit-learn, xgboost, shap, lime, matplotlib, joblib, pyyaml; Streamlit
only in the optional `demo` extra). The lock diff is **additions only (+823 lines)**: no
existing package version changes. Two pins were loosened on purpose so shared packages
are not downgraded: `pyyaml>=6.0.2` and `streamlit>=1.38`.

## 3. Environment variables (`.env.example`)

Proposed additions, both optional:

```
# C3: folder with the trained model bundles (default: data/c3/models from config.yaml)
C3_MODEL_DIR=
# C3: true only on a researcher's machine; lets ?debug=true return probability and cut-offs
C3_RESEARCH_MODE=false
```

## 4. Streamlit for the PP1 demo

Still the open question in `CLAUDE.md`. Streamlit is a demo client only (`demo/`), calls C3
through the gateway, and is not a service dependency.
