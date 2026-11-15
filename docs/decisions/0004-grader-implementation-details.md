# 0004 Implementation details of the grader (S07)

## Background

The pre-registration (`docs/preregistration.md`) fixed the metrics and the aggregation, but writing the code turned up a few details it does not cover. Once these details are written into `prepare.py`, `evaluate.py` and `final_test.py`, they are frozen with the code, so they are recorded here for a person to confirm. All of the choices below were made **before** seeing any model score. While debugging S07, M1s and QM were trial-run on the validation windows only to confirm that the code runs end to end; the code was not changed because of the scores (see "Disclosure").

## Options and recommendations (each item is the recommended approach and has been implemented this way)

1. **Which cell-months are usable**: the label sensor (S-NPP) is `complete`, and every MODIS input sensor in orbit (Aqua, Terra) is also `complete`. Reason: if the input is missing some days, the estimate will be too low and not comparable with the label. Effect: Terra is partially missing in 2016-02, so that month takes no part in training or scoring (the auxiliary window excludes 1 of 24 months, and the main training period loses 1 month). The alternative is to look only at the S-NPP status, but that would let months with incomplete inputs slip in.
2. **Scoring rectangles**: the regional stage uses only rectangles with `set = demo` (200 per training region, 600 in total). 25 GFED rectangles happen to lie entirely within training regions; they are not counted, because otherwise extra scoring units such as "SHAF" would appear and break the "equal weight per region" aggregation. Stage G (global) passes `rect_sets=("demo", "gfed")` when calling, without changing the frozen code. The final test also uses only demo rectangles: Test 1 uses the training-region rectangles and Test 2 the holdout-region rectangles.
3. **Aggregation details**:
   - MALE: first average over rectangle-months within each "region × calendar year", then take the equal-weight mean; a unit with no samples with V ≥ 10 is skipped. `male_all` uses the same aggregation.
   - Zero-hotspot share, error for 1–9 hotspots: computed over all rectangle-months in the window pooled together (the pre-registration did not say to compute them per unit).
   - Total bias: uses the totals for the whole region (all cells, not rectangles), reported by region × year; the summary gives the mean absolute bias across units.
   - Seasonal correlation: for each region, use the mean regional totals for the 12 calendar months within the window and compute the Pearson correlation between the predicted and observed curves; the summary gives the mean across regions.
   - Block resampling: each of the two windows resamples "region × year" units with replacement and computes the MALE difference, then the two windows are averaged with equal weights; 2000 times, seed 7.
4. **What predict() gets**: the cell indices (`lat_idx`, `lon_idx`) plus the MODIS features in `config/features.json`. No VIIRS columns, month strings, years or region names. The cell indices are provided because M1s by design uses each cell's own ratio (the proposal's "Candidate models"); they are not in `features.json`, and **the S10 LightGBM may not use them as features**. Needs a person to confirm: whether cell indices count as a banned input like "region name". We think not, because M1s needs them in the first place, and CI checks only the feature list.
5. **Final test (`final_test.py`)**:
   - The answer key is built the same way as the training labels: with the frozen `ingest.normalise`, `clean.clean` (standard products only, so no NRT mask is needed) and `grid.aggregate`, keeping only the cells of the six regions, months 2012-02 to 2021-06.
   - The `locked` status this machine assigns to 2012/2013 S-NPP is replaced in the cloud by the real status from the FIRMS missing-data list.
   - If the answer sheet is missing any usable cell-month, the run exits with an error. No results are written on error, so it does not count as "having taken the test once".
   - Stability-interval coverage: when the answer sheet has `rs_*` resampling columns, sum them by "region × month", take the 5%–95% quantiles, and check whether the observed value falls inside the interval. The calibration factor must be determined before the freeze using only the validation windows, and is written into the answer sheet's Parquet metadata as `interval_scale`. When `lo_90`/`hi_90` columns are present, cell-level coverage is reported as well.
   - Agreement of anomaly levels: the reference set is the observed values of the same rectangle and the same calendar month in the other usable years within 2012-02 to 2021-06; it requires at least 8 reference years and a reference median ≥ 10.

## Disclosure

While debugging S07, M1s (λ = 20) and QM were run on both validation windows, with combined MALE over both windows of about 0.377 and 0.463 respectively. After that, the grader code changed in only three places: the regional stage uses only demo rectangles (item 2; the reason was wrong aggregation units, unrelated to scores), a fix for two read-only-array errors, and a fix for an error on empty units. None of these changes affects the comparison between M1s and QM.

## Status

Confirmed: qiuxue-yee, 2026-11-03 (agreed to the freeze after looking over the grader code; the details in this record are frozen together with the code).
