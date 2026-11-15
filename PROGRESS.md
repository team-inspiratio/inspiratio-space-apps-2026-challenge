# PROGRESS: Project progress

> The machine-readable status block sits between the two comment lines below, in YAML. Read it at the start of every session, change it when you claim a card, and update it after every completed stage.
> `tests/test_progress.py` checks its format.

<!-- STATUS:BEGIN -->
```yaml
current_card: docs/sessions/G-global.md        # next (or current) task card
status: done                            # ready | in_progress | blocked | done
claimed_by: ""                          # claimant's name; empty means unclaimed
claimed_at: ""                          # claim time, ISO 8601 UTC
last_pushed_stage: G4                   # last stage completed and pushed
branch: feat/data-harmonization
data_release: global-v1               # full Release v1 (CC BY 4.0, S15); the global version is Release global-v1 (stage G); v1 for the 6 regions is still Release v1; processed inputs are in data-v0, milestone A in milestone-a; SHA256 in results/expected/
next_step: "All task cards are done. The global Release global-v1 is published (docs/data-interface-global.md); waiting for the PR to be merged into main"
needs_human:
  - "Tell the front end: public global-v1 frontend assets are bundled in inspiratio-site/public/data/global-v1/ (CC BY 4.0); setup and availability are in docs/public-data.md; interface in docs/data-interface-global.md (interval factor 16.75; explain that intervals are very wide)"
  - "Please merge: the G-global PR (feat/data-harmonization → main)"
  - "Confirmed (by the user on 2026-11-04 together with approving the global-v1 release): the G-global production version uses the globally retrained model, and the interval factor is re-derived on the global validation windows (docs/decisions/0013 items 3 and 5)"
  - "Awaiting human confirmation (a look-over is enough; not blocking): S15 acceptance used the pipeline.py all --from-release entry point (starting from the grid tables in Release data-v0), not a full rerun from raw data (docs/decisions/0012 item 1)"
  - "Tell the front end: this public repository currently has no Release assets; bundled global frontend data and availability are documented in docs/public-data.md"
  - "Tell the front end: the anomaly indicator reference implementation harmonization/anomaly.py + 25 standard test cases docs/anomaly-cases.json (check answers field by field; extra details in docs/data-interface.md section 6 and docs/decisions/0011 item 1); the dataset now also has a CSV version"
  - "Please read through: the data card docs/data-card.md and the AI usage statement docs/ai-usage.md"
  - "Please read through: the validation report reports/validation.md (6 core figures + limitations; conclusion: trustworthy in the training regions; in the holdout regions the error is 2.5 times larger and totals are 14–45% too low)"
  - "Awaiting human confirmation (a look-over is enough; not blocking): implementation details of the GFED check and the era-shift investigation newly done in S13 (docs/decisions/0010: the era-shift main number uses the mean 5-fold AUC; GFED only through 2016; no numeric comparison with the literature value)"
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
  - "For a person to handle: hold a 1-hour review meeting following docs/review-packet.md, prioritizing X1 (PRs #4/#5 not merged) and X2 (repository private and without a LICENSE)"
  - "Awaiting human confirmation: whether to unlock the 2012–2013 S-NPP observations to replace the training-region estimates (docs/decisions/0014; recommendation: replace only, no retraining, aggregated in the cloud; a person must commit the [unfreeze])"
  - "Awaiting human confirmation: confidence levels for the global product, M1s fallback, web-page labels (docs/decisions/0015; recommendation: finer levels, no fallback)"
  - "Awaiting human confirmation: the website deployment option (docs/decisions/0016; recommendation: first republish the fixed version on the existing Sites, then switch to GitHub Pages once the repository is public)"
  - "For a person to handle: after the official guides are released on 11/13, check every draft in docs/submission/ item by item and fill in the bracketed items"
  - "Awaiting a person's decision: whether a \"one click to a given region and month\" entry point is needed (currently the preset buttons go to a region in one click, and a route takes 1–3 clicks; this is a new feature and was not built)"
```
<!-- STATUS:END -->

## Submission prep (not part of the data track)

> This section records the competition submission prep. It does not change the data track's status block and does not claim G-global.

- Task 1 done: human review packet `docs/review-packet.md` (covers the 20 needs_human items of data branch `5dbc2e2`, plus two inventory findings, X1 and X2).
- Task 2 done: proposal ADR 0014 (unlocking the 2012–2013 S-NPP observations) and ADR 0015 (global confidence levels, M1s fallback, web-page labels); both are proposals only and were not implemented.
- Task 3 done: draft comparison of deployment options, ADR 0016 (chatgpt.site, Vercel, Netlify, GitHub Pages); nothing was deployed.
- Task 4 done: draft submission materials `docs/submission/` (`project-page.md`, `demo-script.md`, `checklist.md`), all marked to be checked item by item after the official guides are released on 11/13.
- Task 5 done: the three demo routes were tested on the PR #5 build and written into `docs/submission/demo-script.md`. No bugs blocking the demo were found, so the web code was not changed.

## Sessions overview

| Session | Task card | Stages covered | Status |
|---|---|---|---|
| 0 | (repository setup) | S00 | ✅ done |
| 1 | [`1-data`](docs/sessions/1-data.md) | S01–S06 | ✅ done |
| 2 | [`2-baselines`](docs/sessions/2-baselines.md) | S07–S09 (milestone A) | ✅ done |
| 3 | [`3-model`](docs/sessions/3-model.md) | S10 | ✅ done |
| 4 | [`4-freeze-test`](docs/sessions/4-freeze-test.md) | S11–S12 | ✅ done |
| 5 | [`5-report`](docs/sessions/5-report.md) | S13–S15 (milestone B) | ✅ done |
| G | [`G-global`](docs/sessions/G-global.md) | Global rerun | ✅ done |

## Stage table

| Stage | Content | Status | Key numbers |
|---|---|---|---|
| S00 | Environment, guardrails, CI, self-describing files | ✅ done | CI green; 17 pytest tests pass |
| S01 | Pre-registration (settings, holdout regions, random rectangles, grader.yml) | ✅ done | 6 regions (3 training + 3 holdout); 3300 rectangles; 5 files frozen |
| S02 | Download (annual archives, 2026 via API, missing-data list, GFED) | ✅ done | 46 annual archives (about 9 GB, locked years skipped); 918 satellite-days from the API; 24 years of GFED; 178 missing days; 4 days × 3 sources compared: every annual-archive row is in the API |
| S03 | Import (stream to Parquet, drop holdout-region VIIRS) | ✅ done | 46 annual archives + 6 API sources; for every file, raw rows = written + dropped for holdout regions (`docs/ingest-ledger.csv`); VIIRS archives deleted |
| S04 | Cleaning | ✅ done | 529 million → 444 million rows; type −6.1%, low confidence −9.7%, NRT mask −0.18%, 222 duplicates; spot check of 20 found no wrongful deletions (`reports/cleaning.md`) |
| S05 | Gridding and features | ✅ done | Totals conserved (sum of cell counts per satellite = cleaned points); dense regional table 2.616 million rows; 20 features |
| S06 | Data health check (A5) | ✅ done | S-NPP/Aqua annual ratio about 4.6–10; NOAA-20/S-NPP median 0.98–1.00; Terra/Aqua drops sharply after 2020 |
| S07 | Grader (prepare, evaluate) | ✅ done | Dummy methods: always 0, combined MALE 5.90; MODIS as is, 1.79; SHA256 identical over two runs (`reports/judge-check.md`) |
| S08 | Fallback models M0, M1s, QM; bridge and continuation | ✅ done | Combined MALE over both windows: M1s (λ=20) 0.377, QM 0.463, M0 1.795; Terra→Aqua→M1s chain 0.522; NOAA-20 continuation median monthly total bias −0.3% to +3.1% (`reports/scores-v1.md`) |
| S09 | ★Milestone A: dataset v0, front-end export, pre-release | ✅ done | 2.616 million cell-months: 554,000 S-NPP observed, 47,000 NOAA-20 converted, 1.82 million M1s, 197,000 Terra bridge; pre-release `milestone-a`, SHA256 of all 9 files checked after download |
| S10 | LightGBM and AI experiments | ✅ done | 37 experiments (E000–E036; budget cut and wrapped up early per ADR 0007); best validation MALE: E028 two-stage LightGBM 0.2947, 21.8% lower than M1s (0.3766) (difference −0.082 ± 0.016, 95% interval −0.113 to −0.053), 0.169 lower than QM; all top 3 pass the guardrails and the leakage review (`reports/scores-s10.md`, `reports/model-review.md`) |
| S11 | Freeze and external blind grading | ✅ done | E028 selected. Test MALE: Test 1 **0.258** (M1s 0.332, 22% lower), Test 2 holdout regions **0.644** (M1s 0.857); κ 0.69 / 0.53; regional interval coverage after calibration 95.5% / 55.9% (raw 37.9% / 12.9%); in the holdout regions the zero-hotspot and low-hotspot metrics are worse than M1s and totals are 20–35% too low (`reports/final-test.md`) |
| S12 | Final dataset | ✅ done | Production version = the frozen evaluation version E028 (ADR 0009); 2.616 million cell-months: 554,000 S-NPP observed, 1.817 million model estimates, 197,000 Terra bridge, 47,000 NOAA-20 converted; 100 resampled intervals, regional intervals multiplied by the calibration factor 5.37; acceptance: in the S-NPP segment, 15.19 million points over 426 region-months match the observations one by one; pre-release `dataset-v1` |
| S13 | Validation report (D1) | ✅ done | All of items 1–7 in section 3 done (`reports/validation.md`). The two new items: era-shift AUC 0.57 (training regions) / 0.56 (holdout regions), versus 0.75 / 0.70 for the 2022–2026 control (Terra drift); hotspots per km² of GFED burned area unchanged across 2012 (southern Africa 2.77 → 2.92, Córdoba 5.90 → 5.86), while direct stitching jumps about 5 times. 6 core figures `reports/figures/d1-*.png` |
| S14 | Delivery | ✅ done | CSV version of the dataset `dataset_v1.csv.gz` (18 MB, checked column by column against the Parquet, relative error < 5×10⁻⁶); data card `docs/data-card.md`; AI usage statement `docs/ai-usage.md`; anomaly indicator reference implementation `harmonization/anomaly.py` + 25 standard test cases `docs/anomaly-cases.json` (19 hand-worked edge cases + 6 from real data); HANDOFF section "Where the results are"; ADR 0011 |
| S15 | ★Milestone B: one-command reproduction, Release v1, merge into main | ✅ done | After the user confirmed, squash-merged into main and published the full Release `v1` (CC BY 4.0). Fresh clone + empty data directory running `pipeline.py all --from-release`: 87 minutes, all 37 `pipeline.py check` items pass (score files identical word for word; scores on both validation windows equal freeze.json and E028; the test set's est_final and 100 resamples bit-for-bit identical to the sealed answer sheet; SHA256 of every file in datasets v0 and v1 matches). Along the way, fixed download and import wrongly skipping work in an empty data directory (ADR 0012) |
| G1 | Global configuration and global dense table | ✅ done | `config/regions-global.json`: 14 GFED regions + 3 holdout boxes, 278,192 cells (273,712 training, 4,480 holdout), 86.8 million cell-months; split into 10° latitude bands; one global training run takes about 4 minutes (24.36 million rows) |
| G2 | Global validation scores (by GFED region, reported only) | ✅ done | Combined MALE over both windows (all rectangles): E028 global retrain **0.534**, M1s 0.619 (difference −0.084 ± 0.013), QM 0.680, M0 2.030; reference S11 three-region model 0.563. M1s is better in CEAM, EQAS, NHSA and SHSA; BOAS is worst at 1.03; the error for 1–9 hotspots is 1.13 times M1s's (`reports/global-scores.md`) |
| G3 | Global resampling and interval calibration | ✅ done | First 50 sealed resamples per group (ADR 0013 item 5 addendum, approved by the user); calibration factor on the global validation windows **16.75** (S11: 5.37), raising coverage from 14% to 90% |
| G4 | Global dataset generation and release | ✅ done | 86.8 million cell-months; S-NPP recount over 1,988 region × months and 189 million hotspots, 0 mismatches; global annual totals go from 16.0 M in 2013 (model) to 16.6 M in 2014 (observed), with no break (`reports/global-review.md`). After the user looked it over, Release `global-v1` was published (CC BY 4.0), with SHA256 in `results/expected/dataset-global-v1.sha256` |

## Handover notes

No active handover. See the status block for outstanding review items.

## Public website source maintenance

- V2 publishing uses the repository's GitHub Pages workflow, with checksum-verified bundled assets and production-build browser checks under the repository path. Relevant merges into main deploy automatically.
- V2 uses the current public repository name, `inspiratio-space-apps-2026-challenge`, with no rename. The deployment job attempts to enable Pages; if GitHub rejects automatic setup, a repository admin selects GitHub Actions under Settings → Pages → Build and deployment → Source. Direct Pages management through the current GitHub integration returned HTTP 403.
- V2 documentation and evidence links use this public repository. Data preparation verifies and copies the bundled global frontend files without credentials or downloads.
- Public data availability and hosting requirements are documented in `docs/public-data.md`. No scientific results, frozen files or data-stage claims changed.

## Website directory organization (2026-11-15)

User-requested path-only relocation: the legacy frontend is now in `web/archive/website-v1/` and the production frontend is in `frontend-v2/website/`. Build scripts, tests, documentation links and the Pages workflow follow the new paths. Website content, URLs, scientific data and model behavior are unchanged. The completed data-task status above is unaffected.
