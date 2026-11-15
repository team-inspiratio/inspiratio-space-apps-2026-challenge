# 0009 S12: the production model and how the final series is built

## Background

Task card S12 and the proposal's "Producing the final series" require: retrain the production version on all overlap data in the training regions from 2012-02 to 2021-06; use S-NPP observations for 2012-02 to 2026-10; add source flags; give stability intervals. Writing the code ran into the points below, which the plan leaves unclear or which conflict with the red lines. Items 1–4 were all fixed after the S11 answer sheet was sealed and **before seeing the test scores**.

## 1. Training range of the production version (inconsistent with the plan; awaiting human confirmation)

- **Conflict**: the plan says the production version uses 2012-02 to 2021-06. But red line 1 says this machine **never** downloads S-NPP for 2012 or 2013, and the grading workflow does not bring the answers back to this machine either. So this machine cannot do it.
- **Approach**: production version = the evaluation version frozen in S11 (training regions 2014-01 to 2021-06, with the parameters and numbers of trees in `results/freeze.json`). The advantage is that the test scores are directly the production version's scores. Retraining in S12 reproduced the answer sheet's `est_final` bit for bit.
- **Effect**: the series for the training regions from 2012-02 to 2013-12 is a model estimate (`model_aqua`), not observations; the acceptance check "the S-NPP segment matches the observations" can only cover 2014-01 to 2026-10.
- **The alternative**: after the test, a person lifts the lock on these two years (a person must change the frozen guardrails and the AGENTS.md red line), downloads the data, retrains, and replaces these 23 months with observations. The AI cannot do this.

## 2. Terra-only months (2000-11 to 2002-09, and months with missing Aqua)

- The model's inputs include Aqua features, and these months have no Aqua. Approach: build Aqua inputs from Terra (hotspot counts and neighbor hotspot counts multiplied by the cell's Terra→Aqua M1s ratio; the other Aqua features copied from Terra), then feed them into the model. The source is flagged `model_terra_bridge`, shown as low confidence on the web page.
- **How it was chosen**: only on the two validation windows, real Aqua was replaced by inputs built from Terra, and two approaches were compared (`series_v1.py terra-check`; results in `s12/terra_check.json` in the data directory):

  | Approach | main | aux | Combined MALE |
  |---|---:|---:|---:|
  | Model + real inputs (reference) | 0.300 | 0.289 | 0.295 |
  | **Model + Aqua inputs built from Terra (adopted)** | 0.461 | 0.460 | **0.460** |
  | v0 chain: Terra bridge → M1s | 0.499 | 0.494 | 0.496 |
  | M1s + real inputs (reference) | 0.393 | 0.360 | 0.377 |

  "Model + inputs built from Terra" is better in both windows, so it is adopted. With only Terra the error is much larger than with Aqua (0.46 versus 0.29), which is the basis for the low-confidence flag.
- The bridge ratio is fitted on months from 2003-01 to 2019-12 where both MODIS are complete (Terra drifts after 2020, item 7 of `reports/findings.md`), with λ = 20.

## 3. Terra bridge in the holdout regions

Following the recommendation in ADR 0005 item 6, option B is used: the bridge ratio is fitted on each region's own MODIS (the six regions fitted together, with each cell shrunk toward its region's ratio), without touching VIIRS at all. The training regions' ratios are the same as in v0. The user authorized the AI to decide technical details (ADR 0007 item 5), so it is carried out as recommended.

## 4. Source flags and intervals

- `source`: `snpp` (complete S-NPP months in the training regions, observed values), `noaa20_scaled` (S-NPP incomplete but NOAA-20 complete, converted value; the continuity criterion still awaits a person's decision, ADR 0005 item 4), `model_aqua` (model estimate), `model_terra_bridge` (only Terra, low confidence).
- `nrt`: the value comes from near real-time data (VIIRS from 2026-08, MODIS from 2026-09; `sp_last_day` in `config/settings.yaml`).
- `input_complete = false`: the sensors used have missing days that month, and the value may be too low. This flag is what the plan calls "missing"; in the six regions there is no month with no input at all.
- Stability intervals: the same 100 whole-year resamples as in S11 (parameters and numbers of trees fixed); the cell-level `lo_90`/`hi_90` are the 5%/95% quantiles (reflecting only the effect of the training years). For region × month intervals, each resample is first summed into a regional total and then the quantiles are taken; per ADR 0008 section 5, since at least one of the two tests has raw coverage below 80%, they are multiplied by the calibration factor 5.37 around the estimate. Observed months and NOAA-20 months have no model interval (both bounds equal the estimate).
- For areas drawn on the front end: the cell-level estimates from the first 20 resamples (non-zero values only) are saved separately as `resamples20_v1.parquet` (the proposal's "Producing the final series").

## Status

Items 2–4 were decided by the AI under the user's authorization. Item 1 is inconsistent with the plan, forced by the red lines, and **awaits human confirmation**: keep it as it is now (recommended), or have a person unlock and fill in 2012–2013.
