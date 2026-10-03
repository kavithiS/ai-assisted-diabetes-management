# Personalized AI Diabetes Care System for Sri Lankan Patients

SLIIT final-year research project **J26-IT-352**.

> **Research prototype.** This system is not a diagnostic or clinically validated tool and
> must not be used for medical decisions.

## Components

| ID | Component | Directory | Status |
|----|-----------|-----------|--------|
| C1 | Food Recognition & Nutritional Analysis | [`components/c1_food_nutrition/`](components/c1_food_nutrition/) | Phase 0 scaffold |
| C2 | Glucose forecasting | not created yet | |
| C3 | Risk profiling + explainability (XAI) | not created yet | |
| C4 | Mobile app (Flutter) | not created yet | |

Components integrate only through versioned HTTP APIs. C1 serves `/api/v1`, consumed by
C2 and C3.

## Repository layout

Each component is self-contained under `components/`, with its own tooling, CI workflow
(`.github/workflows/<component>.yml`, path-filtered) and pre-commit block. The layout is
proposed in C1's [ADR 0002](components/c1_food_nutrition/docs/adr/0002-monorepo-layout.md),
pending confirmation by all component owners.
