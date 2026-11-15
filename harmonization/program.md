# S10 AI-driven automated experiments: program.md

> Written following the proposal's "AI-driven automated experiment loop / program.md template", with this project's specific rules added (`docs/decisions/0006`).

# Goal
Lower the combined validation MALE over both windows output by `evaluate.py` (lower is better), without worsening the share of positive estimates on samples with zero VIIRS detections,
the error for 1–9 hotspots or the regional total bias (the tolerances in pre-registration section 4, items 3–4, relative to M1s λ = 20).

# What you may change
Only `harmonization/harmonize.py` (the `LGB` configuration, the `DERIVED` derived features, `fit_lgb()` and its helpers).
`fit()` receives the training table with true VIIRS values; `predict()` receives only `prepare.feature_table()`: the cell indices plus
the MODIS features in `config/features.json`.
Current starting point (E000): LightGBM, Tweedie objective (variance_power 1.3), monotonically increasing constraint on the Aqua and Terra hotspot counts,
31 leaves, at least 50 rows per leaf, learning rate 0.05, deterministic mode, seed 42, 8 threads.

# Hard rules
- Do not modify `prepare.py`, `evaluate.py`, `final_test.py`, the configuration files or the data splits.
- Do not use year, region name, cell indices (`lat_idx`, `lon_idx`) or any VIIRS information as features; derived features may only be computed from
  columns in `features.json`.
- Keep the monotonically increasing constraint on the MODIS hotspot counts.
- The number of trees is determined only on the earliest 12 months inside the training table (backward direction); Optuna tunes numeric parameters only on this internal split
  and does not look at the validation windows.
- The thread count is fixed at 8 (results depend on the thread count); during class, only lower the priority (`--low`).
- Each experiment states a one-sentence hypothesis and is run with `uv run python -X utf8 -m harmonization.autoexp run --hyp "..."`,
  which records it in `harmonization/experiments.csv` and commits it to the `exp/lightgbm` branch.
- Keep rule: pass every guardrail, and improve on the current best version by more than 1 standard error (block resampling).
- Budget: at most 150 experiments or 8 hours; stop after 30 consecutive runs without a keep.
- Make only structural changes to LightGBM; leave numeric parameters to Optuna. No models outside the plan (CNNs, pixel-level models, M1s hybrids and so on).

# Directions worth trying
- Handling zeros: the estimate when neither the cell itself nor its neighbors have MODIS hotspots (the guardrail metrics are most sensitive to this)
- FRP distribution features: median, 75th percentile, share below 10 MW
- Mean pixel size, or hotspot counts binned by pixel size
- Sum of MODIS hotspots in surrounding cells
- Share of night-time hotspots
- Tweedie variance_power between 1.1 and 1.9; Poisson objective
- Shallower trees and larger leaves to reduce overfitting
- Terra features are unstable after 2020 (item 7 of `reports/findings.md`); try removing them

# Background
VIIRS has smaller pixels, no orbital gaps near the equator, and sees more clearly at oblique angles, so it counts more hotspots.
The gap varies with viewing angle, latitude and fire type.
