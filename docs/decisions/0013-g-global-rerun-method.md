# 0013 Stage G: how the global rerun is done

## Background

Task card `G-global` requires: switching the region configuration to global (a new configuration, without changing the frozen `config/regions.json` and settings), rerunning the pipeline after gridding with the frozen model settings (training the production version, generating the series, stability intervals, export), reporting validation-window scores by GFED region with the same grader, and then publishing the global dataset. Re-selecting the model and retaking the test are not allowed.

On 2026-11-03 the user agreed to extend to global coverage and authorized the AI to decide the technical details and write them up. All items below were fixed **before seeing any global scores**. The code is in `harmonization/global_grid.py` and `harmonization/series_global.py`; the global configuration is in `config/regions-global.json`.

## 1. Git: how to continue and open a PR

- **Situation**: PR #2 has been squash-merged into main (`e8a260e`). The file tree of `feat/data-harmonization` is identical to main, but the histories are not connected.
- **Approach**: on `feat/data-harmonization`, run `git merge --no-ff origin/main` (merge commit `cd6d467`), keep working on this branch, and finally open a new PR into main.
- **Reasons**:
  - no reset, stash or force-push is needed;
  - it follows AGENTS.md red line 6 (work on this branch);
  - this branch name is hard-coded in the grading workflow `grader.yml` (frozen);
  - the new PR shows only the stage G changes.
- After the merge the guardrail check has 0 violations (the frozen manifest's history is append-only).

## 2. Global coverage (`config/regions-global.json`)

- **Cells**: every 0.25° cell meeting any of these conditions is included, 278,192 in total:
  - its GFED4.1s basis-region code is not 0 (land);
  - it has had any cleaned hotspot from any satellite between 2000-11 and 2026-10;
  - it lies in any scoring rectangle (so every rectangle is complete);
  - it lies in one of the six boxes in `config/regions.json` (so v1's six regions are complete).
- **Regions**: the 14 GFED4.1s basis regions. Ocean cells (code 0) are assigned to the region of the nearest land cell.
- **Holdout regions**: the three holdout boxes are kept exactly as in `config/regions.json` and listed separately as regions, with `role = holdout`. They have no VIIRS columns, take no part in training or scoring, and every month of their series is a model estimate. All other cells have `role = train`.
- The frozen `regions.json` is only read, never changed; `regions-global.json` is not frozen.

## 3. Model: frozen settings, retrained on the global training cells (per the task card)

- **Production version**:
  - E028, with all parameters and numbers of trees (766 / 970) taken from `results/freeze.json`;
  - retrained on the usable cell-months of the global training cells (`role = train`) from 2014-01 to 2021-06;
  - no re-tuning (no Optuna run) and no new early stopping.
- **Validation windows**: each uses that window's own frozen configuration (`validation_windows` in `freeze.json`), the same as S12's `terra-check`.
- **Relation to S11**: the S11 test scores belong to the evaluation version trained on the 3 demo regions only; the global version has no test scores, which the data documentation states.
- **Why the S11 model is not simply applied globally**: the task card says "rerun training (production version)", and plan section 2 says "switch to the global configuration and rerun everything". Under the global configuration the frozen code (`freeze.training_table`) uses all training cells anyway. Moreover, Test 2 already showed that training on only 3 regions leads to large errors in new ecosystems (holdout MALE 0.644, central Siberia 1.14).
- **Awaiting human confirmation (a look-over is enough)**: this item follows the task card, but it means the production version is not the same model as the one that took the test, so a person should be aware of it.

## 4. Global validation scores (reported only, not used for selection)

- Scored with the frozen `evaluate.score` on both validation windows. The scoring units are the demo rectangles and GFED rectangles on training cells (ADR 0004 item 2: stage G uses `rect_sets=("demo", "gfed")`). Reported over three scopes: all, GFED only, demo only. MALE and auxiliary metrics are given by region, and region-year total bias by GFED region.
- M1s (λ = 20), QM and M0 are fitted on the same training rows and listed alongside; the difference from M1s uses the frozen `bootstrap_diff`.
- Reference: S11's window models (trained on the 3 demo regions only, same parameters) applied directly to the globe, as a reference only.
- **Agreed in advance**: whatever these scores are, the production version is the global retrain of item 3. The scores are not used to pick a model, change parameters or change the coverage; if the global version is clearly worse than M1s in some regions, this is written truthfully in the report and the data documentation and left to a person to decide.

## 5. Stability intervals

- **Cell level**: use the 100 whole-year resamples sealed in S11 (`seeds.resampling`; the years drawn are checked one by one against `freeze.json`), with frozen parameters and numbers of trees; each time retrain on the resampled global training rows and take the 5% / 95% quantiles.
- **Region level**: quantiles of the resampled totals per region × month. Per ADR 0008 item 5 and the S11 test results, the intervals are multiplied by a calibration factor.
  - The calibration factor is re-derived with the frozen formula (`freeze.interval_scale`) on the GFED region × month totals of the **global** two validation windows, rather than reusing S11's 5.37. Reason: 5.37 is a number for 3 demo regions and the demo model, and does not apply once the training data and region sizes change.
  - This requires 100 resamples on each of the two validation windows as well.
  - **Awaiting human confirmation**: this changes the source of the interval calibration.
- Computed only for two levels, GFED regions and the six boxes; areas the user draws still use the approximation from the first 20 resamples (as in v1).

### Item 5 addendum (2026-11-04): only the first 50 resamples per group

- **What changed**: all three groups, the production version (deploy), the main validation window and the auxiliary validation window, use only the first 50 whole-year resamples instead of 100:
  - The cell-level 5% / 95% quantiles use these 50.
  - The interval calibration factor uses the first 50 of each of the two validation windows. The auxiliary window had already computed 100; only the first 50 are taken, so both windows use the same resamples.
  - Code: `RESAMPLES = 50` in `harmonization/series_global.py`.
- **Not newly drawn**: these 50 are the first 50 of the S11 sealed resamples (`seeds.resampling`). The random numbers are generated in order, so resample b is exactly the same as S11's resample b. The code still checks the years drawn one by one against `results/freeze.json`.
- **Reason**: run time. With 100 the computation would not finish until around 19:00; with 50 it can be done the same day. The 5% / 95% quantiles from 50 are only slightly noisier than from 100, an approximation. The point estimates, all scores and the model itself do not change. The front end already uses only 20 for areas the user draws (`docs/data-interface.md`).
- **When it was decided**: before any global interval coverage or calibration factor had been computed. The global validation MALE (`reports/global-scores.md`) had already been computed by then, but it uses only point estimates and does not depend on the number of resamples.
- **Who decided**: approved by the user and relayed by the top-level session (data analysis and algorithm design), 2026-11-04.
- To use the full 100 later, just set `RESAMPLES` back to 100 and run the remaining resamples. Finished ones do not need recomputing.

## 6. The rest of the series is exactly as in v1

- Source rules, the Terra bridge, the NOAA-20 continuation, the near real-time flag and `est_m0` all follow `series_v1.build`.
- The fitting range of the bridge and continuation ratios becomes global: the bridge uses all cells, the continuation all training cells, with GFED regions as priors.
- The ratios depend only on the sums per "cell × calendar month", so they are summed by band first and then fitted. The counts are integers, so the result is exactly the same as fitting on the whole table directly (checked in `tests/test_global.py`).

## 7. Implementation choices made to keep it computable (they do not change results)

- **Split by latitude**: the global dense table has about 86.8 million rows and is written to disk in 10° latitude bands (`processed/global/grid/band_NN.parquet`).
  - `grid.dense_regions` only gained an optional parameter `cells`; with the default value its behavior is unchanged (the S15 reproduction check still applies).
  - The frozen files used (`prepare`, `evaluate`, `harmonize`, `freeze`) were not changed by a single character.
- **Identical inputs predicted once**: cell-months with exactly the same features must get the same model estimate. Many rows where "neither the cell nor its neighbors have MODIS hotspots" have repeated features, so each feature combination is predicted once and then spread back. The code checks value by value on each band that the spread-back features are identical to the originals, and raises an error on a hash collision.
- **Converted to float64 once**: the training inputs are converted into a single float64 block. LightGBM converts mixed types to float64 anyway, so the values are the same; this just saves a few copies in memory.
- **Resamples split across processes in parallel**: each process still uses 8 threads (`harmonize.THREADS`; results depend on the thread count). Each resample's result is saved to its own file, and finished ones are skipped after an interruption.
  - With two processes in parallel memory ran out twice (long-running processes keep growing their committed memory). So it was changed to run one process at a time, starting a new process every 20–25 resamples (`--max-new`) and freeing the model after each resample. Results are unchanged.

## 8. Release

- Files go in `processed/global-v1/`, in the same format as v1, plus a `gfed_region` column and `frontend/index.json` listing the region files.
- Front-end JSON: the 14 GFED regions (without the holdout boxes), the 3 holdout regions, and the 3 training boxes (California, Córdoba, southern Africa, cut out of the global results).
- Interface description: `docs/data-interface-global.md`.
- Release tag `global-v1`. **Stop before publishing and ask a person to look it over** (task card requirement).

## Status

Decided by the AI under the user's authorization (technical details judged by the AI), 2026-11-04.

**Confirmed** (when the user looked over `reports/global-review.md` on 2026-11-04 and approved publishing Release `global-v1`, these were confirmed at the same time):
- Item 3: the production version becomes the global retrain, which differs from the model that took the test;
- Item 5: the global interval calibration factor is re-derived on the global validation windows (result 16.75).

Item 5 addendum (only the first 50 resamples per group): approved by the user (2026-11-04, relayed by the top-level session).

The rest are implementation details, now recorded.
