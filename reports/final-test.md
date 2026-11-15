# Final test scores (S11, external blind grading)

> The scores were computed in the cloud by the GitHub Actions grading workflow `grader.yml`, and are kept as is in `results/final-test/` (`scores.json`, `summary.md`, `provenance.txt`, SHA256 of the locked data). Answer sheet commit `674b3f5`; the `final-test` tag was pushed by a person; run record: https://github.com/team-inspiratio/inspiratio-space-apps-2026/actions/runs/41768696897 ; results commit `742547e` (2026-11-04 03:50 UTC). The test is taken only once; scores are only reported, and the model is not changed afterwards.
> Model: LightGBM E028 (two-stage), selected by pre-registration section 4, retrained after freezing on the training regions over 2014-01–2021-06 (`docs/decisions/0008`, `results/freeze.json`). The comparison methods are fitted on the same training table.

## 1. Main score (MALE, lower is better)

| Method | Test 1: training regions 2012-02–2013-12 | Test 2: holdout regions 2012-02–2021-06 |
|---|---:|---:|
| **LightGBM E028 (final model)** | **0.258** | **0.644** |
| M1s (λ = 20) | 0.332 | 0.857 |
| QM | 0.431 | 0.866 |
| M0 direct stitching | 1.814 | 2.263 |

How much better E028 is than the comparisons ("year × region" block resampling 2000 times; positive means E028 is better; no p-values):

| Comparison | Test 1 | Test 2 |
|---|---|---|
| M1s | 0.075 ± 0.010 (95% interval 0.057 to 0.096), 22% lower | 0.213 ± 0.019 (0.174 to 0.250), 25% lower |
| QM | 0.173 ± 0.013 (0.150 to 0.198) | 0.222 ± 0.020 (0.182 to 0.261) |

- **Test 1 agrees with the validation set**: on the validation set E028 was 21.8% lower than M1s; on Test 1 it is 22% lower. Predicting back to 2012–2013 did not get worse (0.258, even lower than the validation set's 0.295).
- **Test 2 is much worse for both methods**: E028 0.644, M1s 0.857, about 2.5 times the training regions. E028 is still better than M1s, and the interval does not cross 0. The S10 review worried that "latitude is used as a region label, so the holdout regions might reverse the result"; it did not reverse, but the overall error is indeed large.

## 2. MALE by region

| Region | E028 | M1s | QM |
|---|---:|---:|---:|
| California (Test 1) | 0.282 | 0.387 | 0.490 |
| Córdoba (Test 1) | 0.298 | 0.361 | 0.474 |
| Southern Africa (Test 1) | 0.193 | 0.249 | 0.328 |
| Northern Australia (Test 2) | 0.321 | 0.424 | 0.446 |
| India's Ganges Plain (Test 2) | 0.470 | 0.767 | 0.798 |
| Central Siberia (Test 2) | **1.142** | 1.381 | 1.353 |

- Northern Australia (tropical savanna, similar to southern Africa) is almost as good as the training regions.
- Central Siberia (boreal forest, an ecosystem absent from the training regions, at a latitude far outside them) has the largest error, above 1.1 for every method. The estimates there are not reliable and should not be applied directly in the global stage.

## 3. Auxiliary metrics

| Metric | Test 1: E028 / M1s | Test 2: E028 / M1s |
|---|---|---|
| Share with Ĥ ≥ 1 among zero-hotspot rectangle-months | 8.1% / 4.2% | **11.9% / 2.9%** |
| Share with Ĥ ≥ 5 among zero hotspots | 3.6% / 3.2% | 9.6% / 2.5% |
| Mean absolute error for 1–9 hotspots | 4.03 / 5.68 | **9.72 / 4.87** |
| Region × year total bias (mean absolute) | 4.8% / 9.3% | 18.4% / 34.1% |
| Seasonal correlation (mean) | 0.999 / 0.996 | 0.972 / 0.929 |

- **Test 1**: the zero-hotspot share is 3.9 percentage points higher than M1s (the pre-registered tolerance is 5), the error for 1–9 hotspots is smaller, and the total bias for every region and year is within ±9% (M1s: California 2012 +18%).
- **Test 2's weaknesses**: where fires are rare, E028 is more likely than M1s to estimate hotspots "out of nothing" (zero-hotspot share 11.9% versus 2.9%, beyond the 5-percentage-point tolerance used for model selection), and in months with few hotspots its error is twice M1s's. By the guardrail standard used for model selection, these two items **fail** on Test 2. They are only reported; the model is not changed.
- **Totals**: in the holdout regions E028 is generally **too low**: about −22% to −35% per year in India's Ganges Plain, about −14% to −45% in central Siberia; northern Australia is within ±5% in 2012–2019, and −13% and −23% in 2020–2021 (consistent with Terra's drift after 2020, item 7 of `reports/findings.md`). M1s's bias is larger (central Siberia about −36% to −65%, northern Australia about −23% to −33%).

## 4. Validation by use case: agreement of anomaly levels (Cohen's κ)

| | Test 1 | Test 2 |
|---|---:|---:|
| E028 | 0.686 | 0.534 |
| M1s | 0.612 | 0.415 |
| Samples (rectangle-months) | 11,090 | 47,878 |

How well "high / normal / low" judged from the harmonized data agrees with the same judgment from real VIIRS: "good" in the training regions (0.69) and "moderate" in the holdout regions (0.53). Better than M1s in both tests. The confusion matrices are in `scores.json`.

## 5. Coverage of the stability intervals (pre-registration section 7, nominal 90%)

| | Test 1 | Test 2 |
|---|---:|---:|
| Region × month, raw intervals | 37.9% (66 of them) | 12.9% (333 of them) |
| Region × month, after multiplying by the calibration factor 5.37 | **95.5%** | **55.9%** |
| Cell × month, raw intervals | 64.7% | 73.5% |

- By the rule fixed before seeing scores in ADR 0008 section 5: the raw coverage of both tests is below 80%, so **the calibrated coverage counts**, and the regional intervals of the S12 production version are also multiplied by 5.37.
- Test 1 reaches 95.5% after calibration, meeting the nominal level. Test 2 reaches only 55.9%: the error in the holdout regions is mainly a systematic underestimate (section 3), which variation across training years cannot capture, so the intervals are clearly too narrow for new regions. On the web page, intervals for the holdout regions (and future new regions) must not be read as "90% intervals".
- Cell-level coverage looks higher than region-level coverage because a large number of cell-months have an estimate and an observation of 0, so the interval [0, 0] happens to cover them.

## 6. Conclusions

1. The selected E028 beats M1s and QM on both tests; the improvement on Test 1 (22%) agrees with the validation set, with no sign of overfitting the validation set.
2. Moving to ecosystems and latitudes outside the training regions (Test 2), the error becomes 2.5 times that of the training regions, the zero-hotspot and low-hotspot metrics are worse than M1s, and totals are 20% to 35% too low (except northern Australia). The claim that "the conversion learned from 3 training regions generalizes directly to the globe" **does not hold**; the global stage (G) needs more training regions, or the report must mark new regions as low confidence.
3. The stability intervals represent only the variation from changing training years. After calibration they are adequate in the training regions, but not in new regions.

## 7. This machine and process disclosures

- This machine has never had S-NPP data for 2012 or 2013 or VIIRS for the holdout regions; the answer key was generated only on GitHub's machines. Remaining risk: this machine has internet access (blocked by three layers: the hook, pre-commit and CI; `AGENTS.md`).
- The first time a person was asked to push the tag, it did not get pushed (no tag existed locally or on the remote), so it was pushed again. The workflow ran only once; see the run record above.
- The S10 experiments were cut short for time reasons (37 experiments, ADR 0007).
