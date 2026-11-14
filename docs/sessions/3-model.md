# Task card 3-model: LightGBM and AI-driven automated experiments (S10)

> Before starting, read progress, claim the card and run the preflight following the "Start-of-session routine" in [`AGENTS.md`](../../AGENTS.md).

## Prerequisites

- S07–S09 are done: the grader is frozen, fallback score table v1 is out, and the milestone A pre-release exists.
- If this machine has no data: download it from the Release recorded in `PROGRESS.md` and check the SHA256.
- Several hours at full CPU load, 10–20 GB of memory; no GPU needed.

## What a person must prepare

- Confirm that it can run for up to 8 hours straight (during class say "class is starting" and background work drops to low priority with at most 8 threads; "class is over" restores full speed; "pause" stops after the current experiment finishes).
- Ask a person to look over the review subagent's conclusions.

## Plan sections to read (only these)

From [`docs/execution-plan.md`](../execution-plan.md): section 2 (models, features), section 3 item 7 (selection rule), section 5 (AI-driven automated experiments), the S10 row of the table in section 6; plus [`docs/preregistration.md`](../preregistration.md). For the experiment framework and the `program.md` template, see the proposal's "AI-driven automated experiment loop" and "B4".

## Stages to do

### S10 LightGBM and AI experiments

- Hand-write the first version (in `harmonization/harmonize.py`): Tweedie objective (variance_power starting at 1.3) or Poisson; a monotonically increasing constraint on the MODIS count; 15–31 leaves, at least 50 rows per leaf; learning rate 0.05; deterministic mode, fixed seed. Write the feature list into `config/features.json` (CI checks it for banned features).
- Write `harmonization/program.md` (following the proposal's template) and run the experiment loop: **only `harmonize.py` may be changed**; the LLM makes only structural changes, and numeric tuning is left to Optuna; each experiment states a one-sentence hypothesis recorded in `harmonization/experiments.csv`; if the result is better, keep it and commit to a separate branch (for example `exp/lightgbm`), pushing regularly.
- Budget: at most 150 experiments or 8 hours; stop after 30 consecutive runs without improvement; an improvement counts only if it exceeds 1 standard error.
- At the end, open a **review subagent with a fresh context** to review the top 3: check for leakage, run feature-ablation experiments, draw prediction-relationship plots, and check stability on the auxiliary window. Write the review notes to `reports/model-review.md`.

## Acceptance criteria

- `experiments.csv` is complete; the review notes are done; the validation scores of the top 3 are shown side by side with M1s and QM, with 95% intervals from "year × region" block resampling.

## Not allowed

- Changing any evaluation-related file other than `harmonize.py`; using year, region name or VIIRS information as features.
- Looking at the test set or holdout-region data; pushing the `final-test` tag (that belongs to session 4 and is a person's decision).
- Building models outside the plan (CNNs, pixel-level models and so on); M2 and M5 are done only after S15 and if quota remains.

## When finished, update

- `PROGRESS.md` stage table row S10 (number of experiments, best validation MALE, improvement over M1s); change the status block to `current_card: docs/sessions/4-freeze-test.md`, `status: ready`, clear the claim, `last_pushed_stage: S10`, and add "Session 4 needs a person to decide on pushing the final-test tag" to `needs_human`. Update the README progress box to match. CI green.

## Next card

[`4-freeze-test.md`](4-freeze-test.md)
