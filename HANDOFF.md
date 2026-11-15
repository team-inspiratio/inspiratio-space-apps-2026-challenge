# HANDOFF: Relay guide

> You don't need to know this project. Prepare your machine with the checklist below, then copy the whole "universal relay prompt" into your AI tool (Claude Code or Codex). It will read the progress file itself and tell you where things stand and what you need to do.

## 1. Checklist

| Step | What to do |
|---|---|
| 1 | Install [Git](https://git-scm.com/downloads), [uv](https://docs.astral.sh/uv/getting-started/installation/) and [GitHub CLI](https://cli.github.com). |
| 2 | Run `gh auth login --web` and approve in the browser (you need access to this repository). |
| 3 | `gh repo clone team-inspiratio/inspiratio-space-apps-2026 inspiratio`, then `cd inspiratio` and `git switch feat/data-harmonization`. On Windows, first run `git config --global core.longpaths true` and put the project under a short path. |
| 4 | Get your own free FIRMS MAP_KEY (1 minute): <https://firms.modaps.eosdis.nasa.gov/api/map_key/>. |
| 5 | Copy `.env.example` to `.env` and fill in `FIRMS_MAP_KEY=your key` and `INSPIRATIO_DATA_DIR=data folder` (outside the repository, for example `D:/inspiratio-data` or `~/inspiratio-data`). **Never commit `.env`, send it to anyone, or paste it to an AI.** |
| 6 | Run `uv sync`, then `uv run pre-commit install`, then `uv run python tools/preflight.py` to see what is missing. |

**Machine**: the data stages (task cards 1 and G) need about 50 GB of disk and 16 GB+ of RAM; later stages download the processed data from GitHub Releases and run on an ordinary laptop. No GPU needed.

**AI tool**: Claude Code works out of the box (the repository ships its hook). Codex needs network access and command execution enabled.

## 2. Universal relay prompt

Use the same prompt every time; the AI works out the progress itself. Replace [MY NAME] with your name:

```
You are taking over an ongoing data-analysis project (MODIS x VIIRS active-fire harmonization). Follow the repository rules strictly; do not improvise.
1. First read AGENTS.md and PROGRESS.md and tell me in plain language: how far the project has got, which task card is next, and what I need to prepare.
2. Check the claim fields in PROGRESS.md: if someone else claimed the same card within the last 12 hours, stop immediately and tell me. Otherwise set the claimant to "[MY NAME]" with the current time, then commit and push.
3. Run the environment preflight from AGENTS.md. For anything I must do myself (getting a FIRMS key, logging in to GitHub, installing software that needs approval), stop and walk me through it step by step.
4. Execute the task card, reading only the plan sections it names. After each stage: run the tests -> update PROGRESS.md -> commit -> push.
5. For any decision the task card does not cover, write it up in docs/decisions/ and mark it "awaiting human confirmation" in PROGRESS.md. Do not change the method, data splits or evaluation rules on your own.
6. When you are running out of quota or need to stop, push what is finished first, then write in PROGRESS.md exactly where you stopped and what comes next.
```

## 3. One-liner for a specific card

To redo or run a specific card:

```
Following the rules in AGENTS.md, execute docs/sessions/3-model.md.
```

## 4. FAQ

- **Where does the data come from?** Session 1 downloads it from FIRMS and processes it; after that, every session ends by uploading the processed data as a GitHub Release asset, and `PROGRESS.md` records which Release to use and its SHA256. To download: `gh release download <tag> -D <your data folder>`.
- **What if CI goes red?** Paste the Actions error to the AI and have it fix the problem following AGENTS.md; if the error comes from the guardrails, a red line has been touched, so ask a person first.
- **What is the test set, and why can't I download 2012/2013 S-NPP data?** It is the answer key for the final exam. Only GitHub Actions downloads it in the cloud and scores the submission, and the test can be taken only once. The rules are the same whoever takes over.

## 5. Where the results are (from S14)

| You want | Look here |
|---|---|
| Headline results | [`reports/validation.md`](reports/validation.md) (validation report, 6 core figures + limitations), [`reports/final-test.md`](reports/final-test.md) (one-time blind-test scores) |
| The dataset | GitHub full Release `v1` (CC BY 4.0; the pre-release `dataset-v1` with the same content is kept as a historical record): `dataset_v1.parquet`, `dataset_v1.csv.gz`, `region_totals_v1.csv`, front-end `<region>.json.gz`. After downloading, check with `sha256sum -c SHA256SUMS.txt` |
| Data card | [`docs/data-card.md`](docs/data-card.md) |
| Front-end interface | [`docs/data-interface.md`](docs/data-interface.md) |
| How the anomaly indicator is computed and checked | Reference implementation [`harmonization/anomaly.py`](harmonization/anomaly.py), standard test cases [`docs/anomaly-cases.json`](docs/anomaly-cases.json) (25 of them, for the front end to check one by one) |
| AI usage statement | [`docs/ai-usage.md`](docs/ai-usage.md) |
| Decisions still open | `needs_human` in the `PROGRESS.md` status block; details in [`docs/decisions/`](docs/decisions/) |
| What next | After milestone B comes task card [`G-global`](docs/sessions/G-global.md) (global rerun). Before starting, read section 9 "Limitations" of the validation report: the error in the holdout regions is 2.5 times that in the training regions, so the global stage needs more training regions or must mark everything outside them as low confidence |

**Data only, no code**: with `gh` installed and logged in, run `gh release download v1 --repo team-inspiratio/inspiratio-space-apps-2026 -D <folder>` and read `data-card.md`; no FIRMS key is needed.
