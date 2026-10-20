# C1 task playbooks

One file per recurring or planned task. Each says what the task is for, what must be true before starting, the exact steps, how to know it is done, and what to record afterwards. Read `../CONTEXT.md` first.

Anything marked **[UNVERIFIED]** was not checked when the playbook was written (2026-10-15). Check it before relying on it.

| Playbook | Task | Source |
|---|---|---|
| [run-stage2-experiment.md](run-stage2-experiment.md) | Train and score a Stage 2 model, three seeds | CONTEXT §11.4, OPEN_ITEMS C |
| [leak-audit-and-fix.md](leak-audit-and-fix.md) | Find and remove train copies of valid/test photos | CONTEXT §11.2, OPEN_ITEMS C |
| [study-weak-classes.md](study-weak-classes.md) | Find out why some classes score low, and what to try | CONTEXT §11.4, OPEN_ITEMS C |
| [move-training-into-repo.md](move-training-into-repo.md) | Move cleaning and training scripts into `training/` | CONTEXT §11.5, OPEN_ITEMS D |
| [wire-recognizer.md](wire-recognizer.md) | Put the trained model behind `FoodRecognizer`; map classes to nutrition rows | CONTEXT §11.6, OPEN_ITEMS D |
| [nutrition-importers.md](nutrition-importers.md) | Implement the MRI Sri Lanka and USDA importers | OPEN_ITEMS D |
| [portion-estimation.md](portion-estimation.md) | Replace the mock portion estimator | CONTEXT §11.6, OPEN_ITEMS D |

Decisions that belong to other people (OPEN_ITEMS section A) have no playbook: they are questions, not tasks.

## Rules that apply to every playbook

- Ask before any download over about 50 MB, and say the size.
- Never commit, push or open pull requests; give a commit message (`<type>(c1): ...`, no tool or vendor names).
- Report only numbers that a file holds, and name the file.
- After the task: update `CONTEXT.md` (sections 3 and 10), `OPEN_ITEMS.md`, `CHANGELOG.md`, and add an `EXPERIMENTS.md` row for each run.
