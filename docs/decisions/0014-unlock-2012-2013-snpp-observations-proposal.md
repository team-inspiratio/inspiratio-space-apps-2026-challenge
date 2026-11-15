# 0014 Proposal: after the test, replace the training-region estimates with 2012–2013 S-NPP observations

> **This is a proposal and has not been implemented.** This record downloads no data and changes no guardrails, frozen files or datasets. Whether to do it is a person's decision.

## Background

The plan originally used S-NPP observations in the training regions for 2012-02 to 2026-10, but red line 1 says this machine never downloads S-NPP for 2012 or 2013, because they are the answers to the final test. So in dataset v1 this period is a model estimate (ADR 0009 item 1), and that record also describes the alternative: after the test, a person unlocks it and replaces it with observations.

The test is now over:

- The `final-test` tag was pushed by a person, and the run happened only once ([public result archive](../../results/final-test/)).
- The scores are in `results/final-test/`, recorded 2026-11-04 03:50 UTC.

Scope:

- **Months**: 2012-02 to 2013-12, 23 months in total. 22 of them were usable at grading time (10 months in 2012, 12 in 2013, ADR 0010 item 2); the unusable month keeps the model estimate.
- **Cells**: the 3,904 cells of the 3 training regions, 89,792 cell-months in total (equal to the number of Test 1 rows in the answer sheet).
- **Out of scope**: holdout-region VIIRS stays locked; this proposal does not unlock it.

Benefits:

- The training regions' series from 2012 on becomes entirely observations, and the "observed / estimated" boundary on the calendar moves from 2014-01 back to 2012-02.
- The direct-stitching view no longer has a 2012–2013 gap, so the false step in 2012 can be seen directly.
- The "S-NPP only" anomaly baseline gains two more years of history.

## Why the reported test scores are not affected

| What the scores depend on | Does it change after the replacement? |
|---|---|
| The sealed answer sheet `results/submission.parquet` (frozen, hash in `config/frozen-manifest.json`) | No. What is replaced is a new version of the dataset, not the answer sheet |
| The grading results `results/final-test/` (generated in the cloud, committed) | No, and they are not recomputed |
| The frozen model `results/freeze.json` and `harmonization/harmonize.py` | No. **Option B does not retrain** |
| The grading workflow `grader.yml` | No. It refuses to run when scores already exist, so a second test is impossible |
| The published Release `v1` | No. The new data is published under a new version number, and v1 stays as it is |

It also holds logically: the scores answer "with only MODIS, can the model estimate VIIRS for these two years?". That question was answered on 2026-11-04. Replacing the estimates with observations afterwards changes only what these cells show in the data product, not the answer sheet the model submitted at the time.

**Three boundaries must be stated clearly:**

1. **It holds only without retraining.** If these two years were merged into training (option C), the production model would no longer be the one that took the test, and the statement "the scores are the production version's scores" would no longer hold (the benefit of ADR 0009 item 1 would be lost).
2. **These two years can never be a test set again.** To prove an improved model in the future, new untouched data must be used (as section 6 of `docs/project-journey.md` also says).
3. **"The answers never reached this machine" needs a time qualifier.** After unlocking, it must become "before the test ended, the answers never reached this machine", with the unlocking date stated. The relevant text is in `docs/ai-usage.md`, `reports/validation.md`, `docs/data-card.md` and the web methods page.

## Options

| Option | What it does | Pros | Cons |
|---|---|---|---|
| A Keep things as they are | Do not unlock; keep using estimates (the recommendation in ADR 0009) | Zero risk; no text needs changing | The gap and the "estimate" remain |
| **B Replace values only, no retraining** | After unlocking, replace the usable months with observations and publish a new version | Scores unaffected; the product is more complete | Guardrails and quite a lot of text must change; these two years can no longer serve as a test set |
| C Replace and retrain | Merge these two years into training, then generate the series | Close to the original plan; 23 more months of training data | The production model has no test scores, which amounts to giving up the blind test, the core evidence |

With B, there are two ways to get the data:

| Way | Process | Guardrails to change |
|---|---|---|
| **U1 Cloud aggregation** | Create a one-time workflow that fetches the annual archives in the GitHub cloud, computes the training regions' "cell × month" counts with the frozen cleaning and gridding code, and attaches them as a Release asset; this machine only fetches that aggregate | Fewer; this machine's lock can stay |
| U2 Local fetch | Remove this machine's lock and fetch the annual archives directly through the full pipeline | More; and the annual archives contain global data, so the holdout regions must be dropped at import |

## Which guardrails need changing

**All frozen files in the table below may be changed only by a person**; the first line of the commit message must contain `[unfreeze]` and the reason (`check_manifest_append_only` resets its baseline by commit subject), and `config/frozen-manifest.json` must be updated at the same time. An AI cannot do this step, and the hook would block it.

| File | Frozen? | U1 cloud aggregation | U2 local fetch |
|---|---|---|---|
| `AGENTS.md` red line 1, `CLAUDE.md` | No, but they are red lines, changed by a person | Change to "this machine does not fetch the raw data; after the test it only receives aggregated training-region counts" | Remove the 2012/2013 ban, keep the holdout regions locked |
| `tools/guardrails.py` | **Frozen** | Add the new workflow to `LOCK_SCAN_ALLOW` (otherwise `check_locked_downloads` reports an error) | Change `LOCKED_SNPP_START/END`, `assert_download_allowed` and `locked_download_reason` |
| `config/settings.yaml` | **Frozen** | No change | Change `splits.locked_snpp_years` |
| `.claude/hooks/guard.py` | No | No change (its rules come from `guardrails.py`) | No change |
| `tests/test_guardrails.py` | No | No change | Change the assertions around lines 35 and 51–58 |
| `harmonization/download.py` | No | No change | Change the year range for `viirs-snpp` (currently from 2014) |
| `harmonization/grid.py` | No | No change | No code change, but the `locked` status changes with the settings |
| `.github/workflows/grader.yml` | **Frozen** | No change | No change |
| `harmonization/final_test.py` | **Frozen** | No change; only its counting functions are called | No change |
| `results/`, `results/expected/` | Partly frozen | Add hash files for the new version; old files unchanged | Same |
| `docs/execution-plan.md` section 4, `docs/preregistration.md` | The latter was finalized through the S01 process | Leave the original text; add a note pointing to this ADR | Same |

## How to accept it (when implementing)

1. The SHA256 of the 2012 and 2013 annual archives fetched in the cloud must match `results/final-test/locked-data-sha256.txt`. If not, stop and ask a person.
2. In the new data, each training region's observed total per year must equal the total recorded by the grader (`V` in `total_bias` in `results/final-test/scores.json`, for example 42,767 for California in 2012, counting only the months usable at grading).
3. `results/final-test/`, `results/submission.parquet` and Release `v1` do not change by a single byte.
4. `tools/guardrails.py check` and `pipeline.py check` pass.

## What must change along with it once approved

- **Data**: the `source` rules, intervals (observed months have no model interval), the source count table, the front-end JSON, `region_totals`, `docs/data-interface.md`.
- **Anomaly cases**: the 6 real-data cases may change; decide whether to save a separate copy or bump the version (`docs/anomaly-cases.json`).
- **Web page**: all "withheld" and "blind-test years" wording and the calendar divider in `web/src/series.js`, `web/src/main.js` and `web/src/methods.js`, and `web/test/series.test.mjs`.
- **Global version**: `global-v1` has the same estimated period (273,712 training cells × 23 months, about 6.3 million rows). This proposal does not cover it; doing it would need a separate version.
- **Documents**: limitation 2 in `docs/data-card.md`, limitation 4 in `reports/validation.md`, `docs/ai-usage.md`.

## Recommendation

**Choose B + U1**: replace values only, no retraining, with cloud aggregation. Reasons:

- The scores are completely unaffected, and the grading records can be used to cross-check the new data.
- This machine's lock can stay, keeping changes minimal.
- The blind test is this project's strongest evidence and is not worth giving up for 23 more months of training data (option C).

**On timing**: if there is no time before the competition, the submitted version can stay as it is (option A) with no problem at all; the current state is honest and fully documented. Do not change red lines a day or two before the competition just to save time.

## Status

**Awaiting human confirmation.** A person must decide: A, B or C; with B, U1 or U2; and when to do it. After deciding, a person commits the `[unfreeze]`. Related: ADR 0009 item 1 (still "awaiting human confirmation" in `PROGRESS.md`).
