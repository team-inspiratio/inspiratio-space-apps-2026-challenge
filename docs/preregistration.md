# Pre-registration (S01)

> Written on 2026-11-03 and committed and frozen **before any model is fitted and before any validation score is seen**. Basis: sections 2–4 of the execution plan and the proposal's "Validation framework".
> Files frozen together with this one: `config/settings.yaml` (grid, time, quality control, splits, seeds), `config/regions.json` (training and holdout regions), `config/rectangles.csv` (scoring rectangles), `.github/workflows/grader.yml` (external grading), `tools/guardrails.py` (guardrails).
> Any later change requires a person to write `[unfreeze]` in the commit message with the reason, and must be disclosed in the report.

## 0. Basic units and data

- 0.25° cells (aligned with GFED4.1s) × calendar months (UTC), 2000-11 to 2026-10.
- Four raw series: A = Aqua MODIS, T = Terra MODIS (only to fill in before 2002-07), V = S-NPP VIIRS (the target scale), N = NOAA-20 VIIRS (for continuation). In no month are counts from several VIIRS satellites added together.
- Quality control (finalized before modeling): keep only `type = 0`; MODIS confidence ≥ 30; keep nominal and high for VIIRS; merge only duplicate-download records (key: satellite, date, time, latitude/longitude; standard products take priority over near real-time); the near real-time segment has no `type`, so the 0.25° cells where `type = 2` appeared during the standard-product period serve as a static heat-source mask.
- 0 versus missing: a cell-month with no records gets 0 ("no hotspot recorded"); months covered by the official FIRMS missing-data list are marked missing or partially missing and take no part in training or scoring.
- Input features use only MODIS (count, FRP median and 75th percentile, share of low FRP (< 10 MW), mean pixel size, night share, fire days, neighbor counts) plus latitude and month. Year, region name and any VIIRS information are banned (`config/features.json`, checked by CI).

## 1. Data splits (as in plan section 2)

| Purpose | Training | Evaluation | Space |
|---|---|---|---|
| Main validation window | 2016-01–2021-06 | 2014-01–2015-12 | Training regions |
| Auxiliary backward window | 2018-01–2021-06 | 2016-01–2017-12 | Training regions |
| Test 1 (locked) | 2014-01–2021-06 | 2012-02–2013-12 | Training regions |
| Test 2 (locked) | 2014-01–2021-06 | 2012-02–2021-06 | Holdout regions |

- Training regions: California, Córdoba in Argentina, the southern African savanna. Holdout regions: northern Australia, central Siberia, India's Ganges Plain (`docs/decisions/0001`). Bounds are in `config/regions.json`.
- 2012-01 has only some of its days (S-NPP starts on January 20), so it is not used as a complete-month label.
- This machine never downloads S-NPP for 2012 or 2013; holdout-region VIIRS is dropped at import and never written to disk.

## 2. Main metric (plan section 3, item 1)

- Scoring units: the random rectangles in `config/rectangles.csv` (fixed seed 20261103). 200 for each demonstration region and holdout region and 150 for each GFED4.1s basis region, with sides of 1°–5° (in 0.25° steps) and bounds on the 0.25° grid. Rectangles for GFED regions do not touch the holdout regions. A rectangle's value = the sum of the cells inside it (rectangle bounds coincide with cell bounds, so no apportioning by area is needed).
- **Main score = MALE** = mean of |ln(Ĥ+1) − ln(V+1)|, counted only over rectangle-months with a monthly VIIRS count ≥ 10, excluding missing and partially missing months.
- **Aggregation**: first average over rectangle-months within each "region × complete year", then take the equal-weight mean over all "region × year" units. Incomplete years within a window (for example 2012 in Test 1, which has only February–December) are computed over their actual months and still count as one "year" unit.
- Also reported: the MALE over all valid samples (including V < 10), the sample count, and the share excluded because of missing data.
- **Auxiliary metrics** (reported side by side with M1s):
  - Zero hotspots: among rectangle-months with V = 0, the share with Ĥ ≥ 1 and with Ĥ ≥ 5;
  - Low hotspots: mean absolute error |Ĥ − V| for rectangle-months with V of 1–9;
  - Total bias: Σ Ĥ ÷ Σ V − 1, by region and complete year; when Σ V = 0, report the absolute bias;
  - Seasonal shape: by region, the Pearson correlation of the curve of mean values over the 12 calendar months.

## 3. Comparisons and confidence intervals (item 2)

- For the MALE difference between the model and M1s and QM, give a 95% percentile interval and a standard error (the standard deviation of the resampling distribution) from "year × region" block resampling (resampling "region × year" units with replacement, 2000 times, seed `seeds.bootstrap = 7`).
- Overlapping rectangles do not count as independent samples; **no p-values are reported**.

## 4. Selection rule (item 7, using only the two validation windows)

LightGBM is chosen as the final model only if it meets **all** of the following conditions **at the same time**; otherwise the final model is M1s.

1. **Improvement threshold**: the aggregated MALE over the two validation windows (each window first aggregated as in section 2, then the two windows averaged with equal weights) is at least 10% lower than M1s: MALE_LGB ≤ 0.90 × MALE_M1s.
2. **Anti-score-gaming**: the improvement in the previous condition (MALE_M1s − MALE_LGB) exceeds 1 standard error of itself (from the block resampling in section 3).
3. **Neither window may get clearly worse**: looking at each window on its own, MALE_LGB ≤ MALE_M1s; and for each training region in each window, MALE_LGB ≤ 1.05 × MALE_M1s.
4. **Tolerances for the guardrail metrics** (relative to M1s, checked separately on both windows):
   - on zero-hotspot samples, the share with Ĥ ≥ 1 may be at most 5 percentage points higher than M1s, and the share with Ĥ ≥ 5 at most 2 percentage points higher;
   - the mean absolute error on samples with 1–9 hotspots may not exceed 1.10 times that of M1s.
5. **Leakage review** passed: the feature list complies with red line 3; validation results after feature ablation, prediction-relationship plots and importance plots are checked by a review subagent with a fresh context (plan section 5).
6. **Total bias**: for each training region, ±10% is the preset target, **reported only, not a threshold**; if it is not met, say so honestly.

If extension models such as M2 and M5 are built, they are compared with M1s by the same rule, using the validation set only.
Once selected, the model is frozen (features, parameters, number of trees), retrained on 2014-01–2021-06, and then takes the test set once.

## 5. Validation by use case: agreement of anomaly levels (item 3)

- The grading rule follows the proposal's "Anomaly indicators": percentile = 100 × [number less than h + 0.5 × number equal to h] ÷ n; ≥ 90 is labeled "high", ≤ 10 "low", everything else "normal".
- Evaluation: for each rectangle-month in the test period (target month in year y, calendar month c), the reference set = the **observed VIIRS** values of the same rectangle and the same calendar month in the other complete years within 2012-02–2021-06 (the target year itself is not in the reference set).
  - "True" level: the target value is the observed V;
  - "Harmonized" level: the target value is the model estimate Ĥ.
- Because the VIIRS overlap period is only about 9 years, this check requires at least 8 reference years (the product rule is ≥ 10; it is relaxed here in advance and explained in the report); only rectangle-calendar-months whose reference-set median is ≥ 10 are included; missing months are excluded.
- Report the 3-class confusion matrix and the unweighted Cohen's κ (separately for Test 1 and Test 2), side by side with M1s. **Reported only, not a model-selection threshold**.

## 6. Plausibility check against an independent reference (item 4)

- Use GFED4.1s burned area (0.25° monthly, 2000–2023, beta version from 2017) to compute the annual series of "hotspot count ÷ burned area" for the training regions, and check whether it is stable across 2012 (in the harmonized series); compare with values from the literature (for example, VIIRS counting about 70% more than MODIS in the tropics).
- This is only a plausibility check and is **not used to tune or select models**. The 2012–2013 VIIRS part is plotted only after the freeze, using data on the same basis as the blind-grading results.

## 7. Uncertainty (item 5)

- Stability intervals: year-block resampling of the training years with retraining, 100 times (`seeds.resampling = 2026`), taking the 5%–95% quantiles of regional totals.
- Report the **actual coverage** of the intervals on the test set (nominal 90%). If coverage is below 80%, apply one proportional calibration to the regional-aggregate intervals using validation-set residuals (the calibration factor is determined from the validation windows only), and report the calibrated coverage on the test set; the calibration method is fixed here and will not be changed after seeing the test results.

## 8. Era-shift investigation (item 6)

- Use a classifier that sees only the model's input features (LightGBM, 5-fold cross-validation grouped by year) to distinguish cell-months from 2002–2011 and from 2014–2021; report the AUC and the most important features, and analyze the causes (orbit or product changes, land-use or fire-regime changes). **Features are not deleted to lower the AUC**.

## 9. External blind grading (plan item 4.4)

- `.github/workflows/grader.yml` is frozen in this same commit; it runs only when a person pushes the `final-test` tag, and the test can be taken only once.
- Answer-sheet convention: `results/submission.parquet` (generated on this machine from MODIS inputs only after the model is frozen; its hash is written into the frozen manifest and committed). One row per "cell × month", covering every cell in Test 1 (training regions, 2012-02–2013-12) and Test 2 (holdout regions, 2012-02–2021-06):
  - `lat_idx`, `lon_idx` (0.25° cell indices, consistent with the repository's grid code), `month` (`YYYY-MM`);
  - `est_final` (estimate from the selected model), `est_m1s`, `est_qm`, `est_m0` (where applicable);
  - `lo_90`, `hi_90` (stability interval; optional at cell level, while the grading code sums the resampling columns for region level).
- The grading code `harmonization/final_test.py` is written and frozen in S07; it reuses the frozen cleaning and gridding code, builds the answer key from the annual archives downloaded in the cloud, and computes all metrics according to sections 2, 4, 5 and 7 of this file. At S01 it does not exist yet; the calling convention is already written into the workflow.
- Test scores are only reported; the model is not changed and retested afterwards.

## 10. Outside the scope of this pre-registration

- Sensitivity analyses with 0.5°/1° grids and extensions such as M2/M5 are done only after S15 and if quota remains, and their results are labeled separately as exploratory analyses.
