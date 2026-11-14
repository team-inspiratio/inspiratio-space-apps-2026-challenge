# AGENTS.md: project rules for AI agents (shared by Claude Code, Codex and Cursor)

> Summary: this file is binding for any AI agent working in this repo. Read it fully, then
> `PROGRESS.md`, then the task card it points to. The red lines below are enforced by CI
> (`tools/guardrails.py`) no matter which AI tool you use.

## What the project is

We harmonize the hotspot records of MODIS (from 2000) and VIIRS (from 2012) into a **monthly series on the VIIRS scale** (0.25° cells × calendar months, 2000-11 to 2026-10) and hand it to the front end for the burning-calendar web page. This line of work in the repository covers only the data analysis and algorithms; teammates handle the front end, the proposal and the demo.

- **Single source of truth**: [`docs/execution-plan.md`](docs/execution-plan.md) (execution plan v4). [`docs/proposal.md`](docs/proposal.md) is background; where the two conflict, the execution plan wins.
- **Progress**: the status block at the top of [`PROGRESS.md`](PROGRESS.md).
- **Task cards**: [`docs/sessions/`](docs/sessions/), one card per session.
- **Relay guide for people**: [`HANDOFF.md`](HANDOFF.md).

## Red lines (if any one of them is crossed, stop at once and tell a person)

1. **Test-set isolation (plan section 4)**
   - This machine **never downloads** S-NPP VIIRS data for 2012 or 2013 (not as annual archives, not through the API, not from any mirror). Only the GitHub Actions grading workflow `grader.yml` may download it.
   - VIIRS records in the holdout regions (registered in `config/regions.json` in S01) are dropped during import and never written to disk. Before the model is frozen, holdout-region VIIRS is not looked at, plotted or summarized.
   - All download code must call `assert_download_allowed(source, start, end)` from `tools/guardrails.py` before sending any request.
   - The final test can be taken only once: pushing the `final-test` tag is a person's decision, and an AI must never push this tag on its own.
2. **Do not change frozen files**: the files listed in `config/frozen-manifest.json` (from S01: settings, holdout regions, grader; from S07: prepare, evaluate) may be changed only by a person. Unfreezing requires a person to write `[unfreeze]` in the commit message and give the reason.
3. **Banned features**: year, region name and any VIIRS information may not be used as model inputs. The feature list lives in `config/features.json`, and CI checks it.
4. **Secrets**: the FIRMS MAP_KEY lives only in `.env` (which is gitignored). Do not print it, read it into the conversation, or write it into any file, log, commit message or PR. In code, read it with `python-dotenv`.
5. **No improvising on methods**: the only models are M0, M1s, QM (quantile mapping) and LightGBM (plan section 2). Data splits, evaluation metrics and the selection rule all follow the plan and the pre-registration and may not be changed after seeing scores.
6. **Do not push directly to main**: work on the `feat/data-harmonization` branch and merge through a PR (squash-merge at S15).

The guardrails have three layers: the Claude Code hook (`.claude/settings.json`, the earliest block), pre-commit (before each commit) and CI (on every push, the final verdict). **Other tools such as Codex have no hook, so check yourself against the red lines**; CI will still mark violating commits red.

## Start-of-session routine (the same for every session)

1. **Read progress**: read this file and `PROGRESS.md`. Report to the person in plain language: how far the project has got, which task card is next, and what the person needs to prepare (see `needs_human` in the status block and "What a person must prepare" in the task card).
2. **Claim**: check `claimed_by` and `claimed_at` in the status block. If someone else claimed the same card within the last 12 hours, **stop at once** and tell the person. Otherwise fill in the claimant (ask the person for their name) and the current UTC time, change `status` to `in_progress`, then commit and push. If the push is rejected, run `git pull --rebase` first and check the claim again.
3. **Preflight**: run `uv sync`, then `uv run python tools/preflight.py` (add `--need-gb 50` for the data stages). For any `[FIX]` item, fix what you can yourself; for things the person must do in person (getting a FIRMS key, `gh auth login --web`, installing software that needs approval, filling in `.env`), stop and walk them through it step by step.
4. **Execute the task card**: read only the plan sections the task card names, and do the stages it lists, in order.
5. **After each stage (S level)**: `uv run pytest` → update `PROGRESS.md` (stage table, status block) → commit → push. During long stages, also push regularly along the way.
6. **Finish**: once every acceptance criterion on the task card passes, change the status block to the next card with `status: ready` and clear the claim; update the progress box at the top of the README to match; after pushing, confirm CI is green.

## When something is unclear

- For a decision that neither the task card nor the plan covers: write `docs/decisions/NNNN-short-title.md` (background, options, your recommendation), add an item "Awaiting human confirmation: …" to `needs_human` in `PROGRESS.md`, then **stop and ask a person**, or first do the parts that are not affected. Do not change the method, the data splits or the evaluation rules on your own.
- Anything the plan explicitly marks as "needs team confirmation" (for example the holdout regions) must wait for a person to confirm before it is committed.
- When you are about to run out of quota or must stop: push the finished parts first, then write in the "Handover notes" of `PROGRESS.md` exactly where you stopped, what comes next, and whether any half-finished files exist.

## Environment conventions

- Python 3.12, managed with `uv` (`uv sync` installs from `uv.lock`). No GPU needed.
- Use `pathlib` throughout, and do not write scripts that run only in PowerShell or only in bash; CI runs on Linux, which ensures Mac/Linux also work.
- Raw data and large processed files **stay out of git**; they go in the directory that `INSPIRATIO_DATA_DIR` in `.env` points to (on this machine `D:/inspiratio-data`). At the end of each data stage, the processed Parquet files are uploaded as GitHub Release assets and their SHA256 is recorded.
- Paths can get too long on Windows: the repository has `git config core.longpaths true` set, and the project lives under a short path.
- LightGBM runs in deterministic mode with a fixed seed.
- Each stage writes a `.done` marker (in the data directory) so runs can resume where they stopped.
- **Codex users**: you need to allow network access and command execution (downloading data, running tests and pushing all need them).

## Repository map

```
AGENTS.md / CLAUDE.md     AI rules (this file; CLAUDE.md references it)
PROGRESS.md               Progress status block + stage table + handover notes
HANDOFF.md                Relay guide for people + universal relay prompt
docs/execution-plan.md    Execution plan (the single source of truth)
docs/proposal.md          Original proposal (background)
docs/sessions/            Task cards: 1-data, 2-baselines, 3-model, 4-freeze-test, 5-report, G-global
docs/decisions/           Records of decisions awaiting or given human confirmation
config/                   settings, regions, features, frozen-manifest (from S01)
tools/guardrails.py       Guardrails (shared by CI, pre-commit and the hook)
tools/preflight.py        Environment preflight
tests/                    pytest
.claude/                  Claude Code hook
.github/workflows/        ci.yml (every push); grader.yml (committed in S01, external blind grading)
```

## Common commands

```bash
uv sync                                   # set up the environment
uv run python tools/preflight.py          # preflight
uv run pytest                             # tests
uv run ruff check . && uv run ruff format .
uv run python tools/guardrails.py check   # guardrails
uv run pre-commit install                 # install the pre-commit checks once per clone
```
