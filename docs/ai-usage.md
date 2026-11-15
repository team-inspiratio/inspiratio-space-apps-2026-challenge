# AI usage statement

> Scope: the data-analysis and algorithm work in this repository (branch `feat/data-harmonization`:
> download, cleaning, gridding, models, validation, dataset). The web page, proposal page and demo
> are made by teammates and described separately. NASA Space Apps 2026 asks every team to say how
> AI tools (called "SI" in this year's rules) were used.

## 1. Tools

| Tool | Used for |
|---|---|
| Claude Code (Anthropic), model Claude Opus 5.5 | Writing and running all code in this repository, running the experiment loop, writing reports and documents. Every commit made with it carries a `Co-Authored-By: Claude` line, so the git history shows exactly which changes were AI-assisted. |
| Fresh-context Claude sub-agent | Independent review of the top 3 models before the final choice (leakage, feature ablation, prediction plots): `reports/model-review.md`. |
| GitHub Actions | Not AI: runs the guardrails on every push and the one-time blind grader. |

## 2. What the AI did

- Wrote the pipeline: download (FIRMS archive and API, GFED), import, cleaning, gridding, the judge (`prepare.py`, `evaluate.py`, `final_test.py`), baselines, LightGBM, freezing, the final series, this validation report and the delivery files. About 5,000 lines of Python plus tests.
- Ran the **AI experiment loop** (plan section 5, `harmonization/program.md`): 37 experiments (E000-E036) on LightGBM, each with a one-sentence hypothesis, scored only on the two validation windows by the frozen judge, all logged in `harmonization/experiments.csv`, with each variant's code kept on branch `exp/lightgbm`. Methods compared in total: direct splice (M0), simple ratio (M1s, 5 shrinkage values), quantile mapping (QM), and the 37 LightGBM variants. The two-stage design (classifier, then count model) that won came out of this loop.
- Wrote every figure, report and decision record, including the ones that report the model's weaknesses.

## 3. What people did

- Approved the execution plan and the scope (including extending to a global run later).
- Chose the three holdout regions on geography and ecology alone (`docs/decisions/0001`).
- Reviewed the judge code before it was frozen (`docs/decisions/0004`).
- Decided to cut the experiment budget for time reasons (`docs/decisions/0007`, quoted).
- Pushed the `final-test` tag that starts the one-time blind test. The AI is not allowed to push it.
- Confirm or overrule every open decision in `docs/decisions/` (marked "awaiting human confirmation" in `PROGRESS.md`), and approve merging into `main` and the public release.

## 4. How we kept the AI honest

The main risk with an AI that tries many models is that it fits the test, on purpose or by chance. The safeguards are built into the repository, not left to good intentions:

1. **Pre-registration before any model**: metrics, data splits, the selection rule and its thresholds were written and frozen first (`docs/preregistration.md`, commit `7d1aa0c`).
2. **The test answers never reached the AI's machine**: 2012-2013 S-NPP data and all VIIRS data of the holdout regions are blocked at download and import. Only the GitHub Actions grader downloads them, and it runs once (`.github/workflows/grader.yml`).
3. **Three layers of guardrails** (`tools/guardrails.py`): a Claude Code hook that blocks forbidden downloads and edits of frozen files before they happen, a pre-commit check, and CI on every push. Forbidden model inputs (year, region name, any VIIRS information) are checked by CI.
4. **Frozen files**: the judge, the settings, the regions, the selected model and the sealed submission are hashed in `config/frozen-manifest.json`; only a person can unfreeze them.
5. **Selection on validation only**, with a rule fixed in advance (≥ 10% better than the simple ratio, more than one standard error, no window or region worse, guardrail metrics in tolerance, leakage review).
6. **Results reported as they came out**: the blind test showed the model is much weaker in unseen regions; this is reported in full (`reports/final-test.md`, `reports/validation.md`), and the model was not changed afterwards.

## 5. Limits of this statement

- People reviewed the plan, the judge, the decisions and the reports; most of the remaining code was checked by tests, CI and the independent AI review rather than read line by line by a person.
- The experiment loop was stopped early for time (37 experiments instead of a budget of up to 150), as recorded in `docs/decisions/0007`.
