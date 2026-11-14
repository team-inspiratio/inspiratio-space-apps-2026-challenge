# Task card G-global: global rerun

> Before starting, read progress, claim the card and run the preflight following the "Start-of-session routine" in [`AGENTS.md`](../../AGENTS.md).

## Prerequisites

- S15 (milestone B) is done and Release v1 is published.
- On 2026-11-03 the user agreed to extend to global coverage (plan section 2); stage G is planned work.
- Machine: about 50 GB of disk, 16 GB+ of RAM; the global cleaned data can be downloaded from session 1's Release (download and cleaning are global anyway).

## What a person must prepare

- Confirm that there is enough quota to finish the global run (possibly several hours at full CPU load).
- Ask a person to look over the global results before publishing a release.

## Plan sections to read (only these)

From [`docs/execution-plan.md`](../execution-plan.md): section 2 ("Scope: first the regions set in the proposal, with global coverage kept as a final switch"), section 3, section 4 and section 10.

## Stages to do

- Switch the region configuration from the demonstration regions to global (create a new global configuration file; **do not change the frozen** `config/regions.json` or settings; the holdout regions are still excluded from training in the global version).
- With the frozen model settings, rerun the pipeline from gridding onward: training (production version), series generation, stability intervals, export. The code should not need changes; if it does, first write a record in `docs/decisions/` and ask a person.
- Report global scores on the validation windows with the same grader (broken down by GFED region), side by side with the demonstration-region results.
- Publish the global dataset (Release, with SHA256 recorded).

## Acceptance criteria

- The global dataset is generated and its S-NPP segment exactly matches the observations; global validation scores are reported by region; the front end can load it directly.

## Not allowed

- Using the global version to re-select the model or retake the test (the test is taken only once, and its scores belong to the S11 evaluation version).
- Changing frozen files; downloading 2012/2013 S-NPP.

## When finished, update

- Record the global results in `PROGRESS.md`; set the status block to `status: done`. Update the README progress box to match. CI green.

## Next card

None (the main line is complete). If quota remains, the extensions under "Priority" in plan section 6 can be done: M2, M5, 0.5°/1° sensitivity analysis. Ask a person first.
