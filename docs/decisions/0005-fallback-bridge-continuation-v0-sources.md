# 0005 Fallback models, bridge, continuation, and the source rules for dataset v0 (S08–S09)

## Background

Task card 2-baselines asks for QM, the Terra→Aqua bridge, the NOAA-20→S-NPP continuation test, and dataset v0 generated with M1s. The plan and the pre-registration say only what to do, not the details below. Items 1–3 were fixed **before** seeing any scores (written into the code and run once in S08). The pass criterion in item 4 was proposed only **after seeing the test results**, so it is only a recommendation and must be decided by a person.

## Options and recommendations (implemented as recommended)

1. **QM (quantile mapping)**: one mapping per calendar month, fitted on the cell-months of the three training regions pooled together, Ĥ = F_V⁻¹(F_A(A)). Ties in A take the mid-rank (for example, all cells with A = 0 map to the midpoint of the "zero segment" of the V distribution). When A exceeds the maximum in the training period, scale up as Ĥ = max of V × A ÷ max of A, with no cap. Fitting separately by region is also possible, but new regions (the holdout regions) can only use the pooled version, so only this one pooled variant is built, to avoid cherry-picking results.
2. **λ for M1s**: choose from {0, 5, 20, 50, 100} the value with the lowest combined MALE over both validation windows; ties go to the smaller λ. Result: **λ = 20** (combined MALE 0.3766; λ = 50 gives 0.3771, a very small difference). The bridge and the continuation use the same λ, with no separate tuning.
3. **Terra→Aqua bridge**:
   - Test version: fitted on 2003–2010 and checked against real Aqua over 2011–2019. Only years with a stable Terra/Aqua ratio are used (item 7 of `reports/findings.md`).
   - Production version (used for dataset v0): fitted on the training regions over 2003-01 to 2019-12.
   - Holdout-region cells took no part in the fit and use the training regions' pooled ratio by calendar month.
4. **Pass criterion for the NOAA-20→S-NPP continuation (awaiting a person's decision)**: fitted on the training regions over 2018-04 to 2021-12 and tested on 2022-01 to 2026-10. Results (section 5 of `reports/scores-v1.md`):
   - Median monthly total bias: California +3.1%, Córdoba −0.3%, southern Africa +1.1%;
   - Region × year bias: 13 of 15 within ±10%; California 2023 is +15%;
   - Day and night separately give similar results; the 90th percentile is slightly higher at night.

   Suggested pass criterion: the median monthly total bias of each region within ±5%, and at least 80% of "region × year" units within ±10%. By this criterion the test counts as "passed". But the criterion was proposed after seeing the results, so **a person must decide whether to accept it**; until then, the web page must not claim that the NOAA-20 segment is "continuous".
5. **Source of each cell-month in dataset v0 (the `source` field)**:
   - `snpp`: training regions, complete S-NPP months (2014-01 to 2026-10; this machine has no data for 2012–2013); observed values are used directly;
   - `noaa20_scaled`: when S-NPP is partially or entirely missing in a training region but NOAA-20 has a complete month, the converted NOAA-20 whole-month value is used, never added to S-NPP. The conversion ratio is fitted on the data in the training regions over 2018-04 to 2026-10 where both satellites have complete months;
   - `m1s_aqua`: in other months, when Aqua has a complete month, the M1s estimate is used;
   - `m1s_terra_bridge`: when Aqua is not complete (2000-11 to 2002-07, and months with missing Aqua data) but Terra is, Terra is first bridged to Aqua and then M1s is applied; the web page marks this as low confidence;
   - when neither MODIS is complete, compute with Aqua anyway (or the bridged Terra if there is no Aqua), and also set `input_complete = false`.
   - The holdout regions use M1s estimates throughout. The reason is that holdout-region VIIRS was already dropped at import and may only be used after the blind grading.
   - M1s is fitted on the training regions over 2014-01 to 2021-06 (the same range used for the post-freeze retraining), with λ = 20. The production version waits for S12 and will use 2012-02 to 2021-06.
   - v0 has no uncertainty intervals; they are added in S12 with resampling.

6. **Terra bridge in the holdout regions (awaiting a person's decision)**: while building v0, it turned out that the training regions' pooled Terra→Aqua ratio (about 2.5×) does not suit the holdout regions. Northern Australia's local Aqua/Terra ratio is only about 1.1–1.3× (2003–2006), so the estimates for northern Australia over 2000-11 to 2002-06 are about 1.5–2× too high: the 2001 estimate is 12.7× Terra, while the 2003–2006 Aqua segment is only about 7.5×. A likely cause is that the daily cycle of fires differs from place to place (Terra passes in the morning, Aqua in the afternoon).
   - Option A (what v0 does now): following the proposal's "the locked region gets no local ratio estimate", use the training regions' pooled ratio and mark it as low confidence on the web page.
   - Option B: fit a local Terra→Aqua ratio using only the holdout regions' own MODIS (2003–2019, when both Terra and Aqua exist). This does not touch VIIRS at all and does not affect Test 2 (the test period 2012–2021 needs no bridge), but it does not match the literal wording of that sentence in the proposal.
   - Recommendation: use B for the S12 production version and explain it in the report; keep A for v0 for now.

## Status

Items 1–3 and 5: recommended approach, awaiting human confirmation. Items 4 and 6: **awaiting a person's decision**.
