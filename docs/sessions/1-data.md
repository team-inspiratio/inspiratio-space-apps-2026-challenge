# Task card 1-data: pre-registration and data (S01–S06)

> Finish this card in one session. Before starting, read progress, claim the card and run the preflight following the "Start-of-session routine" in [`AGENTS.md`](../../AGENTS.md).

## Prerequisites

- S00 is done (S00 is marked done in `PROGRESS.md` and CI is green).
- No Release data package is needed: this card downloads everything from scratch.
- Machine: about 50 GB of free disk (data directory), 16 GB+ of RAM, a stable network. The annual archives add up to tens of GB and take several hours to download.

## What a person must prepare

1. `.env` contains `FIRMS_MAP_KEY` and `INSPIRATIO_DATA_DIR` (the preflight checks this).
2. `gh auth login --web` is done (at the end of this card, `gh release create` is used to upload the data package).

**The holdout regions are confirmed; do not ask again** (the user, 2026-11-03, see [`docs/decisions/0001-holdout-regions.md`](../decisions/0001-holdout-regions.md)): northern Australia (savanna), central Siberia (boreal forest), India's Ganges Plain (cropland), each about 10°×10°. S01 writes these three regions directly into `config/regions.json`: the exact bounds are set only from geographic location and ecosystem type, **without looking at any VIIRS data**, without overlapping the training regions, and are frozen once written.

## Plan sections to read (only these)

From [`docs/execution-plan.md`](../execution-plan.md): section 1 (verified facts), section 2 (method), section 3 (validation, for writing the pre-registration), section 4 (test-set isolation), the S01–S06 rows of the table in section 6, and section 10 (data relay). For field meanings and cleaning details, see the "Data", "Basic units and data preparation" and "Line A: Data" sections of [`docs/proposal.md`](../proposal.md); where they conflict with the execution plan, the execution plan wins (for example, the execution plan uses the global annual archives, so no Earthdata account is needed).

## Stages to do

### S01 Pre-registration (must be committed before any modeling)

- `config/settings.yaml`: 0.25° grid, calendar months (UTC), time range 2000-11 to 2026-10, quality-control thresholds (type=0; MODIS confidence ≥ 30; keep n/h for VIIRS), data splits (training 2016-01–2021-06; validation 2014–2015; auxiliary backward window: train 2018–2021-06, validate 2016–2017; Test 1 2012-02–2013-12; Test 2 holdout regions), random seed.
- `config/regions.json`: training and showcase regions (California, Córdoba in Argentina, the southern African savanna; for bounds, see "Demonstration regions" in the proposal) + the 3 confirmed holdout regions (see above), with the fields name, west/south/east/north and role (train or holdout).
- Random rectangles: generated with a fixed seed, about 150 per GFED region plus another 200 per demonstration region, 1°–5° on a side, saved as `config/rectangles.parquet` or `.csv` (small files may go into git). The GFED region bounds are taken from the GFED4.1s basis regions.
- `docs/preregistration.md`: turn items 1–7 of plan section 3 into concrete metrics, thresholds and tolerances (for example the selection rule "at least 10% better than M1s, with an improvement of more than 1 standard error", and the allowed range of change in the share of positive estimates on zero-hotspot samples), and state that they are fixed before any validation score is seen.
- `.github/workflows/grader.yml` (external blind grading, plan item 4.4):
  - triggered only when the `final-test` tag is pushed;
  - first checks whether `results/final-test/` already exists, and fails if it does (the test can be taken only once);
  - verifies that the hash of `submission.parquet` matches the frozen manifest;
  - downloads the 2012 and 2013 S-NPP annual archives and the holdout-region VIIRS in the cloud (the annual archives are public and need no key), and uses the code from the same commit as the tag (`harmonization/final_test.py`, written and frozen in S07) to compute the answer key and the scores;
  - commits the scores back to the repository (requires `permissions: contents: write`).
  - At S01 `final_test.py` does not exist yet; write the calling convention into the workflow and explain it in the pre-registration.
- Extend the guardrails: add a helper for the holdout-region spatial lock to `tools/guardrails.py` (for example `in_holdout(lat, lon)`, reading `config/regions.json`), and add tests.
- Freeze: `uv run python tools/guardrails.py freeze config/settings.yaml config/regions.json config/rectangles.* .github/workflows/grader.yml tools/guardrails.py`, and commit the frozen manifest. The commit message should say "S01 pre-registration".

### S02 Download

- Annual archives: MODIS 2000–2025, S-NPP 2014–2025 (**skip 2012 and 2013**), NOAA-20 2018–2025, downloaded to `INSPIRATIO_DATA_DIR/raw/` with resumable downloads; record each file's SHA256 and row count in `data/manifest` (small files go into git, for example `docs/data-manifest.csv`). Call `assert_download_allowed()` before every request.
- FIRMS API (with the key from `.env`, rate-limited): SP and NRT for all of 2026 (SP: VIIRS up to 2026-07-31, MODIS up to 2026-08-31; NRT after that), with S-NPP only up to 2026-11-02. Missing-data list: `/api/missing_data/?action=fetch_data`.
- GFED4.1s (0.25°, monthly burned area), as the independent reference for item 4 of section 3.
- Acceptance: for a few randomly chosen days, compare the API output with the annual archives row by row; they match.

### S03 Import

- Stream the CSVs into Parquet (partitioned by satellite and year). VIIRS records that fall in the holdout regions are dropped during the streaming import and never written to disk.
- After import, delete the raw VIIRS archives and keep only their hashes.
- Acceptance: the row accounting balances (raw rows = written rows + rows dropped for holdout regions, one accounting line per file).

### S04 Cleaning

- Keep only type=0; MODIS confidence ≥ 30; keep n/h for VIIRS; merge only duplicate-download records (by satellite, date, minute, latitude/longitude; SP takes priority over NRT).
- The NRT segment has no type column: use the locations of type=2 in the SP period as a static heat-source mask, and note this in the cleaning report.
- Manually inspect 20 randomly chosen deleted records. Produce the cleaning report `reports/cleaning.md` (how many rows each rule deleted).

### S05 Gridding and features

- Counts per cell × month × satellite; MODIS features (count, FRP median and 75th percentile, share of low FRP, mean pixel size, latitude, month, night share, fire days, neighbor counts). For empty cells, FRP-type features are recorded as missing, with a "no detection" flag.
- Distinguish 0 from missing (using the missing-data list).
- Acceptance: the sum of cell counts = the total number of cleaned hotspots (totals conserved), written as a pytest test.

### S06 Data health check (A5)

- The 4 plots required by the proposal (monthly series for the training regions; the S-NPP/Aqua ratio over time; the ratio against latitude and pixel size; the NOAA-20/S-NPP ratio), plotting VIIRS only from 2014-01 onward and only for the training regions.
- Write `reports/findings.md` (a one-page findings note).

## Acceptance criteria

- The S01 commit is earlier than any modeling code; `grader.yml` and the pre-registration are committed and frozen; CI is green.
- S02 spot-check comparison matches; S03 row accounting balances; S04 cleaning report is done; S05 totals-conservation test passes; S06's 4 plots and findings.md are done.
- The processed data (cleaned Parquet and the cell × month table, about 1–2 GB) has been uploaded as a GitHub Release asset (for example tag `data-v0`, pre-release), with its SHA256 recorded in `PROGRESS.md` and the data manifest.

## Not allowed

- Downloading any 2012/2013 S-NPP data; writing holdout-region VIIRS to disk; looking at holdout-region or 2012–2013 VIIRS to choose regions or tune parameters.
- Replacing the confirmed holdout regions (ask a person first if they must change); changing settings, regions or grader after the S01 freeze.
- Committing raw data or large files to git; writing the key into any file or log.
- Starting any modeling (M0, M1s and so on belong to session 2).

## When finished, update

- `PROGRESS.md`: after each of S01–S06, update the stage table (status, time, key numbers, commit) and push; once all are done, change the status block to `current_card: docs/sessions/2-baselines.md`, `status: ready`, clear the claim, set `last_pushed_stage: S06`, and replace `needs_human` with what session 2 needs.
- Update the progress box at the top of the README to match. Confirm CI is green.

## Next card

[`2-baselines.md`](2-baselines.md)
