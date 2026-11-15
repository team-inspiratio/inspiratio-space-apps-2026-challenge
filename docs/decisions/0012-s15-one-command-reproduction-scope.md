# 0012 S15: scope and checks of the one-command reproduction

## Background

S15 on the task card requires "one-command reproduction in a clean environment (for example `uv run python pipeline.py all`), with results matching the score table". Plan section 10 says teammates "can download the Release data directly, or rebuild from scratch with `pipeline.py all`". The task card does not say which step to start from, what to compare, or which steps cannot or should not be rerun.

## 1. Two entry points; acceptance uses the first

- `pipeline.py all --from-release`: downloads the S05 grid tables from Release `data-v0` (checked against the Release's SHA256), then reruns every stage after that. No FIRMS key needed, about 2–3 hours. **S15 acceptance uses this entry point**, run in a fresh clone with an empty data directory.
- `pipeline.py all`: starts from raw data (FIRMS annual archives, the API, GFED; about 50 GB; needs a FIRMS key). The code is wired up, but this time it was **not fully rerun**, because:
  - the annual archives are pinned by SHA256, and re-downloading them means checking each one again, while the S02–S05 acceptance checks (comparisons, row accounting, totals conservation) have already been done;
  - the 2026 data comes from the API, and FIRMS gradually replaces near real-time data with standard products, so a re-download may legitimately differ from the one made on 2026-11-03; the API segment therefore only reports differences and does not treat them as errors;
  - the download is about 9 GB plus 1 hour of rate-limited API calls, and would use up the user's FIRMS quota.

## 2. Steps that are not rerun

| Step | Why it is not rerun | How consistency is ensured |
|---|---|---|
| S10 experiment loop (37 runs) | It is a "search" whose result is the choice of E028; E028 is frozen in `harmonize.py` | The `freeze` stage reruns E028's frozen procedure on both validation windows, and the scores and parameters must match `scores-s10.json` and `freeze.json` exactly |
| S10 review | Depends on the variant sources on the experiment branch | The review notes are committed |
| S11 sealing | The answer sheet is a frozen file, and resealing would overwrite it | Rerun the 100 test-set resamples and compare bit for bit with the sealed answer sheet |
| Final test | Can be taken only once (red line 1) | The scores are in `results/final-test/`, produced by the GitHub grader |
| S12 point-by-point recount | Needs the cleaned S-NPP point data, which `data-v0` does not have (ADR 0003) | S12 did it on the original machine (426 region-months, 0 mismatches, recorded in `meta.json`); when rebuilding from the Release, `meta.json` differs only in this item, so it is removed before comparing |

## 3. What is checked (`pipeline.py check`, 37 items)

1. The committed files that stages rewrite (`reports/a5-stats.json`, `judge-check.md`, `scores-v1.json/.md`, `validation.json`, `docs/anomaly-cases.json`) are identical word for word to the committed versions (ignoring line endings).
2. Both validation windows: the frozen procedure's scores, parameters and numbers of trees equal `freeze.json`, and MALE equals E028's in `scores-s10.json`; the calibration factor equals 5.37.
3. Test set: the retrained `est_final` and the 100 resamples are bit-for-bit identical to the sealed answer sheet; M1s, QM and M0 are also identical.
4. The SHA256 of every file in datasets v0 and v1 equals the value recorded in `results/expected/` (except the document copies shipped with the Release, which are compared through git in item 1). When starting from the Release there is no S12 point-by-point recount, so that item is removed from `meta.json` before comparing; the 6 web-page region files embed the same `meta.json`, so the published recount record is put back, re-encoded the way `series_v1` writes it, and the SHA256 is then required to match bit for bit (stricter than "remove and compare").

## 3a. Acceptance result (2026-11-04)

In a fresh clone (`94bdd93`) with the empty data directory `D:/inspiratio-repro`, running `uv run python -X utf8 pipeline.py all --from-release` took 87 minutes in total (41 minutes for the freeze stage, 42 for dataset v1, everything else under 2 minutes). `pipeline.py check`: **all 37 items passed**. `git status` in the clone is clean (`docs/anomaly-cases.json` differs only in Windows line endings; the content is identical).

The first check had 31 items passing and 6 failing, all of them v1 region files, for exactly the recount-record reason described above. After the check rule was fixed and the check rerun, all 37 passed. The data did not change at all.

## 4. Problems found and fixed during reproduction

- Download and import used to decide whether something had been done by "whether this file is in the committed manifest / ledger". In an empty data directory this treated every file as done and skipped it (in a clean environment not a single GFED file was downloaded). Changed to check for the actual results in the data directory; re-downloaded annual archives and GFED files must match the manifest's SHA256, and re-imported annual archives must match the ledger's row counts. No existing results are affected.
- The check rule originally handled the "recount skipped" case only for `meta.json` and missed the 6 region files that embed it. This is fixed (see section 3, item 4), and a unit test was added.

## Status

Decided by the AI under the user's authorization, 2026-11-04. **Awaiting human confirmation (a look-over is enough)**: acceptance used the `--from-release` entry point rather than a full rerun from raw data (item 1).
