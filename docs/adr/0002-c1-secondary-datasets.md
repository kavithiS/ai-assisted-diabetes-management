# ADR 0002: C1 uses secondary datasets only

- **Status:** Accepted
- **Date:** 2026-10-08
- **Component:** C1 Food Recognition & Nutritional Analysis (Thilakarathne K.S)

## Context

TAF task 1 for C1 was worded "collect & annotate" food image data. The TAF supervisor comment
says "Data sets are available".

## Decision

C1 uses **secondary datasets only**. No new food images are collected.

| Purpose | Source | Role |
|---|---|---|
| Food images | Food-101 | Primary |
| Food images | UEC-FOOD-256, VIREO Food-172 | Optional |
| Nutrition | USDA FoodData Central (mapped to the MRI 36-column schema) | Primary |
| Nutrition | MRI Sri Lanka Food Composition DB | Sri Lankan values |

## Consequences

- No ethical clearance is needed for C1, because no primary images are collected.
- The novelty claim "first large-scale annotated Sri Lankan food dataset" no longer applies and
  must not be repeated anywhere. The remaining TAF novelty is the multi-label CNN for mixed-dish
  recognition and the hybrid MRI Sri Lanka + USDA nutritional knowledge base.
- The current MRI CSV export is corrupted. The importer must reject a header of `food_100me`.
  Fixing the export is an open C1 item.
