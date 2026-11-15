# 0010 S13: implementation details of the validation report

## Background

S13 on task card `5-report` requires completing validation items 1–7 of plan section 3 and drawing 6 core figures. Items 1, 2, 3, 5 and 7 of section 3 were already computed by the frozen grader code in S08–S11 (`reports/scores-v1.json`, `reports/scores-s10.json`, `results/final-test/scores.json`); S13 only summarizes them and does not recompute. Item 4 (the GFED plausibility check) and item 6 (the era-shift investigation) are new. Pre-registration sections 6 and 8 give only the principles; neither the task card nor the plan specifies the methods below. All of them were fixed **after the test scores came out**, but they only describe the data and the model and **do not change the model, the data, the splits or any reported score**. Code: `harmonization/validation.py`; numbers: `reports/validation.json`.

## 1. Era-shift investigation (pre-registration section 8)

- **Rows**: cell-months in the training regions, 2002-07–2011-12 (the old era; Aqua starts in 2002-07) versus 2014-01–2021-12 (the new era), where both MODIS are complete months and there is at least one MODIS hotspot. Cell-months with no hotspots have identical inputs (count 0, everything else null), so the classifier cannot tell their era and they do not affect the model's estimate (the two-stage model estimates 0 for them); including them would only pull the AUC toward 0.5. The same is done for the holdout regions as a supplement: it uses only MODIS inputs and involves no holdout-region VIIRS, which the red lines allow.
- **Inputs**: the 18 inputs the frozen model actually uses (`inputs` in `results/freeze.json`), with none removed.
- **Classifier**: LightGBM binary classification with fixed parameters (31 leaves, at least 200 rows per leaf, learning rate 0.05, 300 trees, feature subsampling 0.8, seed 42, deterministic mode), no tuning.
- **Cross-validation**: 5 folds by calendar year (years sorted and assigned in turn, so every fold contains years from both eras).
- **Main number = the mean of the 5 fold AUCs**. The "pooled AUC" computed by combining the predictions of the 5 models comes out lower (the proportion of the two eras differs between the folds' training sets, so the baseline level of the predictions shifts with it); both are recorded in the JSON, and the report uses the mean.
- **Diagnostics (only for finding causes, not for changing the model)**: the AUC of each input on its own; the AUC with only Aqua inputs, only Terra inputs, and only latitude and month; and a **control**: the same classifier separating 2002–2011 from 2022–2026 (years with known Terra and Aqua orbit drift), which shows that the classifier can detect a real shift when there is one.

## 2. GFED plausibility check (pre-registration section 6)

- **Only 2003–2016 can be used**: the GFED4.1s 2017–2023 beta files in the data directory contain only emissions (`emissions`), not `burned_area`. 2000–2002 are not complete Aqua years and are not used.
- **Metric**: for each region and year, "hotspot count ÷ GFED burned area (km²)". The harmonized series uses dataset v1's regional monthly totals (2003–2013 are model estimates, 2014–2016 S-NPP observations); direct stitching uses Aqua (before 2012) and S-NPP (from 2014).
- **Observations for 2012–2013**: this machine has no S-NPP for these two years. The pre-registration says only "data on the same basis as the blind-grading results" may be used: the grading results contain the observed total V per year for the training regions (counting only the months the grader judged usable). Which months the grader used is worked out from the answer sheet's estimates (summing the answer sheet's estimates month by month to match the annual total H the grader reported; 10 months in 2012, 12 months in 2013), and burned area is summed over those months only.
- **Plausibility check only**: not used to select or tune the model. The holdout regions' numbers are also in the JSON, but every month there is a model estimate, so they cannot test the period around 2012; the report uses only the training regions.
- **Comparison with the literature**: the plan's example is "VIIRS counts about 70% more than MODIS in the tropics". We could not verify the original source of this number or its basis (pixel counts, fire area or overpass counts). This project's ratio is 375 m pixel counts versus 1 km pixel counts, a different basis (already pointed out in item 1 of `reports/findings.md`), so only a qualitative comparison is made, not a numeric one.

## 3. Data sources for the core figures

- **Figure 2 (evidence from the test years)**: this machine has no VIIRS for the test period (red line 1), so only the "region × year" observed totals and estimated totals from the grading results can be used. The monthly comparison is in supplementary figure S2 (validation windows 2014–2017, for which this machine has VIIRS).
- **Figure 4 (model explanation)**: uses the frozen evaluation version (= the production version, ADR 0009 item 1) retrained on the 2014-01–2021-06 training table (bit-for-bit the model used for the answer sheet). For hotspot count, FRP and pixel area, observations are "binned by decile, comparing the observed and modeled VIIRS/Aqua ratios"; this is a fit on the training data and shows only what the model learned, not its accuracy. A partial dependence that changes only the hotspot count would create impossible inputs such as "more fire days than hotspots", so it is not used. Latitude uses partial dependence (changing only latitude, other inputs unchanged), specifically to show the "latitude as a region label" problem.
- **Figure 5 (the full series)**: plots dataset v1's regional monthly totals and the calibrated regional intervals directly (ADR 0008 section 5), without recomputing them.

## Status

Decided and carried out by the AI under the user's authorization (technical details judged by the AI, ADR 0007 item 5), 2026-11-04. **Awaiting human confirmation** (a look-over is enough; it does not block later stages): item 1, using the mean 5-fold AUC as the main number; item 2, GFED only through 2016; item 2, no numeric comparison with the literature value.
