# PROGRESS: Project progress

> The machine-readable status block sits between the two comment lines below, in YAML. Read it at the start of every session, change it when you claim a card, and update it after every completed stage.
> `tests/test_progress.py` checks its format.

<!-- STATUS:BEGIN -->
```yaml
current_card: docs/sessions/1-data.md   # next (or current) task card
status: in_progress                     # ready | in_progress | blocked | done
claimed_by: "qiuxue-yee"                # claimant's name; empty means unclaimed
claimed_at: "2026-11-03T18:48:11Z"      # claim time, ISO 8601 UTC, e.g. 2026-11-03T08:00:00Z
last_pushed_stage: S01                  # last stage completed and pushed
last_pushed_at: 2026-11-03
branch: feat/data-harmonization
next_step: "Task card 1-data in progress: S01 done; now doing S02 download → S03 import → S04 cleaning → S05 gridding → S06 data health check"
needs_human:
  - "Awaiting human confirmation: the frozen tools/guardrails.py crashes on Chinese Windows when it reads git history as GBK; currently worked around with -X utf8. Should a person [unfreeze] it to fix the encoding? (docs/decisions/0002)"
  - "The data stages need about 50 GB of disk and 16 GB+ of RAM; fill in FIRMS_MAP_KEY and INSPIRATIO_DATA_DIR in .env"
  - "GitHub CLI login: can be skipped when taking over on this already-logged-in computer; when taking over on another computer, first run gh auth login --web once (gh is needed to upload the Release data package at the end of session 1)"
```
<!-- STATUS:END -->

## Sessions overview

| Session | Task card | Stages covered | Status |
|---|---|---|---|
| 0 | (repository setup) | S00 | ✅ done |
| 1 | [`1-data`](docs/sessions/1-data.md) | S01–S06 | 🔄 in progress (qiuxue-yee) |
| 2 | [`2-baselines`](docs/sessions/2-baselines.md) | S07–S09 (milestone A) | not started |
| 3 | [`3-model`](docs/sessions/3-model.md) | S10 | not started |
| 4 | [`4-freeze-test`](docs/sessions/4-freeze-test.md) | S11–S12 | not started |
| 5 | [`5-report`](docs/sessions/5-report.md) | S13–S15 (milestone B) | not started |
| G | [`G-global`](docs/sessions/G-global.md) | Global rerun | not started (after S15) |

## Stage table

| Stage | Content | Status | Completed | Key numbers | commit |
|---|---|---|---|---|---|
| S00 | Environment, guardrails, CI, self-describing files | ✅ done | 2026-11-03 | CI green; 17 pytest tests pass | 3dcf808 |
| S01 | Pre-registration (settings, holdout regions, random rectangles, grader.yml) | ✅ done | 2026-11-03 | 6 regions (3 training + 3 holdout); 3300 rectangles; 5 files frozen | 7d1aa0c |
| S02 | Download (annual archives, 2026 via API, missing-data list, GFED) | ⬜ todo | | | |
| S03 | Import (stream to Parquet, drop holdout-region VIIRS) | ⬜ todo | | | |
| S04 | Cleaning | ⬜ todo | | | |
| S05 | Gridding and features | ⬜ todo | | | |
| S06 | Data health check (A5) | ⬜ todo | | | |
| S07 | Grader (prepare, evaluate) | ⬜ todo | | | |
| S08 | Fallback models M0, M1s, QM; bridge and continuation | ⬜ todo | | | |
| S09 | ★Milestone A: dataset v0, front-end export, pre-release | ⬜ todo | | | |
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
