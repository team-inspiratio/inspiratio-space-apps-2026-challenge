# PROGRESS: Project progress

> The machine-readable status block sits between the two comment lines below, in YAML. Read it at the start of every session, change it when you claim a card, and update it after every completed stage.
> `tests/test_progress.py` checks its format.

<!-- STATUS:BEGIN -->
```yaml
current_card: docs/sessions/5-report.md        # next (or current) task card
status: ready                           # ready | in_progress | blocked | done
claimed_by: ""                          # claimant's name; empty means unclaimed
claimed_at: ""                          # claim time, ISO 8601 UTC, e.g. 2026-11-03T08:00:00Z
last_pushed_stage: S12                  # last stage completed and pushed
last_pushed_at: 2026-11-04
branch: feat/data-harmonization
data_release: dataset-v1                # final dataset v1 (S12); processed inputs are in data-v0, milestone A in milestone-a; SHA256 in the handover notes
next_step: "Start a new session for task card 5-report: S13 validation report (D1, including the final test reports/final-test.md and the era-shift investigation), S14 delivery, S15 milestone B"
needs_human:
  - "Please look over: the final test scores reports/final-test.md (Test 1 is 22% better than M1s; in the holdout regions the error is 2.5 times the training regions' and totals are 20–35% too low, which must be considered before the global stage G)"
  - "Tell the front end: the final dataset pre-release dataset-v1 + docs/data-interface.md (v1: source names changed to model_*, lo_90/hi_90 and nrt added)"
  - "Awaiting human confirmation: the S12 production version keeps the frozen 2014-01–2021-06 model, and 2012–2013 in the training regions uses estimates, because this machine never has S-NPP for those two years (docs/decisions/0009 item 1)"
  - "Please look over: the S10 review notes reports/model-review.md (conclusion: all top 3 pass the leakage review; risk: with only 3 training regions, latitude acts as a region label, so the holdout regions may do worse; Test 2 will check this)"
  - "Awaiting a person's decision: the pass criterion for the NOAA-20 continuation (docs/decisions/0005 item 4; the criterion was proposed after seeing the test results)"
  - "Recorded: the Terra bridge in the holdout regions uses the local MODIS ratio (option B), as recommended in ADR 0005 item 6, decided by the AI under the user's authorization (docs/decisions/0009 item 3)"
  - "Awaiting human confirmation: QM details, choice of λ, bridge years, v0 source rules (docs/decisions/0005 items 1–3 and 5)"
  - "Recorded: implementation details of the S10 LightGBM and experiment loop (docs/decisions/0006), decided by the AI under the user's authorization"
  - "Recorded: the S10 budget cut, deadline and remedy reruns were the user's decisions (docs/decisions/0007)"
  - "Tell the front end: the milestone-a pre-release + docs/data-interface.md are available (comment already left on PR #2)"
  - "GitHub CLI login: can be skipped on this already-logged-in computer; when taking over on another computer, first run gh auth login --web (needed to download the Release data)"
```
<!-- STATUS:END -->

## Sessions overview

| Session | Task card | Stages covered | Status |
|---|---|---|---|
| 0 | (repository setup) | S00 | ✅ done |
| 1 | [`1-data`](docs/sessions/1-data.md) | S01–S06 | ✅ done |
| 2 | [`2-baselines`](docs/sessions/2-baselines.md) | S07–S09 (milestone A) | ✅ done |
| 3 | [`3-model`](docs/sessions/3-model.md) | S10 | ✅ done |
| 4 | [`4-freeze-test`](docs/sessions/4-freeze-test.md) | S11–S12 | ✅ done |
| 5 | [`5-report`](docs/sessions/5-report.md) | S13–S15 (milestone B) | ⏭ next |
| G | [`G-global`](docs/sessions/G-global.md) | Global rerun | not started (after S15) |

## Stage table

| Stage | Content | Status | Completed | Key numbers | commit |
|---|---|---|---|---|---|
| S00 | Environment, guardrails, CI, self-describing files | ✅ done | 2026-11-03 | CI green; 17 pytest tests pass | 3dcf808 |
| S01 | Pre-registration (settings, holdout regions, random rectangles, grader.yml) | ✅ done | 2026-11-03 | 6 regions (3 training + 3 holdout); 3300 rectangles; 5 files frozen | 7d1aa0c |
| S02 | Download (annual archives, 2026 via API, missing-data list, GFED) | ✅ done | 2026-11-03 | 46 annual archives (about 9 GB, locked years skipped); 918 satellite-days from the API; 24 years of GFED; 178 missing days; 4 days × 3 sources compared: every annual-archive row is in the API | 7df072f |
| S03 | Import (stream to Parquet, drop holdout-region VIIRS) | ✅ done | 2026-11-03 | 46 annual archives + 6 API sources; for every file, raw rows = written + dropped for holdout regions (`docs/ingest-ledger.csv`); VIIRS archives deleted | 84abd8c |
| S04 | Cleaning | ✅ done | 2026-11-03 | 529 million → 444 million rows; type −6.1%, low confidence −9.7%, NRT mask −0.18%, 222 duplicates; spot check of 20 found no wrongful deletions (`reports/cleaning.md`) | 94669f0 |
| S05 | Gridding and features | ✅ done | 2026-11-03 | Totals conserved (sum of cell counts per satellite = cleaned points); dense regional table 2.616 million rows; 20 features | 0ec693d |
| S06 | Data health check (A5) | ✅ done | 2026-11-03 | S-NPP/Aqua annual ratio about 4.6–10; NOAA-20/S-NPP median 0.98–1.00; Terra/Aqua drops sharply after 2020 | 6603ac1 |
| S07 | Grader (prepare, evaluate) | ✅ done | 2026-11-03 | Dummy methods: always 0, combined MALE 5.90; MODIS as is, 1.79; SHA256 identical over two runs (`reports/judge-check.md`) | |
| S08 | Fallback models M0, M1s, QM; bridge and continuation | ✅ done | 2026-11-03 | Combined MALE over both windows: M1s (λ=20) 0.377, QM 0.463, M0 1.795; Terra→Aqua→M1s chain 0.522; NOAA-20 continuation median monthly total bias −0.3% to +3.1% (`reports/scores-v1.md`) | |
| S09 | ★Milestone A: dataset v0, front-end export, pre-release | ✅ done | 2026-11-03 | 2.616 million cell-months: 554,000 S-NPP observed, 47,000 NOAA-20 converted, 1.82 million M1s, 197,000 Terra bridge; pre-release `milestone-a`, SHA256 of all 9 files checked after download | |
| S10 | LightGBM and AI experiments | ✅ done | 2026-11-04 | 37 experiments (E000–E036; budget cut and wrapped up early per ADR 0007); best validation MALE: E028 two-stage LightGBM 0.2947, 21.8% lower than M1s (0.3766) (difference −0.082 ± 0.016, 95% interval −0.113 to −0.053), 0.169 lower than QM; all top 3 pass the guardrails and the leakage review (`reports/scores-s10.md`, `reports/model-review.md`) | |
| S11 | Freeze and external blind grading | ✅ done | 2026-11-04 | E028 selected. Test MALE: Test 1 **0.258** (M1s 0.332, 22% lower), Test 2 holdout regions **0.644** (M1s 0.857); κ 0.69 / 0.53; regional interval coverage after calibration 95.5% / 55.9% (raw 37.9% / 12.9%); in the holdout regions the zero-hotspot and low-hotspot metrics are worse than M1s and totals are 20–35% too low (`reports/final-test.md`) | 742547e |
| S12 | Final dataset | ✅ done | 2026-11-04 | Production version = the frozen evaluation version E028 (ADR 0009); 2.616 million cell-months: 554,000 S-NPP observed, 1.817 million model estimates, 197,000 Terra bridge, 47,000 NOAA-20 converted; 100 resampled intervals, regional intervals multiplied by the calibration factor 5.37; acceptance: in the S-NPP segment, 15.19 million points over 426 region-months match the observations one by one; pre-release `dataset-v1` | |
| S13 | Validation report (D1) | ⬜ todo | | | |
| S14 | Delivery | ⬜ todo | | | |
| S15 | ★Milestone B: one-command reproduction, Release v1, merge into main | ⬜ todo | | | |

## Handover notes

### S00 (2026-11-03)

- Branch `feat/data-harmonization` created; draft PR: https://github.com/team-inspiratio/inspiratio-space-apps-2026/pull/2 . The plan is committed unchanged as `docs/execution-plan.md`.
- Environment: `uv` + Python 3.12; dependencies in `pyproject.toml`, lock file `uv.lock`.
- Guardrails: `tools/guardrails.py` (frozen-file hashes, append-only; banned features; downloads of locked years; secrets), shared by the three layers: CI, pre-commit and the Claude hook. The frozen manifest is currently empty; entries start being added in S01.
- Data directory: `D:/inspiratio-data` on this machine (set as `INSPIRATIO_DATA_DIR` in `.env`).
- Note for this machine: uv's default cache directory has a file-system redirection problem on this Windows machine, so the user-level `uv.toml` moves the cache to `C:/Users/ASUS/.uv-cache`. Other machines are not affected.
- The relay drill passed: a new session, given only the repository files, correctly stated the progress, the next card `1-data` and what a person needs to prepare. Based on the drill we added `docs/decisions/` (see its README) and clearer gh login instructions, and changed the Claude hook to locate the repository root with `git rev-parse --show-toplevel` (falling back to `$CLAUDE_PROJECT_DIR` if that fails), so that the hook does not lose track of its script and block every tool when a session changes directory midway.
- **Holdout regions confirmed** (the user, 2026-11-03): northern Australia (savanna), central Siberia (boreal forest), India's Ganges Plain (cropland), each about 10°×10°; see [`docs/decisions/0001-holdout-regions.md`](docs/decisions/0001-holdout-regions.md). S01 writes `config/regions.json` directly on this basis without asking again; the exact bounds are set only from geography and ecology, without looking at any VIIRS. On the same day the user also confirmed extending to global coverage and keeping the main product on the VIIRS scale.

### Session 1 (2026-11-03, qiuxue-yee)

- **Done**: S01–S06 all completed and pushed; CI green. The pre-registration and freeze are in `7d1aa0c`, earlier than any modeling code.
- **Data Release `data-v0`** (pre-release): https://github.com/team-inspiratio/inspiratio-space-apps-2026/releases/tag/data-v0 . Download with `gh release download data-v0 --repo team-inspiratio/inspiratio-space-apps-2026 -D <INSPIRATIO_DATA_DIR>/release/data-v0`, then check against `SHA256SUMS.txt`:

  | File | Rows | SHA256 |
  |---|---:|---|
  | `grid_regions.parquet` (dense table for the demonstration and holdout regions: MODIS features + VIIRS labels) | 2,615,808 | `c9b254b945c8049554cb0fa309edfab1ff7ba8d661ed22897c206e376955623c` |
  | `grid_counts.parquet` (global sparse counts) | 22,944,336 | `f350a062871614e7750084d2300ff7e9a92997efbc860f856f7fb93eec6e7b05` |
  | `grid_month_status.parquet` | 1,248 | `21fa09aa6b354e07395fe437b97147d743306f493b5a13dca18fbc5746c39ab5` |
  | `clean_aqua.parquet` | 69,034,390 | `26312bb94b2d4b910cd22a7634935885da8c46cde2f16458e6ac3393c19d29b7` |
  | `clean_terra.parquet` | 36,272,942 | `6647342f9e5636c4b3e8f6eddacf1c78d7fbff442e86c70deabbdb66584947f3` |

  The cleaned VIIRS point data (about 4.6 GB) is not uploaded, by decision (`docs/decisions/0003`, confirmed).
- **Tips for session 2**:
  - Cell indices in the grid tables: `lat_idx = floor((lat+90)/0.25)`, `lon_idx = floor((lon+180)/0.25)` (counted from the southwest corner); scoring-rectangle bounds lie on the 0.25° grid, and a rectangle's value = the sum of the cells inside it.
  - `*_status` columns: only `complete` may be used for training and scoring (pre-registration sections 0 and 2); `partial` also has counts but must be excluded. The VIIRS columns for the holdout regions are all null.
  - The Terra/Aqua ratio drops sharply after 2020, so the Terra→Aqua bridge can only use years with a stable ratio (item 7 of `reports/findings.md`).
  - Running the guardrails and tests on this machine needs `-X utf8`: `uv run python -X utf8 -m pytest` (`docs/decisions/0002`, confirmed: no unfreezing).
  - The Claude hook wrongly blocks commands whose commit message contains both "locked years" and "download" wording, so don't write commit messages like that; the same applies to code comments (CI scans them).

### Session 2 (2026-11-03, qiuxue-yee)

- **Done**: S07–S09 all completed and pushed. The grader files `prepare.py`, `evaluate.py` and `final_test.py` were frozen after a person looked them over (`e19f26c`); implementation details are in `docs/decisions/0004` (confirmed).
- **Score table v1**: `reports/scores-v1.md`. Combined MALE over both windows: M1s (λ = 20, chosen on the validation set from {0, 5, 20, 50, 100}) 0.377, QM 0.463, M0 1.795; QM is worse than M1s by 0.087 (95% interval 0.074–0.100). The grader checks (dummy methods, reproducibility) are in `reports/judge-check.md`.
- **Milestone A pre-release `milestone-a`**: https://github.com/team-inspiratio/inspiratio-space-apps-2026/releases/tag/milestone-a . Download with `gh release download milestone-a --repo team-inspiratio/inspiratio-space-apps-2026`, then check with `sha256sum -c SHA256SUMS.txt`. Generated by `uv run python -m harmonization.series` (rerunning on the same input gives byte-identical output).

  | File | SHA256 |
  |---|---|
  | `dataset_v0.parquet` | `66c1696d3a1cdc953ebcc4064054263daf973853ef824ee4b2d01b14aeb43ae8` |
  | `region_totals_v0.csv` | `6d5343c520d18164fd31bd7c908d7ecfe88406c7fab472bc3ccea5aec35d1dab` |
  | `data-interface.md` | `6f00419f11c2855c0e9c76f0b2f8c05e375de00e50dbc3c02720571f3363823e` |
  | `<region>.json.gz` × 6 | see `SHA256SUMS.txt` in the Release |

- **Tips for session 3**:
  - Model interface: `fit(train_table) -> predict`, `predict(feature_table) -> estimates`; score with `evaluate.evaluate(fit)` and `evaluate.bootstrap_diff(m1s_result, new_result)`. The table predict gets has the cell indices `lat_idx` and `lon_idx`; **LightGBM may not use them as features**, and features may come only from `config/features.json` (ADR 0004 item 4).
  - M1s baseline: `harmonize.fit_m1s(t, 20.0)`; it is the reference for the selection rule. Only `harmonization/harmonize.py` may be changed.
  - Finding: the Terra bridge segment in the holdout regions (2000-11 to 2002-06) may be 1.5–2× too high (ADR 0005 item 6, awaiting a person's decision). This does not affect model selection in S10.
  - When generating Release files, fix the gzip timestamp and use LF line endings throughout, otherwise the hashes differ between Windows and Linux (`series.py` already does this).

### Session 3 (2026-11-03 to 04, qiuxue-yee)

- **Done**: S10. LightGBM is `fit_lgb()` in `harmonization/harmonize.py`; this file is now exactly the source of the top experiment E028 (its SHA256 matches the E028 row in `experiments.csv`). The default `fit()` is still M1s, to be changed after S11 decides by the selection rule.
- **Experiments**: `harmonization/experiments.csv` (37 rows, each with a one-sentence hypothesis, all metrics, whether it passes the guardrails and whether it was kept); each experiment's source is in `harmonization/variants/E###.py` on branch `exp/lightgbm` (pushed; this machine also has a worktree `../inspiratio-exp`). Runner `harmonization/autoexp.py`; rules in `harmonization/program.md`, ADR 0006 (awaiting human confirmation) and ADR 0007 (the user's decision to speed things up).
- **How it went**: a single LightGBM reaches a combined MALE of 0.23, but it sprinkles small positive estimates over every cell and badly fails the zero-hotspot guardrail (94% versus 6%). E001–E014 tried various zeroing and discounting rules, none of which passed. After the user asked to speed things up, the approach switched to a "two-stage" model: first decide whether there is any fire, and estimate the count only if there is. E016 was the first to pass every guardrail. After that, ablations and derived features were tried around it, all scoring between 0.293 and 0.305. The two closest were rerun with 30 Optuna trials (E035 fails, E036 passes), and by the rule the rerun scores replace the original ones.
- **Top 3** (`reports/scores-s10.md`): E028 0.2947, E018 0.2950, E032 0.2954. All three pass pre-registration section 4, items 1–4, and the review subagent judged that they also pass item 5, the leakage review. The differences among the three are far smaller than the standard error; they are effectively equally good.
- **Tips for session 4**:
  - By the pre-registration, the top experiment **E028** meets items 1–5 and should be selected. What gets frozen is E028's features, parameters (the parameters tuned in each window are in `experiments/E028.json` in the data directory) and number of trees. The numbers of trees tuned in the main and auxiliary windows differ by 2–4×. Retraining uses 2014-01–2021-06; first write down clearly how the number of trees and the parameters are determined, and do not change them after seeing the test results (section 4 of the review notes).
  - **Risk** (section 5 of the review notes): the latitudes of the 3 training regions do not overlap at all, so latitude acts as a label for "which region this is". A new region gets the conversion of the training region nearest in latitude. Test 2 (holdout regions) checks exactly this. **Do not remove latitude before the test because of this**; that would be changing the method after seeing validation results.
  - The model relies heavily on Terra inputs, and Terra drifts after 2020 (item 7 of `reports/findings.md`); this must be stated in the report.
  - In the two-stage setup, `zero_rule` in the configuration has no effect (section 1.1 of the review notes); don't misread the code.
  - Months before Aqua came online in 2002 (Terra only) are outside the S10 evaluation; check them before S12 generates the series.

### Session 4 (2026-11-04, qiuxue-yee)

- **Where S11 stands**: LightGBM E028 was selected by pre-registration section 4 (item-by-item check in section 1 of `docs/decisions/0008`). `harmonize.py` (default `fit()` changed to `fit_lgb`, otherwise identical to E028's source) and `config/features.json` were frozen, then the frozen procedure was retrained on the training regions over 2014-01–2021-06, with 100 whole-year resamples for the stability intervals and the calibration factor set from the two validation windows (5.37). The answer sheet `results/submission.parquet`, the freeze record `results/freeze.json` and the generating script `harmonization/freeze.py` are in `config/frozen-manifest.json`. Before sealing, the frozen grading function was run end to end on fake answers.
- **Next**: a person pushes the `final-test` tag → the GitHub grader (`grader.yml`) commits `results/final-test/` back to this branch → `git pull` → write `reports/final-test.md` truthfully (raw/calibrated coverage according to the rule in ADR 0008 section 5) → S12.
- **Do not push to this branch during grading**: the workflow's last step pushes results to this branch, and any other commit in the meantime would make that push fail.
- **S12 (done)**: `harmonization/series_v1.py` (committed, not yet run for real): production version = the frozen evaluation version (this machine never has S-NPP for 2012–2013, red line 1); Terra-only months build Aqua inputs from Terra before going into the model (first compared with v0's M1s chain on the validation windows, `terra-check`); the holdout-region bridge uses the local MODIS ratio (ADR 0005 item 6, option B); whether intervals are multiplied by the calibration factor is decided by ADR 0008 section 5; the acceptance check `recount()` has been tried on v0 (426 region-months, 0 mismatches). Intermediate results are in `s11/` in the data directory.
- **S11 scores**: Test 1 MALE 0.258 (M1s 0.332), Test 2 0.644 (M1s 0.857); E028 is better in both; but in the holdout regions the zero-hotspot and low-hotspot metrics are worse than M1s and totals are 20–35% too low (except northern Australia), with central Siberia at MALE 1.14. Interval coverage uses the calibrated values per the ADR 0008 rule: 95.5% / 55.9%. Full text in `reports/final-test.md`.
- **S12 dataset v1** (pre-release `dataset-v1`): generated by `uv run python -X utf8 -m harmonization.series_v1 build` (resampling results are cached in `s12/` in the data directory; without the cache it retrains 100 times, about 1 hour). The production version and the evaluation version are the same model (training regions 2014-01–2021-06, trees 766/970), and retraining reproduces the answer sheet's `est_final` bit for bit. Download with `gh release download dataset-v1 --repo team-inspiratio/inspiratio-space-apps-2026`, then `sha256sum -c SHA256SUMS.txt`.

  | File | SHA256 |
  |---|---|
  | `data-interface.md` | `535aed67ec0a0e365b263c23e5e83775f42597964e83a94c7e3674420938fcf7` |
  | `dataset_v1.parquet` | `60d13babfa450b86194ae72fd1d2d8c048085b303a1e381a7685e6d23b5a559e` |
  | `california.json.gz` | `f206711f9a55bfac7f7256b8b087d7b3bbc7e684c0ef5f7c05e233be0ef98a3f` |
  | `central_siberia.json.gz` | `08e510de4bf5e5a23062158ae16fd44a3f19a028f50da402b2c98ca8ff4ea426` |
  | `cordoba.json.gz` | `703ad6f3b2343ff0a47611de6f38c7f925342a630ab512e8e59968a2d9195175` |
  | `indo_gangetic.json.gz` | `af0e3742caf0f4f253ffa2e175e17eec262e4561d3a73f938043a61e0f58f2d7` |
  | `north_australia.json.gz` | `c38ae0a87c5d79f138a0b8a5bdf5f9da2d3334a305100fb68f968fe57b963c97` |
  | `southern_africa.json.gz` | `c7b00890426b6699979f24bd1caffb6c6902d045feca9ed8ca026bce69958dda` |
  | `meta.json` | `6abc6c3663a45aa093a036b7328c0a5b6ac17652b00a2494d33ddf3290f0b8db` |
  | `region_totals_v1.csv` | `54e3cfbff46a70cd0c2318c0139b3e9a281e67f397b96cebb5c8de1076e10dda` |
  | `resamples20_v1.parquet` | `7cd6d799f3aa8a5e94c1eb1de9119eab1dab5251fe264afb0c629a8293f2c56e` |

- **Tips for session 5**:
  - The report (S13) must state clearly: Test 2's weaknesses (section 3), the intervals' insufficient coverage in new regions, that 2012–2013 in the training regions are estimates in the dataset (ADR 0009 item 1, awaiting human confirmation), and that the error for Terra-only months is about 1.6 times that with Aqua (ADR 0009 item 2).
  - The era-shift investigation (pre-registration section 8) has not been done yet; it is in S13.
  - In the GFED plausibility check, the 2012–2013 VIIRS part can only use data on the same basis as the blind grading, which this machine does not have.
