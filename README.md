# MODIS × VIIRS Hotspot Harmonization / Harmonized Fire Record

**One consistent monthly fire record from 2000 to 2026, across two generations of NASA satellites.**

**[Open the public V2 fire activity explorer](https://team-inspiratio.github.io/inspiratio-space-challenges-2026/)** · [V2 source and setup](frontend-v2/README.md)

We bring the hotspot records of two satellite generations, MODIS (from 2000) and VIIRS (from 2012), onto one monthly series that can be compared across the whole period: global 0.25° cells, 2000-11 to 2026-10.

![Direct stitching creates a false step in 2012; the harmonized record joins up](reports/figures/d1-1-problem.png)

## The one-minute version

- **Problem**: VIIRS is much more sensitive than MODIS, and for the same fires it counts several times as many hotspots. Stitching the two periods together directly creates a **false step in 2012 caused by the change of satellite**, not by any real change in fire activity.
- **Approach**: train a model (a two-stage LightGBM) on the years when both satellites were in orbit, inferring from MODIS information alone "how many hotspots VIIRS would see", then apply this conversion to the years before 2012.
- **Proof**: the scoring rules were written and frozen before any results were seen; the test data is scored only in the GitHub cloud, and **the test is taken only once**.
- **Results**:
  - External blind grading: error 22% lower than the simple ratio method, and 25% lower in regions never seen before ([blind-test scores](reports/final-test.md));
  - Global validation: error 14% lower than the simple ratio method ([global scores](reports/global-scores.md));
  - Globally, 16.0 million hotspots in 2013 (model) and 16.6 million in 2014 (observed): no break at the handover.
- **Scale**: 529 million raw hotspot records, 4 satellites, 26 years; 278,000 cells and 86.8 million cell-months worldwide.

## I want to…

| I want to | Go here |
|---|---|
| **Use the data directly** | Use the bundled [global frontend assets](inspiratio-site/public/data/global-v1/) (CC BY 4.0). See [available public files](docs/public-data.md) and the [data card](docs/data-card.md). No account or key needed |
| **Build the web page** | The [front-end brief](docs/frontend-agent-brief.md) (including an opening prompt for an AI agent), plus the interface specs [`data-interface.md`](docs/data-interface.md) and [`data-interface-global.md`](docs/data-interface-global.md) |
| **See the method and the evidence** | The [validation report](reports/validation.md), then the [project journey](docs/project-journey.md) (why each decision was made) |
| **Understand the whole plan** | The [full proposal](docs/proposal.md) |
| **Rerun everything** | Use `uv run python -X utf8 pipeline.py all` with your own FIRMS key and data directory. Processed-data Release shortcuts are not currently available; see [public data availability](docs/public-data.md) |
| **Continue development** | [HANDOFF.md](HANDOFF.md) (relay guide), [PROGRESS.md](PROGRESS.md) (progress) |

<!-- PROGRESS-BOX:BEGIN -->
> **Status**: all data-track task cards are done (S00–S15 and global stage G). This public repository includes the global frontend assets, source and reports. It currently has no GitHub Release assets; see [public data availability](docs/public-data.md).
<!-- PROGRESS-BOX:END -->

## Repository layout

Each main directory has its own README explaining what every file in it does.

```
README.md            This file: start here
docs/                Documents: for people first, process records after   → docs/README.md
reports/             Result reports and figures                            → reports/README.md
harmonization/       Data processing and model code, by stage              → harmonization/README.md
results/             Freeze and blind-grading records (do not change)      → results/README.md
config/              Regions, scoring rectangles, settings, feature list (mostly frozen)
pipeline.py          Rerun all results and check them with one command
tests/               Automated tests (uv run pytest)
tools/               Guardrails, environment preflight
notes/               Study notes

Files for AI agents (people need not read them):
AGENTS.md, CLAUDE.md Rules an AI must follow (red lines, start-of-session routine)
PROGRESS.md          Machine-readable progress status
.claude/, .github/   AI hook; CI and the cloud grading workflow
```

## About AI

The data and algorithm part of this project used AI (Claude Code) heavily. People made the key decisions: choosing the holdout regions, pushing the blind-grading tag, approving the releases. The AI wrote the code and ran the experiments, and every technical decision is written into the [decision records](docs/decisions/). To prevent "changing things after seeing the answers", the project has three layers of automatic guardrails (hook, pre-commit check, CI). See the [AI usage statement](docs/ai-usage.md).

## Conventions

- Changes go through branches and pull requests; do not push directly to main.
- Secrets live only in a local `.env` and never enter the repository.
- Raw data and large files stay out of the repository; processed data is published as Release assets with recorded SHA256.
