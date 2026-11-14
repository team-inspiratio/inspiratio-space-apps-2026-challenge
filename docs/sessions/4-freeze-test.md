# Task card 4-freeze-test: freeze, external blind grading, final dataset (S11–S12)

> Before starting, read progress, claim the card and run the preflight following the "Start-of-session routine" in [`AGENTS.md`](../../AGENTS.md).

## Prerequisites

- S10 is done: `experiments.csv` and the review notes are complete.
- `grader.yml` was committed and frozen in S01; prepare, evaluate and final_test were frozen in S07.
- `results/final-test/` **does not exist** (if it exists, the test has already been taken and can be taken only once: stop at once and tell a person).

## What a person must prepare

- **A person decides in person** whether to push the `final-test` tag. The AI only gets everything ready, then stops, gives the command to run, and waits for the person to confirm.
- `gh auth login --web` is done (to view the Actions run results and publish releases).

## Plan sections to read (only these)

From [`docs/execution-plan.md`](../execution-plan.md): section 2 (the methods needed to generate the series), section 3 items 5 and 7, section 4 (external blind grading), the S11–S12 rows of the table in section 6; plus [`docs/preregistration.md`](../preregistration.md). For details, see the proposal's "B5", "B6" and "Producing the final series".

## Stages to do

### S11 Freeze and blind grading

- Following the pre-registered selection rule (at least 10% better than M1s, neither window clearly worse, guardrail metrics within tolerance, passing the leakage review, improvement of more than 1 standard error), decide between LightGBM and M1s, and write a decision record in `docs/decisions/`.
- Write the frozen manifest (features, parameters, number of trees, code version), and freeze `harmonize.py` and `config/features.json`.
- Retrain the frozen model on the training regions for 2014-01 to 2021-06 and, **using only MODIS inputs**, generate the test-period predictions `submission.parquet` (Test 1 years + holdout regions); write its hash into the frozen manifest, then commit and push (the answer sheet is sealed first). Seal M1s's answer sheet at the same time as a comparison.
- Stop and ask a person to push the tag: `git tag final-test && git push origin final-test`. GitHub Actions downloads the locked data itself, scores the submission and commits the scores back to the repository.
- When the scores come back, `git pull` and write them truthfully into `reports/final-test.md`, good or bad.

### S12 Final dataset

- Retrain the production version on all overlap data from the training regions for 2012-02 to 2021-06 (the holdout regions stay isolated). The evaluation version and the production version each record their code, features, number of trees and training range.
- Year-block resampling 100 times for stability intervals (first sum to regional or monthly totals, then take the 5%/95% quantiles); report the actual coverage on the test set (plan section 3 item 5).
- Generate the series from 2000-11 to 2026-10 with source flags (VIIRS observed, MODIS estimate, Terra low confidence, NOAA-20 continuation, near real-time, missing).
- Acceptance spot check: the S-NPP segment (complete months 2012-02 to 2026-10) exactly matches the observed counts under the same quality control.

## Acceptance criteria

- The scores are committed back to the repository by CI; `reports/final-test.md` records them truthfully.
- The final dataset passes the "S-NPP segment exactly matches the observations" check; the processed data is uploaded as a Release asset with its SHA256 recorded.

## Not allowed

- The AI pushing the `final-test` tag itself; changing the model and retaking the test after seeing the test scores; using test scores to choose among several models.
- Changing `grader.yml` or any frozen file; downloading the locked data on this machine.

## When finished, update

- `PROGRESS.md` stage table rows S11–S12 (selected model, test MALE, coverage); change the status block to `current_card: docs/sessions/5-report.md`, `status: ready`, clear the claim, `last_pushed_stage: S12`. Update the README progress box to match. CI green.

## Next card

[`5-report.md`](5-report.md)
