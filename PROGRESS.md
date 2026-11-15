# PROGRESS: Project progress

> The machine-readable status block sits between the two comment lines below, in YAML. Read it at the start of every session, change it when you claim a card, and update it after every completed stage.
> `tests/test_progress.py` checks its format.

<!-- STATUS:BEGIN -->
```yaml
current_card: docs/sessions/3-model.md   # next (or current) task card
status: ready                           # ready | in_progress | blocked | done
claimed_by: ""                          # claimant's name; empty means unclaimed
claimed_at: ""                          # claim time, ISO 8601 UTC, e.g. 2026-11-03T08:00:00Z
last_pushed_stage: S09                  # last stage completed and pushed
last_pushed_at: 2026-11-03
branch: feat/data-harmonization
data_release: data-v0                   # gh release download data-v0; SHA256 in the handover notes; milestone A data is in milestone-a
next_step: "Start a new session for task card 3-model: S10 first LightGBM version + AI-driven automated experiments + independent review"
needs_human:
  - "Awaiting a person's decision: the pass criterion for the NOAA-20 continuation (docs/decisions/0005 item 4; the criterion was proposed after seeing the test results)"
  - "Awaiting a person's decision: whether the Terra bridge in the holdout regions uses the training regions' pooled ratio or the local MODIS ratio (docs/decisions/0005 item 6; affects the S12 production version)"
  - "Awaiting human confirmation: QM details, choice of λ, bridge years, v0 source rules (docs/decisions/0005 items 1–3 and 5)"
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
| 3 | [`3-model`](docs/sessions/3-model.md) | S10 | ⏭ next |
| 4 | [`4-freeze-test`](docs/sessions/4-freeze-test.md) | S11–S12 | not started |
| 5 | [`5-report`](docs/sessions/5-report.md) | S13–S15 (milestone B) | not started |
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
| S10 | LightGBM and AI experiments | ⬜ todo | | | |
| S11 | Freeze and external blind grading | ⬜ todo | | | |
| S12 | Final dataset | ⬜ todo | | | |
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
