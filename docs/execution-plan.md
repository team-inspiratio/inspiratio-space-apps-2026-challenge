# Execution plan v4: MODIS × VIIRS hotspot harmonization: data analysis and algorithms

> Once work starts, this file is committed unchanged to the repository as `docs/execution-plan.md`.

## ★ First step after approval: write the public explainer, then stop

1. Use Claude Docs to produce a **plain-language explainer**, titled "Plan to 'repair' the fire hotspot record: the data analysis part", and send the user the link so it can be forwarded to the team. It covers:
   - the goal in one sentence;
   - where the problem lies: the "two bathroom scales" analogy for the difference between MODIS and VIIRS;
   - how we repair it;
   - how we prove the repair is right (including the "external grading" mechanism);
   - what the AI does and what people are responsible for checking;
   - the outputs;
   - resources and time;
   - risks and limitations;
   - **the two things the team needs to confirm**: extending to global coverage; the choice of holdout regions. (On 2026-11-03 the user confirmed both; see `docs/decisions/0001-holdout-regions.md`.)
2. Once the document is done, **stop and wait for the user to say "go"**.
3. After the user says "go", **this session does no more actual work**. Instead, use the app's "new session" feature (`start_session`, with a clean context, `fresh`) to open a **brand-new session** and give it a short handover note:
   - read this plan file `C:\Users\ASUS\.claude\plans\https-github-com-team-inspiratio-inspir-abundant-crystal.md`;
   - execute S00: have the user choose a directory, clone the repository, create the branch, set up the environment; create `AGENTS.md`, `CLAUDE.md`, `PROGRESS.md`, the task card for each stage, `HANDOFF.md` and the progress box in the README; commit this plan as `docs/execution-plan.md`; configure CI; push;
   - finally, complete the relay drill in section 11.4.

   This session ends here. From then on the new session drives progress, and the user opens it from the sidebar. From this moment the project's "memory" lives on GitHub, and every later stage gets its own new session (see section 9).

## 0. Context

- **Public repository**: `team-inspiratio/inspiratio-space-apps-2026-challenge`. Current source, documents, reports and bundled frontend assets are maintained here. See `docs/public-data.md` for current asset availability; the stages below record the scientific plan.
- **Scope of this plan**: item ① of the user's division of work, i.e. line A (A1–A5) + line B (B1–B6) of the proposal + the D1 validation report, plus the data interface for the front end (C1) and the data card.
  - Not included: the front end, the proposal, the demo.
- **Principles**:
  - follow the proposal's method, without piling on extra models;
  - hold validation to the **standard of a formal paper**;
  - do everything on this machine, fully automated;
  - when quota runs out, a teammate can take over.

## 1. Verified facts (2026-11-03, no longer assumptions)

| Item | Result |
|---|---|
| FIRMS global annual archives | Publicly downloadable, no key needed. MODIS 2000–2025, S-NPP 2012–2025, NOAA-20 2018–2025. **They have the `type` column** (confirmed by reading the file headers directly). Per year, unzipped: MODIS about 0.37 GB, S-NPP about 1.7 GB, NOAA-20 about 1.5 GB |
| FIRMS API (the user's key) | SP data: VIIRS up to 2026-07-31, MODIS up to 2026-08-31; NRT data: from then to the present, with S-NPP ending on 2026-11-02. **NRT has no `type` column**. A global single-day query returns about 30,000–60,000 rows in 1 second, but each call uses dozens of quota units, so the full 2026 data has to be downloaded with rate limiting, taking about 1 hour |
| Official missing-data list | Can be fetched directly from `/api/missing_data/?action=fetch_data` |
| Burned area | Not provided by the FIRMS API (the BA source returns 0 rows). Use the public **GFED4.1s** instead (0.25°, based on MODIS MCD64A1) as an independent reference |
| Disk | 142 GB free on drive C, 101 GB free on drive D. Data goes on drive D, peaking at about 50 GB; code goes under a short path on drive C |
| Challenge requirements | Harmonize until "which sensor the data came from no longer matters"; burning calendar; anomaly compared with the historical median; CSV download. The challenge text names "NASA Earthdata FIRMS" explicitly |
| Paper standards | Two main sources, explained below. In addition, similar projects commonly use OLS or quantile mapping for harmonization, which should serve as comparison methods |

- **ESSD (Earth System Science Data journal)**: data papers **must be validated against independent reference data; when no reference data exists, a plausibility assessment is required**.
- **Merchant et al. 2017**: give an uncertainty for every value; account for correlations between errors when aggregating; **test whether the uncertainty itself is accurate**.

## 2. Method (as in the proposal, plus paper-level comparisons)

- **Grid and time**: 0.25° (aligned with GFED), calendar months (UTC), 2000-11 to 2026-10.
- **Scope: first the regions set in the proposal, with global coverage kept as a final switch**:
  - Download and cleaning handle the whole globe in one pass (the annual archives are global anyway), but modeling, evaluation and export **first cover only the proposal's regions**: California, Córdoba in Argentina and the southern African savanna for training and showcasing, plus the holdout regions. This gets the pipeline working first and reaches milestone A quickly, and the data volume stays small, which makes relaying easier.
  - Once everything is done, and if quota remains, switch the region configuration to global and rerun everything (no code changes; this is the final stage G). **On 2026-11-03 the user agreed to extend to global coverage** (stage G changes from optional to planned).
  - The main product stays on the VIIRS scale (confirmed by the user).
- **Models (only these)**:
  - M0 direct stitching;
  - M1s simple ratio with shrinkage (fallback);
  - **QM quantile mapping** (new: the most common comparison method in similar studies);
  - **M3 LightGBM** (main model, with AI-driven automated experiments).
  - The proposal's extensions (M2 negative binomial, M5 ensemble) are done only after all of P0 is complete and if time allows. CNNs, pixel-level studies and the like are not done at all.
- **Input features as in the proposal**: MODIS count, FRP distribution, pixel size, latitude, month, night share, fire days, neighbor counts. Year, region name and any VIIRS information are banned. A monotonic constraint is applied to the MODIS count.
- **Splits as in the proposal**:
  - Training: 2016-01–2021-06;
  - Validation: 2014–2015; auxiliary backward window: train on 2018–2021-06, validate on 2016–2017;
  - Test 1: 2012-02–2013-12;
  - Test 2: holdout regions.
- **Holdout regions**: registered in advance, before any VIIRS is touched. Suggested: 3 regions of different ecosystem types, each about 10°×10°: northern Australia (savanna, as set in the proposal), central Siberia (boreal forest), India's Ganges Plain (cropland). ~~Needs team confirmation.~~ **Confirmed by the user on 2026-11-03**, see `docs/decisions/0001-holdout-regions.md`; the exact bounds are fixed only from geography and ecology when S01 writes `config/regions.json`.

## 3. Validation (to paper standards; metrics and thresholds written into the pre-registration before any work starts)

1. **Main metric as in the proposal**: MALE on random rectangles. About 150 rectangles per GFED region, plus another 200 per demonstration region. First average separately by region and complete year, then pool with equal weights. Auxiliary metrics: share of positive estimates on zero-hotspot samples, error for 1–9 hotspots, total bias, seasonal correlation.
2. **Comparisons come with confidence intervals**: for the score differences between LightGBM and M1s and QM, give 95% intervals from "year × region" block resampling. Overlapping rectangles do not count as independent samples, and no p-values are reported.
3. **Validation by use case** (new, closest to the challenge): in the test years, compute the "high / normal / low" label for the latest month from the "harmonized history" and from the "real VIIRS history", and measure how well the two agree (Cohen's κ). This directly answers "is our data reliable for judging anomalies?"
4. **Plausibility check against an independent reference** (ESSD requirement): use GFED burned area to see whether "hotspot count ÷ burned area" is stable across 2012; compare with values from the literature (for example, VIIRS counting about 70% more than MODIS in the tropics). This is only a plausibility check and is not used to tune the model.
5. **Uncertainty must be tested** (Merchant 2017): the required part is stability intervals from year-block resampling, with the **actual coverage reported** on the test set. If coverage is insufficient, calibrate the intervals for regional aggregates with validation-set residuals and report the calibrated coverage on the test set.
6. **Era-shift investigation (required by proposal D1)**: use a classifier to distinguish the input features of 2002–2011 from those of 2014–2021, and analyze the causes.
7. **Selection rule as in the proposal**: at least 10% better than M1s, neither window clearly worse, guardrail metrics within tolerance, and passing the leakage review; otherwise use M1s. Plus an anti-score-gaming rule: an improvement counts only if it exceeds 1 standard error.

## 4. Test-set isolation: external blind grading

1. **The time lock physically does not exist on this machine**: this machine **never downloads** S-NPP data for 2012 or 2013.
2. **The spatial lock passes through only once, at import, and never reaches disk**: holdout-region VIIRS records are dropped during streaming import and never written to disk; after import, the raw VIIRS archives are deleted and only their hashes are kept.
3. **The AI itself is restricted by a hook**: the project's `.claude/settings.json` configures a PreToolUse hook that blocks two kinds of action:
   - any download command or URL that requests VIIRS for the locked years or regions;
   - changes, during the AI experiment stage, to fixed files such as `prepare`, `evaluate` and `grader`.
4. **The grader is GitHub Actions, not me**:
   - the grading workflow `grader.yml` is committed **before modeling starts** and written into the pre-registration;
   - after the model is frozen, this machine uses only MODIS inputs to generate the predictions for the test period, `submission.parquet`, writes its hash into the frozen manifest and commits it (the answer sheet is sealed first);
   - after the `final-test` tag is pushed, GitHub's cloud machine **downloads the locked VIIRS data from FIRMS itself**, computes the answer key and the scores with the code from the same commit, and commits the results back to the repository;
   - if the workflow finds that results already exist, it refuses to run again: **the test can be taken only once**.
5. **Conclusion**: this machine and the AI never had the test answers; the scores are computed in a third-party environment, with timestamps throughout. The remaining risk is that this machine has internet access; this is disclosed honestly in the report and is also blocked by the hook.

## 5. AI-driven automated experiments (as in the proposal)

- Directory layout and `program.md` as in the proposal. Only `harmonize.py` may be changed. At most 150 experiments or 8 hours; stop after 30 consecutive runs without improvement.
- Division of labor: the LLM handles only **structural changes**; numeric tuning within each change is left to Optuna's automatic search, which saves tokens.
- Each experiment states a one-sentence hypothesis, recorded in `experiments.csv`; if the result is better it is kept and committed to a separate branch.
- At the end, a **review subagent with a fresh context** reviews the top 3: checks for leakage, runs feature-ablation experiments, draws prediction-relationship plots, and checks stability on the auxiliary window.

## 6. Stages and acceptance

Rule: **after each stage, update `PROGRESS.md`, then commit and push**; the draft PR shows progress automatically.

| Stage | Content | Acceptance |
|---|---|---|
| S00 Environment | The user chooses the directory (suggested: `C:\Users\ASUS\Projects\inspiratio`; data in `D:\inspiratio-data`); clone the repository, create the `feat/data-harmonization` branch; uv + Python 3.12 + lock; write the key into `.env`; configure secret scanning (pre-commit and CI); configure the hook; install gh (the user authorizes once) and open a draft PR; configure CI (ruff, pytest, gitleaks); commit this plan as `docs/execution-plan.md` | CI passes |
| S01 Pre-registration | Freeze settings; register the holdout regions and random rectangles; write `docs/preregistration.md`; **commit grader.yml** | Commit time earlier than any modeling |
| S02 Download | Annual archives (except S-NPP 2012/2013) with resumable downloads and recorded hashes; rate-limited API pulls for 2026 (SP plus NRT) and the missing-data list; for a few randomly chosen days, compare the API and the annual archives row by row | Comparison matches |
| S03 Import | Stream to Parquet, drop holdout-region VIIRS, then delete the raw VIIRS archives | Row accounting balances |
| S04 Cleaning | Keep only type=0; MODIS confidence ≥ 30, keep n/h for VIIRS; merge only duplicate-download records; for the NRT segment, use the locations of type=2 in the SP period as a static heat-source mask and note this in the report; inspect 20 randomly chosen deleted records | Cleaning report |
| S05 Gridding | Generate cell × month counts and features; distinguish 0 from missing | Totals conserved |
| S06 Health check (A5) | The 4 plots required by the proposal, plus findings.md | — |
| S07 Grader | prepare, evaluate; the two dummy-method checks; two runs bit-for-bit identical | Frozen |
| S08 Fallback | M0, M1s, QM; Terra→Aqua bridge; NOAA-20→S-NPP continuation test using the 2018–2026-10 overlap | Score table v1 |
| **S09 ★Milestone A** | Generate dataset v0 with M1s; export the front-end files and draft the data interface spec; publish a GitHub pre-release | The front end can start |
| S10 LightGBM and AI experiments | Hand-write the first version, run the experiment loop, independent review | experiments.csv and review notes |
| S11 Freeze and blind grading | Choose the model by the selection rule, write the frozen manifest, generate and seal the answer sheet, push the tag, GitHub grades it | Results committed back to the repository by CI |
| S12 Final dataset | Retrain the production version; resample 100 times; generate the series from 2000-11 to 2026-10 with source flags | S-NPP segment exactly matches the observations |
| S13 Validation report (D1) | All of items 1–7 in section 3, 6 core figures, limitations | Each figure makes one point clearly on its own |
| S14 Delivery | Dataset (CSV and Parquet), data card, AI usage statement, reference implementation of the anomaly indicators with standard test cases, HANDOFF.md | The front end can check its answers item by item |
| **S15 ★Milestone B** | One-command reproduction in a clean environment; publish Release v1; squash-merge into main | Reproduced results match the score table |

**Priority**: S00–S15 are all required. M2, M5 and sensitivity analyses (0.5°/1° grids) are done only after S15 is complete and if quota remains.

## 7. How it runs

- **Resources**: the download stages mainly use bandwidth; data processing and training run the CPU at full load with 10–20 GB of memory; no GPU is used; Claude itself uses almost no resources.
- **Class mode**: when you say "class is starting", background work drops to low priority with at most 8 threads; "class is over" restores full speed; "pause" stops after the current small unit finishes. You can interrupt at any time and lose at most one small unit.
- **Resuming**: each stage writes a `.done` marker and can be rerun; when resuming, read `PROGRESS.md` first. When quota runs out, the desktop app's auto-continue can keep going automatically, or a classmate can take over following `HANDOFF.md` (each person uses their own FIRMS key).
- **Secrets**: kept only in `.env`; scanned twice, before commit and in CI; no key values appear in the documents.
- **What you need to do**:
  1. choose the directory;
  2. run `gh auth login --web` once;
  3. turn on auto-continue and set the permission mode.
- Earthdata is not needed.

## 9. Execution organization: a new session per stage, ready for a relay at any time

- **Do not do everything in one very long conversation. Also do not go so fine-grained that every small task starts a conversation from scratch**: then the project has to be reread every time, which costs more quota and easily leads to inconsistencies.
- **Use one new session per stage**: each session starts from a task card and, when it ends, pushes all its results to GitHub:

| Session | Task card | Stages covered | What is on GitHub when it ends |
|---|---|---|---|
| 0 (this session) | — | Explainer + S00 | Plan, task cards, PROGRESS skeleton, HANDOFF, CI |
| 1 | `docs/sessions/1-data.md` | S01–S06 | Pre-registration, grader.yml, download and cleaning code, diagnostic plots; processed data as a Release asset |
| 2 | `2-baselines.md` | S07–S09 | Grader, fallback models, **milestone A data package** |
| 3 | `3-model.md` | S10 | LightGBM, experiments.csv, review notes |
| 4 | `4-freeze-test.md` | S11–S12 | Frozen manifest, blind-grading scores, final dataset |
| 5 | `5-report.md` | S13–S15 | Validation report, data card, **milestone B** |
| G (optional) | `G-global.md` | Global rerun | Global dataset |

- **Every task card is self-contained**: which files to read (the plan, PROGRESS, relevant ADRs), which stages to do, what the acceptance criteria are, and what to update at the end. Nothing depends on chat history.
- **Within a session**: commit and push after every stage (S level); during long stages, also push regularly along the way (for example after each experiment). If quota suddenly runs out, at most the small unpushed part is lost.
- **Between sessions**: when one session ends, I use the app's "new session" feature to prepare the next card, and you start it with one click; teammates can also run it on their own computers.

## 10. Relay design (handing over to teammates when quota runs out)

- **Code and documents**: all on GitHub.
- **Data**: tens of GB, kept out of git. At the end of each stage, the **processed data** (Parquet, about 1–2 GB) is uploaded as a GitHub Release asset with its SHA256 recorded. Teammates can download it directly, or rebuild from scratch with `python pipeline.py all`, with the raw data version pinned by hash.
- **Environment**: `uv sync` plus the lock file; code uses pathlib throughout and no PowerShell-only scripts, so it also runs on Mac and Linux, which CI verifies on Linux; LightGBM runs in deterministic mode with a fixed seed, so results are the same on any machine.
- **Secrets**: everyone requests their own FIRMS key (free, 1 minute) and puts it in their own `.env`.
- **Test set**: grading happens on GitHub Actions; the rules are the same whoever takes over, and the test can be taken only once.
- **`HANDOFF.md`** spells out: set up the environment → fill in the key → download the Release data → read PROGRESS → give the next task card to Claude (with a prompt that can be copied directly).
- **Requirements for a teammate's machine**: the data stages need about 50 GB of disk and 16 GB+ of RAM; later stages use the Release data directly and run on an ordinary laptop.

## 11. Zero-background relay: take over with a single prompt

**Goal**: someone who knows nothing about the project but has Claude Code or Codex quota, a computer and GitHub access can open GitHub and see how far the project has got. They copy one prompt into the AI, and the AI works out the current state itself and carries on.

### 11.1 "Self-describing" files in the repository (created in S00 and maintained by every session after that)

| File | Audience | Contents |
|---|---|---|
| "Current status" box at the top of `README.md` | People | A one-line status, e.g. "at session 2 of 5 (fallback models), next: task card 3"; the relay method in three steps, linking to HANDOFF |
| `HANDOFF.md` | People | Preparation checklist: install git/uv, clone, request a FIRMS key, how to fill in `.env`, how much disk is needed; **a copy-and-paste universal relay prompt (one in Chinese and one in English)** |
| `AGENTS.md` | AI (shared conventions for Codex, Cursor and others) | The full project rules: red lines (banned features, test-set isolation, do not change evaluation files); start-of-session routine (read progress → claim → preflight → execute the task card → push); environment preflight checklist; what to do when something is unclear |
| `CLAUDE.md` | AI (Claude Code) | A one-line `@AGENTS.md` reference, plus notes specific to Claude (for example the hook) |
| `PROGRESS.md` | People and AI | Starts with a machine-readable status block: current task card, status (ready/in_progress/blocked), claimant and claim time, last pushed stage, next step, things a person needs to do; below it, the stage table (status, completion time, key numbers, commit) and handover notes |
| `docs/sessions/N-*.md` | AI | Self-contained task cards: prerequisites (which stages are done, which Release data package is needed); **which plan sections to read, and only those**; which stages to do; acceptance criteria; what is not allowed; what to update at the end; which card comes next |

### 11.2 Universal relay prompt (always the same prompt; the AI works out the progress itself)

Prompt:
```
You are taking over an ongoing data-analysis project (MODIS x VIIRS active-fire harmonization). Follow the repository rules strictly; do not improvise.
1. First read AGENTS.md and PROGRESS.md and tell me in plain language: how far the project has got, which task card is next, and what I need to prepare.
2. Check the claim fields in PROGRESS.md: if someone else claimed the same card within the last 12 hours, stop immediately and tell me. Otherwise set the claimant to "[MY NAME]" with the current time, then commit and push.
3. Run the environment preflight from the checklist in AGENTS.md. For anything I must do myself (getting a FIRMS key, logging in to GitHub, installing software that needs approval), stop and walk me through it step by step.
4. Execute the task card, reading only the plan sections it names. After each stage: run the tests -> update PROGRESS.md -> commit -> push.
5. For any decision the task card does not cover, write it up in docs/decisions/ and mark it "awaiting human confirmation" in PROGRESS.md. Do not change the method, data splits or evaluation rules on your own.
6. When you are running out of quota or need to stop, push what is finished first, then write in PROGRESS.md exactly where you stopped and what comes next.
```
The same prompt is also in HANDOFF.md, for teammates.

**One-liner for a specific card** (to redo or run a specific stage): `Following the rules in AGENTS.md, execute docs/sessions/3-model.md.`

### 11.3 Preventing collisions and drift

- **Claim lock**: the claim in PROGRESS.md belongs to whoever pushes first. If a push is rejected, pull first, and stop if someone else has already claimed the card.
- **Resume points**: every stage can be rerun; for a stage marked in_progress in PROGRESS, the AI taking over checks it first and then decides whether to resume or redo it.
- **Quality gates**: every push must pass CI; every task card has acceptance criteria; the final test is graded by GitHub and can be taken only once, whoever takes over.
- **Guardrails live in CI, independent of which AI tool is used**: on every push, CI checks four things:
  - the hashes of frozen files (prepare, evaluate, grader, settings, holdout regions) have not changed;
  - the feature list contains no year, region-name or VIIRS columns;
  - no config or code requests downloads of 2012/2013 VIIRS;
  - no secrets are found by the scan.

  Violating commits turn red and cannot be merged. The Claude hook is only an earlier reminder. So whether the relay uses Claude Code or Codex, the rules are enforced equally strictly. Codex needs network access and command execution enabled, which AGENTS.md states.

### 11.4 Drill (one of the acceptance criteria for S00)

After S00 is done, I open a **brand-new session**, give it only the universal relay prompt, and ask it to "report only, do not execute". I check whether it correctly states the current progress, the next card and what a person needs to prepare. If it gets anything wrong, I revise AGENTS.md, PROGRESS.md or the task cards until it gets it right.

## 8. Validation (engineering)

- **pytest**:
  - grid totals are conserved; 0 and missing are kept separate;
  - edge cases for MALE, percentiles and anomaly indicators;
  - `predict()` cannot get the VIIRS columns or the year column;
  - the hook blocks download requests for locked data;
  - the grading workflow refuses a second run;
  - no key is found by the scan.
- Every push must pass CI; the score table is reproduced with one command in a clean environment.
- **Time**: milestone A is expected about 1 day after work starts; the whole thing in 3–5 days.
