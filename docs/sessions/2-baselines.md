# Task card 2-baselines: grader, fallback models, milestone A (S07–S09)

> Before starting, read progress, claim the card and run the preflight following the "Start-of-session routine" in [`AGENTS.md`](../../AGENTS.md).

## Prerequisites

- S01–S06 are done, and `PROGRESS.md` records the data Release (for example `data-v0`) and its SHA256.
- If this machine has no data: download it into `INSPIRATIO_DATA_DIR` with `gh release download data-v0` and check the SHA256; or rebuild it from scratch with the pipeline (slow).
- An ordinary laptop is enough (50 GB is not needed).

## What a person must prepare

- `gh auth login --web` is done (needed to download the Release data and publish the pre-release).
- Before S07 freezes prepare and evaluate, ask a person to look them over (the plan requires "frozen after the lead confirms").

## Plan sections to read (only these)

From [`docs/execution-plan.md`](../execution-plan.md): section 2 (method, splits), section 3 (validation), section 4 (test-set isolation), the S07–S09 rows of the table in section 6, and section 10; plus [`docs/preregistration.md`](../preregistration.md). For implementation details, see the proposal's "Validation framework", "B1", "B2", "Producing the final series", "Anomaly indicators" and "C1".

## Stages to do

### S07 Grader

- `harmonization/prepare.py`: split out the main validation window and the auxiliary backward window according to the frozen settings; read the frozen random rectangles.
- `harmonization/evaluate.py`: score both windows and output MALE (the main score, averaged by region and complete year and then pooled with equal weights) and the auxiliary metrics (share of positive estimates on zero-hotspot samples, error for 1–9 hotspots, total bias, seasonal correlation). When calling `predict()`, **pass only MODIS features**, never VIIRS columns or the year column (prove this with pytest).
- `harmonization/final_test.py`: for `grader.yml`, following the calling convention set in S01. It is not run on this machine.
- Use the two dummy methods "always predict 0" and "use the MODIS count directly" to check that their scores are as bad as they should be; two runs are bit-for-bit identical.
- Freeze after a person has looked them over: `uv run python tools/guardrails.py freeze harmonization/prepare.py harmonization/evaluate.py harmonization/final_test.py`.

### S08 Fallback models

- Implement M0, M1s (λ ∈ {0, 5, 20, 50, 100}, chosen on the validation set) and QM (quantile mapping) in `harmonization/harmonize.py` (the only file the AI experiments may change).
- Terra→Aqua bridge ratio; NOAA-20→S-NPP continuation test using the 2018–2026-10 overlap period (fit on the early part, test on the late part, check day and night separately).
- Score table v1: `reports/scores-v1.md`.

### S09 ★Milestone A

- Generate dataset v0 with M1s (2000-11 to 2026-10, with source flags).
- Export the front-end files (one compressed JSON per region) and draft the data interface spec `docs/data-interface.md` (fields, units, source flags, how missing data is represented, definitions of the anomaly indicators).
- Publish a GitHub pre-release (for example `milestone-a`) with the data package and its SHA256. Tell the front end it can start (state this in the PR and in PROGRESS).

## Acceptance criteria

- prepare, evaluate and final_test are frozen and CI's frozen-hash check passes; the dummy-method checks and the reproducibility test pass.
- Score table v1 contains all metrics for M0, M1s and QM on both validation windows.
- The pre-release exists, and with its files and the interface spec the front end can start work.

## Not allowed

- Using the test set or holdout-region data for anything; letting `predict()` get VIIRS columns or the year column.
- Changing prepare, evaluate or final_test after they are frozen.
- Starting LightGBM (it belongs to session 3).

## When finished, update

- `PROGRESS.md` stage table rows S07–S09; change the status block to `current_card: docs/sessions/3-model.md`, `status: ready`, clear the claim, `last_pushed_stage: S09`. Update the README progress box to match. CI green.

## Next card

[`3-model.md`](3-model.md)
