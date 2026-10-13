# RP diary - Rajapaksha R.M.L.I (IT23315846), Component 3

Write an entry on every day you work. Short and honest beats long and polished.
The examiner is looking for an development story: decisions, problems and fixes.

---

## Entry template - copy this block

**Date:**
**Activity:**
**Objective:**
**What I implemented:**
**Technical decision:**
**Why I chose it:**
**Problem encountered:**
**How I solved it:**
**Evidence:** (commit hash, screenshot filename, test output)
**AI assistance used:** (tool, what for - see docs/ai_usage_log.md)
**What I verified myself:**
**What I changed myself:**
**Reflection:**
**Next step:**

---

## Example of a well-written entry (this is a FORMAT EXAMPLE, not a record of your work)

**Date:** [date]
**Activity:** Baseline model training
**Objective:** Get a first measurable result to compare later models against
**What I implemented:** `src/train.py` with logistic regression and random forest
**Technical decision:** Put StandardScaler inside a scikit-learn Pipeline
**Why I chose it:** Scaling outside the pipeline fits on the whole dataset and
leaks test statistics into training. Inside the pipeline it is fitted per fold.
**Problem encountered:** Accuracy looked high but recall on the positive class was poor
**How I solved it:** Set class_weight="balanced" and switched the headline metric
from accuracy to PR-AUC and recall
**Evidence:** commit [hash], outputs/reports/model_comparison.json
**AI assistance used:** [tool] to explain why accuracy misleads on imbalanced data
**What I verified myself:** Re-read the scikit-learn docs on class_weight; checked
the confusion matrix by hand
**What I changed myself:** Chose the metric set; added the specificity calculation
**Reflection:** Accuracy would have made a useless model look good
**Next step:** Add SHAP to the trained random forest
