# PP1 development plan - Component 3

Rajapaksha R.M.L.I (IT23315846) · J26-IT-352 · branch `c3_lochana`

---

## YOUR PP1 TARGET

By PP1 you must be able to sit down, run your prototype live, and show a panel:

> A patient's risk factors go in. A trained model returns a risk probability and
> band. SHAP and LIME independently explain which factors drove it. The system
> says in plain English why, states what data was missing, and states that it is
> not a diagnosis.

Everything else - DHS, C1/C2 integration, FastAPI, Sri Lankan validation - is PP2.
**Two finished functions beat six half-built ones.**

---

## YOUR TWO KEY FUNCTIONS

### Function 1 - Multi-factor diabetes risk prediction

| | |
|---|---|
| Input | Patient record: age, sex, BMI, BP flag, cholesterol flag, smoking, activity, general health, medical history |
| Processing | Validation → missing-field reporting → feature alignment → trained classifier |
| Output | Risk probability, Low/Moderate/High band, data-completeness status |
| Technology | Python, pandas, scikit-learn, XGBoost, joblib |
| Difficulty | Moderate |
| Depends on | Dataset only. **No dependency on other members** - this is why it is safe for PP1 |
| Tested by | `pytest` - range, banding, missing fields, feature order, directional sanity, extreme values |
| Evidence | Terminal output, `model_comparison.json`, commits, passing tests |

**Why it satisfies the rubric:** it is proof of concept (10%), it is the core
knowledge area of your component (25%), and it is a completed, tested,
standards-following implementation (40%).

### Function 2 - Explainable risk analysis

| | |
|---|---|
| Input | The prediction from Function 1 plus the patient record |
| Processing | SHAP (Shapley contributions) + LIME (local surrogate) → ranking → agreement check |
| Output | Top-5 ranked factors with direction, SHAP/LIME overlap ratio, plain-language summary |
| Technology | shap, lime, matplotlib |
| Difficulty | Moderate - SHAP on tree models is fast; the care goes into interpretation |
| Depends on | Function 1 |
| Tested by | `pytest` - output shape; manual review of factor plausibility |
| Evidence | SHAP plots, LIME output, agreement ratio, UI screenshots |

**Why it satisfies the rubric:** explainability is the novelty claim in your
proposal. Running two independent XAI methods and honestly reporting their
*disagreement* is a genuine research contribution, not a feature.

**Why not DHS as Function 2?** The DHS has no clinical validation yet. Presenting
an unvalidated score invites the question "how do you know those weights are
right?", which you cannot answer at PP1. Keep it as documented PP2 scope.

---

## SCOPE BOUNDARY

### Must complete for PP1
- Dataset obtained, documented, provenance recorded
- Preprocessing pipeline with leakage control
- Three models trained and compared on real metrics
- Function 1 working and tested
- Function 2 working and tested
- Streamlit demo UI
- Architecture diagram, data dictionary, requirements, risk register, test plan
- GitHub history, diary, Planner tasks, AI usage log

### Should complete if time allows
- SHAP global summary plot saved as a figure
- Calibration curve
- Explanation stability check (run SHAP 5 times, compare rankings)
- One supervisor feedback cycle acted on and recorded

### PP2 / final year
- Adaptive DHS
- C1 and C2 integration via FastAPI
- Recommendation layer with clinician review
- NHANES ablation study
- Sri Lankan validation (STEPS, SLHAS)
- Expert review and user study, after ethics approval

---

## FIVE-WEEK PLAN

### Week 1 - Scope and setup
Freeze scope. Set up the repository, Planner and diary. Get the dataset and
write the data dictionary. Draw the architecture diagram.
**Deliverable:** running project skeleton, dataset inspected, docs started.

### Week 2 - Function 1
Preprocessing, leakage-safe split, three models, comparison table, prediction
function with risk bands.
**Deliverable:** `python -m src.predict` returns a real risk estimate.

### Week 3 - Function 2
SHAP, LIME, agreement check, plain-language narration, Streamlit UI.
**Deliverable:** a working demo you can click through.

### Week 4 - Test and stabilise
Write and run tests. Handle edge cases. Save figures. Complete the risk register
and test plan. Supervisor review, and convert the feedback into tasks.
**Deliverable:** passing test suite, evidence pack, supervisor feedback recorded.

### Week 5 - Rehearse and defend
Build the slides. Record a backup demo video. Practise Q&A. Walk through every
file and confirm you can explain each one.
**Deliverable:** rehearsed 10-minute demo and a defensible codebase.

---

## PHASE-BY-PHASE STEPS

### Phase 0 - Environment (30 minutes)

```bash
git clone https://github.com/kavithiS/ai-assisted-diabetes-management.git
cd ai-assisted-diabetes-management
git checkout c3_lochana
# copy this scaffold into the component-3 folder, then:
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

In VS Code install the **Python** and **Jupyter** extensions, then
`Ctrl+Shift+P` → "Python: Select Interpreter" → choose `.venv`.

Commit: `chore: set up component 3 project structure and dependencies`

### Phase 1 - Dataset
Follow `data/README.md`. Then `python -m src.data_loader`.
Record the real numbers in your diary. Commit the docs, never the CSV.

Commit: `docs: add data dictionary and dataset provenance for BRFSS 2015`

### Phase 2 - Preprocessing
`python -m src.preprocess`. Read the code until you can explain why scaling sits
inside the Pipeline and why the split is stratified.

Commit: `feat: add leakage-controlled preprocessing and train/test split`

### Phase 3 - Models
`python -m src.train`. Compare the three. Note which has the best recall and why
that matters more than accuracy in a screening context.

Commit: `feat: train and compare logistic regression, random forest and XGBoost`

### Phase 4 - Function 1
`python -m src.predict`. Change the example patient's values and watch the risk
move. Confirm the direction makes sense.

Commit: `feat: implement multi-factor risk prediction with risk banding`

### Phase 5 - Function 2
`python -m src.explain`. Check that the top factors are clinically plausible.
Note where SHAP and LIME disagree - that is a finding to discuss.

Commit: `feat: add SHAP and LIME explainability with agreement analysis`

### Phase 6 - UI
`streamlit run app/streamlit_app.py`. Click through it. Fix anything confusing.

Commit: `feat: add Streamlit demo interface for risk and explanations`

### Phase 7 - Tests
`pytest -v`. Screenshot the passing output. Fill in `docs/test_plan.md` with the
results you actually observed.

Commit: `test: add pipeline tests for prediction, banding and explanations`

### Phase 8 - Evidence
Complete the risk register, requirements and AI usage log. Collect screenshots
into `outputs/`. Book the supervisor review.

Commit: `docs: complete risk register, requirements and test evidence`

---

## GIT WORKFLOW

Work on short-lived branches off `c3_lochana`:

```bash
git checkout c3_lochana
git checkout -b c3/function1-risk-prediction
# ... work, commit in small steps ...
git push -u origin c3/function1-risk-prediction
# open a PR into c3_lochana, merge it
```

Good commit messages - small, specific, in the present tense:
- `feat: add risk banding with configurable thresholds`
- `fix: handle missing BMI without defaulting silently`
- `test: add directional sanity check for high-risk profiles`
- `docs: record model comparison results in data dictionary`

Avoid: `update`, `final version`, `changes`, one giant upload at the end.
The panel reads commit history as proof the work is yours.

---

## PLANNER TASKS

| Task | Due | Output | Evidence |
|---|---|---|---|
| Freeze Component 3 scope and confirm two key functions | W1 | Scope note | Supervisor sign-off |
| Set up repository, virtual environment and folder structure | W1 | Running skeleton | Commit |
| Obtain BRFSS dataset and document provenance | W1 | Raw CSV + data dictionary | Commit + terminal screenshot |
| Draw architecture diagram and define I/O contracts | W1 | `docs/architecture.md` | Commit |
| Implement preprocessing with leakage control | W2 | `src/preprocess.py` | Commit + split output |
| Train and compare three classifiers | W2 | `model_comparison.json` | Commit + metrics |
| Implement risk prediction with banding | W2 | `src/predict.py` | Commit + sample output |
| Implement SHAP explanations | W3 | `src/explain.py` | Commit + plot |
| Implement LIME and agreement analysis | W3 | `src/explain.py` | Commit + output |
| Build Streamlit demo interface | W3 | `app/streamlit_app.py` | Commit + screenshots |
| Write and run automated tests | W4 | `tests/` | pytest screenshot |
| Complete risk register and requirements | W4 | `docs/` | Commit |
| Supervisor review and act on feedback | W4 | Meeting note | Diary entry |
| Build slides and rehearse demo | W5 | Slide deck | Rehearsal note |
| Record backup demo video | W5 | Video file | File |

---

## PP1 EVIDENCE CHECKLIST

- [ ] Working prototype that runs on demand
- [ ] Function 1 demonstrated: input → processing → output
- [ ] Function 2 demonstrated: SHAP + LIME + agreement
- [ ] Architecture diagram
- [ ] Dataset provenance documented
- [ ] Data dictionary with schema coverage gaps named
- [ ] Real model comparison metrics (never invented)
- [ ] SHAP output / plot
- [ ] LIME output
- [ ] Passing test suite screenshot
- [ ] Completed test plan with observed results
- [ ] GitHub commit history with feature branches
- [ ] MS Planner board with completed tasks
- [ ] RP diary entries across all five weeks
- [ ] Supervisor meeting notes and actions taken
- [ ] Risk register
- [ ] AI usage log
- [ ] User and functional requirements
- [ ] Slide deck + demo script + backup video
- [ ] Q&A preparation

---

## SLIDE STRUCTURE (10-12 minutes)

| # | Slide | Show | Rubric |
|---|---|---|---|
| 1 | Title | Project, component, your name and ID | - |
| 2 | The problem | Diabetes burden in Sri Lanka; what existing apps do not do | Problem definition |
| 3 | The gap | No explainable multi-factor risk model built on Sri Lankan data | Proven gap |
| 4 | My component | The one-line "if removed, X disappears" answer | Ownership |
| 5 | Architecture | The input → processing → output diagram | Design |
| 6 | **LIVE DEMO** | Both functions end to end | Proof of concept |
| 7 | Dataset | BRFSS now, STEPS/NHANES planned; state the limits yourself | Knowledge |
| 8 | Models | Real comparison table; explain why recall beats accuracy | Technologies |
| 9 | Explainability | SHAP vs LIME, and where they disagree | Key pillars |
| 10 | Testing | Passing tests and the test plan | Standards |
| 11 | Requirements | FR/NFR table with PP1 vs PP2 status | Requirements |
| 12 | Risks | Top 4 risks with mitigations in progress | Risk mitigation |
| 13 | Progress | Commits, Planner, diary; what is next | Completion |
| 14 | Value | Users and benefits; prototype vs medical product | Commercialization |

Spend the most time on slide 6. The demo is the evidence; everything else supports it.

---

## DEMO SEQUENCE

1. Show the repository structure in VS Code - 20 seconds
2. `python -m src.data_loader` - real dataset facts
3. Open the Streamlit app
4. Enter a low-risk patient → show the low band
5. Change to a high-risk patient → show the risk move
6. Read out the SHAP factors
7. Show the LIME cross-check and the agreement ratio
8. Read the plain-language summary and point at the disclaimer
9. `pytest -v` - tests pass
10. One sentence on what comes next

**Backup:** record this as a video in Week 5 and keep saved screenshots. If the
live app fails, switch to the video without apologising and keep talking.

---

## Q&A - the questions that decide your mark

**"What exactly have YOU implemented?"**
The risk schema, the preprocessing pipeline, three trained models, the prediction
function with banding, the SHAP and LIME layer with agreement analysis, the demo
UI and the test suite. Then open the files.

**"If we remove your component, what disappears?"**
The system could still recognise food and forecast glucose, but no one would be
told their overall risk, which factors drive it, or why. The explainable decision
layer disappears.

**"Why isn't your dataset Sri Lankan?"**
BRFSS is development data, chosen because it is large, public and ethically
clean. Sri Lankan validation needs WHO STEPS and SLHAS, which are request-based
and in progress, and primary collection needs ethics approval. I never describe
BRFSS results as Sri Lankan findings.

**"Why not deep learning?"**
On tabular data of this size, gradient boosting is competitive with or better
than neural networks, trains in seconds, and works with exact TreeSHAP. Deep
learning would cost interpretability for no measured gain.

**"What does SHAP actually explain?"**
How much each feature moved *this model's* output away from a baseline
prediction. It explains the model, not the disease.

**"Can SHAP prove a factor causes diabetes?"**
No. It is attribution within a correlational model. Causal claims need a causal
design, which this is not.

**"What if SHAP and LIME disagree?"**
They answer different questions, so partial disagreement is expected. I compute
and report the overlap ratio rather than hiding it, and treat large disagreement
as a signal that the local explanation is unstable.

**"Can your model diagnose diabetes?"**
No, and it never claims to. Every output carries that disclaimer.

**"How will you handle bias?"**
By reporting metrics for demographic subgroups rather than only overall, and by
validating on Sri Lankan data before any local claim.

**"How is the DHS clinically validated?"**
It is not, which is exactly why it is not in the PP1 scope. It is designed as a
self-management indicator, and validation is planned for PP2.

**"Why accuracy isn't your headline metric?"**
The positive class is a minority. A model predicting "no diabetes" for everyone
would still look accurate while being useless, so I report PR-AUC, recall and
calibration.

**"What happens if an important variable is missing?"**
The prediction still runs, but the response flags `data_complete: false` and
lists the missing fields, so the user is told the estimate is based on partial
data instead of being quietly misled.
