# Data dictionary - BRFSS 2015 (PP1 dataset)

All 21 features plus the target. Value codes follow the BRFSS codebook;
confirm against the official codebook before quoting them in the report.

| # | Field | Type | Unit / values | Raw or derived | Preprocessing | Schema factor |
|---|---|---|---|---|---|---|
| 1 | Diabetes_012 | categorical | 0 none, 1 prediabetes, 2 diabetes | raw | binarised to 0/1 for PP1 | TARGET |
| 2 | HighBP | binary | 0 no, 1 yes | raw | none | 7. Clinical |
| 3 | HighChol | binary | 0 no, 1 yes | raw | none | 7. Clinical |
| 4 | CholCheck | binary | 0 no, 1 yes (5 yrs) | raw | none | 7. Clinical |
| 5 | BMI | continuous | kg/m² | derived by BRFSS | scaled for logistic regression | 2. Anthropometric |
| 6 | Smoker | binary | 100+ cigarettes lifetime | raw | none | 6. Behaviour |
| 7 | Stroke | binary | 0 no, 1 yes | raw | none | 5. Medical history |
| 8 | HeartDiseaseorAttack | binary | 0 no, 1 yes | raw | none | 5. Medical history |
| 9 | PhysActivity | binary | activity in past 30 days | raw | none | 3. Lifestyle |
| 10 | Fruits | binary | fruit 1+ per day | raw | none | 4. Diet (weak proxy) |
| 11 | Veggies | binary | vegetables 1+ per day | raw | none | 4. Diet (weak proxy) |
| 12 | HvyAlcoholConsump | binary | men >14, women >7 drinks/wk | raw | none | 6. Behaviour |
| 13 | AnyHealthcare | binary | has coverage | raw | none | 1. Access |
| 14 | NoDocbcCost | binary | cost barrier in past year | raw | none | 1. Access |
| 15 | GenHlth | ordinal | 1 excellent to 5 poor | raw | kept ordinal | 5. Medical history |
| 16 | MentHlth | count | poor mental health days, 0-30 | raw | scaled | 5. Medical history |
| 17 | PhysHlth | count | poor physical health days, 0-30 | raw | scaled | 5. Medical history |
| 18 | DiffWalk | binary | difficulty walking/stairs | raw | none | 5. Medical history |
| 19 | Sex | binary | 0 female, 1 male | raw | none | 1. Demographic |
| 20 | Age | ordinal | 1 = 18-24 ... 13 = 80+ | banded by BRFSS | kept ordinal | 1. Demographic |
| 21 | Education | ordinal | 1 none to 6 college 4+ yrs | raw | kept ordinal | 1. Demographic |
| 22 | Income | ordinal | 1 <$10k to 8 >=$75k | raw | kept ordinal | 1. Demographic |

## Coverage against the eight-factor schema in the proposal

| Schema factor | Coverage in BRFSS | Gap to close in PP2 |
|---|---|---|
| 1. Demographic | Good | Age is banded, not exact |
| 2. Anthropometric | Partial | BMI only; no waist circumference |
| 3. Lifestyle / activity | Weak | yes/no only; no duration or intensity |
| 4. Diet / nutrition | Weak | Component 1 supplies real nutrition data |
| 5. Medical / family history | Partial | **no family history of diabetes at all** |
| 6. Medication / behaviour | Weak | no medications, no adherence |
| 7. Clinical / lab | Weak | self-reported flags; no HbA1c, glucose or lipid values |
| 8. Glycemic forecast | Absent | Component 2 supplies this |

State this openly at PP1. Naming the limits of your own dataset reads as rigour.
