# 0006 Implementation details of LightGBM and the AI experiment loop (S10)

## Background

Task card 3-model and plan section 5 set out the first LightGBM version's settings, the experiment budget and "an improvement of more than 1 standard error", but do not cover the details below. Items 1–7 below were all fixed **before** running the experiment loop. Item 8 lists two approaches that were **deliberately not taken** after seeing the first version's scores.

## Options and recommendations (items 1–7 implemented as recommended)

1. **What data Optuna tunes on**: inside each `fit()`, the earliest 12 months of the training table serve as internal validation (consistent with the backward direction), with the frozen grader's MALE on those 12 months as the objective. **The validation windows are not looked at**. Validation-window scores are used only to decide whether to keep or discard an experiment. The alternative is to let Optuna optimize the validation score directly, but that amounts to tuning parameters thousands of times on the validation set, and the selected result would be optimistic.
2. **Number of trees**: early-stop on the internal split (Tweedie or Poisson deviance), then retrain on the whole training table with the same number of trees (proposal B4).
3. **Monotonic constraints**: Aqua and Terra hotspot counts are monotonically increasing; features derived from hotspot counts (for example the sum of the two satellites, or logs) also get the constraint.
4. **Thread count fixed at 8**: tests showed that 8 threads and 16 threads give different results (with the same thread count, results are bit-for-bit identical). For reproducibility it is fixed at 8. "Class is starting" only lowers the process priority and does not change the thread count.
5. **Keep rule**: an experiment must pass every guardrail in pre-registration section 4, items 3–4 (relative to M1s λ = 20, checked separately on both windows) to be eligible to be kept. It is kept if its improvement over the current best version (`bootstrap_diff`) exceeds 1 standard error. Before the first keep, the "current best version" is M1s. "30 consecutive runs without a keep" is counted by this rule. Whether LightGBM is finally selected is still judged by all conditions in pre-registration section 4 (S11).
6. **Experiment runner and branch**: a new `harmonization/autoexp.py` calls only the frozen grader code and does not change the grader, the data or the splits. Each experiment's `harmonize.py` is saved verbatim as `harmonization/variants/E###.py` on the `exp/lightgbm` branch; kept versions also update `harmonize.py` on that branch. The branch lives in a separate worktree (`../inspiratio-exp`), so the main directory never switches branches. The full results of each experiment go in `experiments/` in the data directory.
7. **The default method stays unchanged for now**: `harmonize.fit()` remains M1s until S11 decides by the selection rule. LightGBM is `fit_lgb()`, and can also be called through `evaluate --method lgb`.

8. **Two approaches not taken, needing a person's decision**:
   - **LightGBM with M1s as an offset** (log(M1s estimate) as init_score): M1s's per-cell ratios come from training-period VIIRS, which amounts to putting "cell index + VIIRS information" into the model; it is also a mix of M1s and M3, which the plan does not include. **Not done**.
   - **Per-cell MODIS climatology features** (the MODIS mean over several months for the same cell): this needs grouping by cell index, and the prediction would depend on which months are passed in. This is a gray area; **not done**.

## Disclosure

Before this record was written, the first version (the settings in items 1–7, without Optuna) was trial-run once on both validation windows, at that time with 16 threads, giving a combined MALE of 0.229 over both windows (M1s 0.377); after switching to a fixed 8 threads it was recorded as experiment E000, at 0.231. It badly failed the zero-hotspot guardrail: among zero-hotspot rectangles the share with Ĥ ≥ 1 was 94%, versus 6% for M1s. The rules in items 1–7 were not changed for the sake of scores after this.

## Status

Items 1–7: recommended approach, implemented, **awaiting human confirmation**. Item 8: recommended not to do, **awaiting human confirmation**.

Update (2026-11-04): the user authorized the AI to judge the technical details of the experiments and the wrap-up itself (the user's words are in ADR 0007, relayed through the S00 session), so items 1–8 are carried out as recommended above and treated as settled. The freeze thresholds and the red lines are not affected.
