# S10 model review: top 3 LightGBM (E028, E018, E032)

Reviewer: a review subagent with a fresh context (pre-registration section 4, item 5; plan section 5).
Script: `uv run python -X utf8 -m harmonization.model_review` (about 3 minutes, 8 threads).
All numbers are in `reports/model-review.json`, and the figures in `reports/figures/s10-*.png`.
Only the two validation windows (main, aux) and the 3 training regions were used. No test data was touched, and no holdout-region VIIRS was read.

## Conclusions (read this first)

| Experiment | Leakage review | Combined MALE | Blocks S11 from selecting it? | Main caveats |
|---|---|---:|---|---|
| E028 | **Pass** | 0.2947 | No | Latitude mainly acts as a "region label"; main zero-hotspot Ĥ≥1 has only 1.0 percentage point of headroom left |
| E018 | **Pass** | 0.2950 | No | Same as above; 0.7 percentage points of headroom |
| E032 | **Pass** | 0.2954 | No | Same as above; 0.5 percentage points of headroom (tightest of the three); the parameters tuned in the two windows differ the most |

- The code of the three experiments differs only in the feature list; everything else is identical line by line. The rerun scores match `experiments.csv` exactly.
- The three differ in score by at most 0.0007, while the standard error of the difference from M1s is about 0.015. The three are effectively equally good. By the rule, the lowest is selected, which is E028.
- No leakage was found: the model's inputs are only the columns in `config/features.json` and derived columns computed from them; the number of trees and Optuna use only the earliest months of the training table; predict() sees only the feature table.
- **A risk to write into S11 and the report**: latitude is an allowed input, but the latitudes of the 3 training regions do not overlap at all, so the model uses latitude as a label for "which region this is" (section 5). This is not leakage and does not violate the pre-registration, so it does not block selection. But when the model is applied to new regions (the holdout regions, the globe), its performance may get clearly worse. Test set 2 (the holdout regions) tests exactly this, and S11 should not change the model at the last minute because of it (that would be changing the method after seeing the validation scores).

## 1. Leakage checks

### 1.1 Results of reading the code

| Check | Result |
|---|---|
| Differences between the three experiments and E028's source | Only the `drop` and `derived` lines in `LGB` (checked by the script with difflib) |
| Model inputs | `lgb_inputs()` first calls `prepare.feature_table()` (which rejects VIIRS, month and year columns), then drops `lat_idx` and `lon_idx` |
| Derived features (used only by E018) | `modis_count = aqua_count + terra_count`, `log_aqua = log1p(aqua_count)`; both use only feature columns and are monotonically increasing |
| Number of trees | Early stopping on the earliest 24 months of the training table, then retraining on the whole training table with the same number of trees |
| Optuna | The objective is the frozen grader's MALE on the earliest 24 months of the training table (plus a guardrail penalty), and the reference M1s is also fitted only on the training table; the validation windows are not looked at |
| `region` column | Used only for internal scoring (the per-region MALE penalty) and the internal M1s; it does not go into the model |
| predict() | Only calls `models_predict(feats)`, where `feats` is exactly the feature table given by the grader |
| Monotonic constraints | Aqua and Terra hotspot counts (and E018's derived counts) are monotonically increasing; kept |

A minor issue (does not affect results): the configuration says `zero_rule` is `cell_and_nbr`, but the two-stage `models_predict()` does not use it. Suggest explaining this in the report, or removing this item later, to avoid misreading.

### 1.2 The models actually trained

| Experiment | Window | Training months | Internal holdout months | Trees clf/reg (rerun = JSON) | Features | Disallowed features | Prediction change after shuffling cell indices |
|---|---|---|---|---|---:|---|---:|
| E028 | main | 2016-01..2021-06 | 2016-01..2018-01 | 534/592 = 534/592 | 18 | None | 0 |
| E028 | aux | 2018-01..2021-06 | 2018-01..2019-12 | 184/224 = 184/224 | 18 | None | 0 |
| E018 | main | 2016-01..2021-06 | 2016-01..2018-01 | 561/846 = 561/846 | 22 | None | 0 |
| E018 | aux | 2018-01..2021-06 | 2018-01..2019-12 | 262/189 = 262/189 | 22 | None | 0 |
| E032 | main | 2016-01..2021-06 | 2016-01..2018-01 | 488/592 = 488/592 | 18 | None | 0 |
| E032 | aux | 2018-01..2021-06 | 2018-01..2019-12 | 218/284 = 218/284 | 18 | None | 0 |

- main's internal holdout runs to 2018-01 because one month in 2016–2017 is unusable (missing data), so "the earliest 24 usable months" spans one extra month. It is still entirely within the training table.
- `feature_name()` lists: E028 = the 20 original features minus the two no-detection flags; E032 = minus the two fire-day counts; E018 = all 20 plus `modis_count` and `log_aqua`. The classifier and the count model have the same list. None includes `lat_idx`, `lon_idx`, `month`, `year`, `region`, `snpp*` or `noaa20*`.
- "Shuffling cell indices": after randomly shuffling `lat_idx` and `lon_idx` in the feature table, the predictions do not change at all (maximum difference 0), which shows the model really does not use the cell indices.

## 2. Feature-group ablation (E028 only)

Method: using E028's tuned parameters for each window, with Optuna turned off, retrain with one group of features removed each time (the number of trees is still early-stopped on the earliest 24 months of the training table).
E028 itself already drops the no-detection flags, so for that group the row means "added back".
Reference M1s: combined 0.3766; zero-hotspot Ĥ≥1 limit main 0.106 / aux 0.115; Ĥ≥5 limit 0.072 / 0.085; 1–9 hotspots MAE limit 7.40 / 8.67.

| Group removed | Combined MALE | Change | main | aux | Ĥ≥1 main/aux | Ĥ≥5 main/aux | 1–9 MAE main/aux | Guardrails |
|---|---:|---:|---:|---:|---|---|---|---|
| (E028 itself) | 0.2947 | — | 0.3003 | 0.2891 | 0.096/0.079 | 0.029/0.037 | 4.20/5.70 | Pass |
| Aqua hotspot count | 0.3042 | +0.010 | 0.3058 | 0.3025 | 0.097/0.078 | 0.027/0.039 | 4.14/5.81 | Pass |
| All Terra inputs | **0.3671** | **+0.072** | 0.3815 | 0.3527 | 0.075/0.087 | 0.042/0.065 | 5.25/5.67 | Fail: southern Africa > 1.05×M1s in both windows |
| FRP statistics | 0.2943 | −0.000 | 0.2986 | 0.2899 | 0.107/0.093 | 0.036/0.039 | 4.33/6.05 | Fail: main Ĥ≥1 over by 5.1 percentage points |
| Pixel area | 0.2938 | −0.001 | 0.2975 | 0.2900 | 0.097/0.081 | 0.027/0.050 | 4.07/5.87 | Pass |
| Night share | 0.3025 | +0.008 | 0.3029 | 0.3021 | 0.101/0.083 | 0.037/0.037 | 4.43/6.29 | Pass |
| Fire days | 0.2961 | +0.001 | 0.3048 | 0.2874 | 0.101/0.080 | 0.033/0.039 | 4.24/5.84 | Pass |
| Neighbor hotspot counts | 0.2962 | +0.002 | 0.3071 | 0.2852 | 0.104/0.081 | 0.045/0.048 | 4.56/6.47 | Pass |
| No-detection flags (added back) | 0.2936 | −0.001 | 0.3011 | 0.2861 | 0.098/0.088 | 0.028/0.038 | 4.14/5.83 | Pass |
| Latitude | **0.3759** | **+0.081** | 0.3799 | 0.3719 | 0.129/0.110 | 0.054/0.054 | 5.91/7.04 | Fail: main Ĥ≥1; aux MALE > M1s; two regions in aux |
| Calendar month | 0.2896 | −0.005 | 0.3047 | 0.2745 | 0.122/0.104 | 0.039/0.047 | 4.62/5.66 | Fail: main Ĥ≥1 over by 6.5 percentage points |

How to read it:

- The standard error of the difference from M1s is about 0.015, so changes within ±0.01 are essentially noise.
- **The model really depends on only two groups: latitude and the Terra inputs**. Removing either makes MALE worse by 0.07–0.08 and fails the guardrails.
- The Aqua hotspot count has the highest importance, but removing it costs only 0.010, because the Terra hotspot count, the Aqua fire days and the neighbor counts can stand in for it.
- FRP and calendar month contribute almost nothing to MALE, but they help the classifier decide "fire or no fire"; without them the zero-hotspot guardrail fails.
- Pixel area, fire days, neighbor counts, no-detection flags: removing them or adding them back makes no real difference.
- Depending on Terra is a risk: item 7 of `reports/findings.md` says Terra's orbit drifts after 2020, and the training table includes 2020–2021. The validation windows are in 2014–2017 and do not reflect this.

## 3. Prediction-relationship plots (E028, main window validation rows)

Figures:

- `reports/figures/s10-pd-estimate.png`: partial-dependence curves of the estimate (set one input to grid values, leave the others unchanged, take the mean).
- `reports/figures/s10-pd-ratio.png`: estimate / Aqua hotspot count. The blue line is the partial dependence; dots are the binned predicted ΣĤ/ΣA; squares are the binned actual ΣV/ΣA.
- `reports/figures/s10-importance.png`: gain importance (classifier and count model shown separately).

The hotspot-count and pixel-area curves use only rows with Aqua > 0 (pixel area is defined only when there is fire). Latitude and calendar month use all rows. 6000 rows are sampled with a fixed seed.

| Input | Shape of the partial dependence | Plausible? |
|---|---|---|
| Aqua hotspot count | Rises monotonically (1 → 300 hotspots, mean estimate 36 → 559); the estimate per Aqua hotspot falls from about 36 to 1.9 | The monotonic constraint works. The binned predicted and actual ratios almost coincide |
| Aqua pixel area | The ratio is almost flat: 5.13 at 1.0 km², 4.77 at 5.4 km² (down 7%) | **Opposite to the proposal's expectation** (expected: the larger the area, the higher the ratio). But the real data does the same: the binned actual ratio falls from 6.30 (1.0 km²) to 4.65 (2.7 km²), with 4.89 in the largest bin. The model follows the data. Its gain is only 0.1%, and removing it makes no difference, so the model hardly uses this input; it is neither leakage nor a spurious relationship |
| Latitude | Step-shaped: flat outside the training regions, with jumps at the edges of training regions or in the gaps between them; a few very narrow spikes within regions | Looks like a region label, not a physical effect; see section 5 |
| Calendar month | Low in May–July (25.5), high in November (35.9) | The 3 regions are in two hemispheres with different fire seasons. This curve is a mix of the three regions' seasons, not a uniform physical law |

Gain importance (main window, share of total gain in %):

| Input | Classifier (fire or no fire) | Count model |
|---|---:|---:|
| aqua_count | 44.1 | 68.1 |
| aqua_frp_median | 15.4 | 0.1 |
| aqua_nbr_count | 11.9 | 0.8 |
| aqua_frp_p75 | 11.2 | 0.6 |
| lat | 5.2 | 0.6 |
| terra_nbr_count | 3.5 | 1.2 |
| cal_month | 1.9 | 0.5 |
| terra_count | 1.4 | 5.5 |
| aqua_fire_days | 1.1 | 20.0 |
| the other 9 | each ≤ 1.1 | each ≤ 0.9 |

Note: latitude has only 5% of the gain, yet removing it costs the most. A small gain does not mean unimportant; it acts mainly by "shifting each region's overall level".

## 4. Stability across the two windows (all three checked)

### 4.1 MALE

| Experiment | main | aux | Difference | California main/aux | Córdoba main/aux | Southern Africa main/aux |
|---|---:|---:|---:|---|---|---|
| M1s | 0.3933 | 0.3600 | −0.033 | 0.443/0.431 | 0.430/0.369 | 0.306/0.280 |
| E028 | 0.3003 | 0.2891 | −0.011 | 0.310/0.281 | 0.318/0.316 | 0.273/0.270 |
| E018 | 0.3021 | 0.2878 | −0.014 | 0.324/0.277 | 0.310/0.324 | 0.272/0.263 |
| E032 | 0.3020 | 0.2888 | −0.013 | 0.308/0.286 | 0.322/0.320 | 0.276/0.261 |

- All three models beat M1s in both windows and in every region; the per-region case closest to M1s is E028 aux southern Africa (0.270 vs 0.280, 0.96×; the guardrail limit is 1.05×), and all the others are at most 0.94×.
- The main–aux difference is smaller than M1s's, which shows the models are not good in only one window by chance.

### 4.2 Parameters tuned in the two windows (main / aux)

| Experiment | variance_power | num_leaves | min_data_in_leaf | lambda_l2 | feature_fraction | p_fire | Trees clf | Trees reg |
|---|---|---|---|---|---|---|---|---|
| E028 | 1.22 / 1.19 | 21 / 27 | 447 / 369 | 1.89 / 0.84 | 0.80 / 0.84 | 0.31 / 0.33 | 534 / 184 | 592 / 224 |
| E018 | 1.17 / 1.22 | 19 / 21 | 471 / 447 | 1.76 / 1.89 | 0.93 / 0.80 | 0.32 / 0.31 | 561 / 262 | 846 / 189 |
| E032 | 1.56 / 1.22 | 20 / 21 | 446 / 447 | 0.02 / 1.89 | 0.88 / 0.80 | 0.29 / 0.31 | 488 / 218 | 592 / 284 |

- The classification threshold p_fire is very stable (0.29–0.33). The number of leaves and the minimum samples per leaf are also close.
- E032's variance_power (1.56 vs 1.22) and lambda_l2 (0.02 vs 1.89) differ a lot between the windows, yet the scores are similar, which shows the objective is very flat around here.
- main's number of trees is 2–4 times aux's. main's training table has 66 months and aux's only 42, and early stopping naturally stops later on the larger table. When S11 freezes the model, the number of trees must be determined the pre-registered way, not by picking one window's value.
- Observation: several parameter sets are exactly identical (for example E028 main = E018 aux = E032 aux). The reason is that Optuna's TPE sampler has a fixed seed and runs only 15 trials, the first 10 of which are the same random starting points, so the experiments often pick the same candidate point. This is not leakage, but it shows that the "tuning" is really choosing among a small fixed set of candidates.

## 5. Latitude: a physical effect or a region label?

Background: E022 (E016 without latitude) has a combined MALE of 0.366, much worse than E016's 0.294. The latitudes of the 3 training regions do not overlap at all: Córdoba −35..−28, southern Africa −18..−8, California 32.5..42. So latitude alone identifies the region.

I ran three tests (E028, no retraining, changing only the latitude of the validation rows):

| Test | Combined MALE | Change | Notes |
|---|---:|---:|---|
| Unchanged | 0.2947 | — | |
| Each row's latitude replaced by its region's median | 0.3319 | +0.037 | Keeps only "which region", removing latitude differences within a region |
| The three regions' median latitudes rotated (California → Córdoba's latitude, and so on) | 0.5606 | +0.266 | Other inputs within the region unchanged; only the region's identity is swapped; Córdoba main goes from 0.318 to 0.924 |
| (Reference) latitude removed and retrained | 0.3759 | +0.081 | Section 2 |

Partial-dependence curve (`s10-pd-estimate.png`, bottom left):

| Latitude band | Min–max of the mean estimate |
|---|---|
| Córdoba (training) | 24.4–32.8 |
| Southern Africa (training) | 27.6–29.9 |
| California (training) | 22.7–28.8 |
| Northern Australia (holdout, −20..−10) | 27.6–29.9 (same as southern Africa) |
| India's Ganges Plain (holdout, 24..32) | Fixed at 25.0 (falls in the gap between two training regions) |
| Central Siberia (holdout, 55..65) | Fixed at 23.2 (copies the value at California's northern end) |

Verdict: **mainly region identification, not a physical effect.**

1. The curve is step-shaped. The jumps fall at the edges of training regions, or at latitudes with no training data at all (for example near 0° and −21°). A physical effect (scan geometry, orbit overlap) should vary smoothly with latitude and depend roughly only on the absolute latitude. No such pattern is visible here: near −32° the ratio is about 5.8, near +38° about 5.0, near −15° about 5.0.
2. Swapping the regions' identities makes the error shoot up (+0.266). This shows the model depends heavily on "latitude = which region".
3. Latitude within a region also helps (replacing it with the median costs 0.037), but the within-region variation consists of very narrow spikes (near −32° in Córdoba, near 38–39° in California), which look more like memorizing "which latitude band within the region often burns" than smooth viewing geometry.
4. With latitude removed, E022 gets worse in all three regions (main: California 0.311→0.408, Córdoba 0.318→0.394, southern Africa 0.274→0.334), not just in one. Latitude supplies each region's own overall calibration, similar in role to M1s's "region × month" ratio.

What this means for new regions:

- Backward prediction within the training regions (test set 1: training regions in 2012–2013) should be fine, because the regions' identities do not change.
- A new region gets the calibration of "the nearest training region": northern Australia is treated as southern Africa (both are tropical savanna, which may be acceptable); central Siberia is treated as the northern end of California; India's Ganges Plain gets an arbitrary value between two regions. None of these has a physical basis.
- So on test set 2 (the holdout regions), LightGBM's advantage over M1s may shrink or even reverse. For new regions M1s uses the pooled ratio of the three regions, which at least behaves predictably.
- Recommendation (without changing S11's selection rule): state this truthfully in the S11 report; in the global stage (G), do not apply a model trained on three regions directly to places far from the training latitudes unless test set 2 shows that it transfers. Do not remove latitude in S11; that would be changing the method after seeing validation scores.

## 6. Other notes

- The main-window model early-stops and tunes on 2016–2017 (the earliest 24 months of its training table), which is exactly the aux window's validation period. But the aux scores come from aux's own model (trained from 2018-01), so there is no leakage.
- The zero-hotspot guardrail (main, Ĥ≥1) is the only tight one: limit 0.106; E028 0.096, E018 0.099, E032 0.101. After S11 retrains on 2014-01–2021-06, this share may move. Per the pre-registration, selection looks only at the validation set, so this is just a note.
- From 2000-11 to mid-2002 there is only Terra, no Aqua. The model depends most on the Aqua hotspot count; how to handle this period is outside the scope of this review, but it must be checked before S12 generates the series (M1s has the same problem).
