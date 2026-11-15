# 0008 S11: model selection, how the freeze is done, and the answer sheet

## Background

Task card `4-freeze-test` requires selecting the model by pre-registration section 4, writing the frozen manifest, retraining the frozen model and sealing the answer sheet. The pre-registration says "Once selected, the model is frozen (features, parameters, number of trees), retrained on 2014-01–2021-06", but does not say exactly how the parameters and the number of trees are determined (each of the two validation windows tunes its own set, see section 4.2 of `reports/model-review.md`), nor how the calibration factor for the stability intervals is computed. Items 2–6 below are these details; all were fixed **before** generating the answer sheet and will not change after the test scores come out.

## 1. Selection result: LightGBM E028 (the outcome of the pre-registered rule, not a judgment call)

| Condition (pre-registration section 4) | Threshold | E028 | Result |
|---|---|---|---|
| ① At least 10% better | Combined MALE ≤ 0.90 × 0.3766 = 0.3389 | 0.2947 (21.8% lower) | Pass |
| ② Improvement of more than 1 standard error | 0.0820 > standard error | Standard error 0.0155, 95% interval −0.113 to −0.053 | Pass |
| ③ Neither window worse | Each window ≤ M1s; each region ≤ 1.05 × M1s | main 0.3003 vs 0.3933, aux 0.2891 vs 0.3600; highest per region 0.96× (aux, southern Africa) | Pass |
| ④ Zero hotspots Ĥ≥1 | At most 5 percentage points above M1s | main +4.0 (9.6% vs 5.6%), aux +1.4 | Pass (main only 1 percentage point from the limit) |
| ④ Zero hotspots Ĥ≥5 | At most 2 percentage points higher | Lower than M1s in both windows | Pass |
| ④ Error for 1–9 hotspots | ≤ 1.10 × M1s | main 4.20 vs 6.72, aux 5.70 vs 7.88 | Pass |
| ⑤ Leakage review | Review with a fresh context | `reports/model-review.md` | Pass |
| ⑥ Total bias (reported only) | Each training region ±10% | See section 7 | — |

The numbers come from `reports/scores-s10.md`; S11 reran both validation windows with the frozen code and the scores are bit-for-bit identical (section 3).

## 2. What is frozen

- **Code**: `harmonization/harmonize.py`. It differs from E028's exact source (SHA256 `033a2ea6…`) in only one place: the default `fit()` changes from M1s to `fit_lgb()`. After the freeze, `fit_lgb` behaves exactly like E028.
- **Features**: `config/features.json` is frozen as is. E028 actually uses 18 inputs (dropping `terra_no_detection` and `aqua_no_detection`); the list is in `inputs` in `results/freeze.json`.
- **Configuration**: `harmonize.LGB`: two-stage (a "fire or no fire" classifier + a Tweedie count model), monotonically increasing in the Aqua/Terra counts, learning rate 0.05, 15 Optuna trials (TPE, seed 42, tuned only on the internal split of the training table), the earliest 24 months of the training table for internal early stopping, 8 threads, deterministic mode.
- **Parameters and number of trees**: see section 3; the numbers are in `results/freeze.json`.

## 3. How the parameters and number of trees are determined (decided by the AI, under the user's authorization)

- **Method**: run the same frozen procedure `fit_lgb` on the 2014-01–2021-06 training table (3 training regions, usable months): the earliest 24 months (2014-01–2015-12) serve as internal validation, Optuna chooses the parameters and early stopping sets the number of trees, then retrain on all 90 months with the same number of trees. The resulting parameters and number of trees are written into `results/freeze.json` before the answer sheet is generated, and all resampling afterwards uses this one set without further tuning.
- **Reason**: the two validation windows' scores measure exactly this procedure (each window tunes, early-stops and retrains on its own training table). Copying the main or aux window's parameters would amount to picking one of the two sets; moreover, the number of trees changes with the length of the training table (main, 66 months → 534/592 trees; aux, 42 months → 184/224 trees), so carrying them over to a 90-month table does not correspond.
- **Approach not chosen**: retrain directly with the main window's parameters and number of trees, for the reason above.
- **Reproduction check**: S11 reran both validation windows with the frozen code; the parameters, numbers of trees and scores are bit-for-bit identical to E028 in S10.

## 4. Stability intervals (pre-registration section 7)

- With the parameters and number of trees fixed, resample the training years as **whole years** with replacement (2014–2021, 8 year blocks in total; 2021 has only January–June), seed `seeds.resampling = 2026`, 100 times; after each retraining, predict every row of the answer sheet and store the predictions as `rs_000`–`rs_099`.
- The grading code sums by "region × month", takes the 5%/95% quantiles, and checks the share of observed totals that fall inside the interval (nominal 90%). The cell-level `lo_90`/`hi_90` are the 5%/95% quantiles of the same resamples, and the grader also reports cell-level coverage.
- This interval reflects only "how much the estimate would change with a different set of training years" and does not include the random variation of the observations themselves, so the raw coverage is expected to be far below 90%.

## 5. Calibration factor (pre-registration section 7, ADR 0004 item 5)

- On both validation windows, use exactly the same method: each window's own E028 parameters and number of trees (reproduced verbatim from S10), resample the training years as whole years 100 times, predict the validation months, and get "region × month" intervals.
- Calibration factor s = the smallest value for which 90% of the region-month observed totals across both windows combined fall within [e − s·(e − q05), e + s·(q95 − e)] (e is the frozen model's estimate; the formula is the same as in the grading code `final_test.coverage`, in steps of 0.01). It is written into the answer sheet's Parquet metadata as `interval_scale`.
- **Reporting and production rule (fixed now, before seeing scores)**: if the raw "region × month" coverage of both Test 1 and Test 2 is ≥ 80%, the raw coverage is what counts, and the S12 production version uses the raw intervals; if either is below 80%, the calibrated coverage counts for both tests, and the S12 production version's regional intervals are multiplied by the same factor (widened around the estimate). Both raw and calibrated numbers are written into the report.

## 6. The answer sheet `results/submission.parquet`

- Rows: all training-region cells × 2012-02–2013-12 (Test 1) + all holdout-region cells × 2012-02–2021-06 (Test 2), not filtered by S-NPP status (this machine does not know the real status of the locked years; they are excluded at grading time).
- Columns: `lat_idx`, `lon_idx`, `month`, `est_final` (E028), `est_m1s` (λ = 20), `est_qm`, `est_m0`, `lo_90`, `hi_90`, `rs_000`–`rs_099`. All four methods are fitted only on the same 2014-01–2021-06 training table, and predictions use only MODIS inputs.
- Before sealing, the frozen grading function `final_test.grade` was run end to end on a fake answer key (labels = 4 × Aqua count, containing no VIIRS at all) to confirm that all rows and columns are present and the calibration factor can be read.
- The generating script `harmonization/freeze.py` is frozen together with the answer sheet and `results/freeze.json`.

## 7. Result numbers (before sealing)

- **Frozen model (evaluation version)**: training regions, 2014-01–2021-06, 347,456 usable cell-months. The parameters chosen by the frozen procedure are the same as for the main window (variance_power 1.225, num_leaves 21, min_data_in_leaf 447, lambda_l2 1.89, feature_fraction 0.80, p_fire 0.309; the reason is that the TPE seed is fixed and there are few candidate points, see section 4.2 of the review notes); numbers of trees: classifier 766, count model 970. Code commit `738fd99`.
- **Reproduction**: both validation windows rerun with the frozen code give MALE 0.3003 / 0.2891 and numbers of trees 534/592 and 184/224, bit-for-bit identical to S10; predictions from retraining on the full table with the frozen numbers of trees are exactly the same as `fit_lgb`'s.
- **Total bias (item ⑥, reported only)**: main window California −9.2%, Córdoba −3.8%, southern Africa +2.8%; aux window +8.1%, +4.6%, +4.4%. All 6 are within the ±10% target.
- **Calibration factor**: on the validation set the raw intervals cover only 34% of region-months (main 40%, aux 28%); `interval_scale` = 5.37, which widens coverage to 90.1% combined (main 91.7%, aux 88.4%).
- **Answer sheet**: 596,032 rows (Test 1: 89,792; Test 2: 506,240), 85.7 MB; SHA256 in `results/freeze.json` and `config/frozen-manifest.json` (the hash in the manifest is computed with the guardrails' uniform line-ending rule and differs from the hash of the raw bytes; both are recorded). The grading code ran successfully on the fake answers: all metrics and coverages were computed for both tests.

## 8. Known risks (to be written into the report)

- **Latitude acts as a region label** (section 5 of `reports/model-review.md`): the 3 training regions do not overlap in latitude, so a new region gets the conversion of the training region nearest in latitude. Test 2 (holdout regions) tests exactly this, and LightGBM's advantage over M1s may shrink or even reverse. Per the pre-registration, the model is not changed before the test.
- The model depends on Terra inputs, and Terra drifts after 2020 (item 7 of `reports/findings.md`).
- The zero-hotspot guardrail in the main window is only 1 percentage point from its limit.
- S10 was cut short for time reasons, with 37 experiments in total (ADR 0007).

## Status

Item 1 is the direct outcome of the pre-registered rule. Items 2–6 were decided and carried out by the AI under the user's authorization (ADR 0007 item 5: "technical details are judged by the AI itself"), on 2026-11-04, before generating the answer sheet.
