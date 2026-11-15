# docs: map of the documents

> Human-facing docs are in the first table; everything below it is a process record kept for
> audit and reproducibility. You rarely need the second half.

## For people (read these first)

| File | For whom | Contents |
|---|---|---|
| [`proposal.md`](proposal.md) | Everyone | The full plan: problem, approach, web page, validation, execution handbook |
| [`project-journey.md`](project-journey.md) | Whoever writes the proposal, makes the demo or builds v2 | What happened over the two days, the results, the reason for each key decision, weaknesses, what is still missing for a paper |
| [`data-card.md`](data-card.md) | Data users | Data card: sources, processing, uncertainty, limitations, citation (in English, with a short summary) |
| [`data-interface.md`](data-interface.md) | Front end | Fields, JSON format, source flags, user-selected areas, anomaly indicators (demo-region version `v1`) |
| [`data-interface-global.md`](data-interface-global.md) | Front end | How the global version `global-v1` differs from `v1` |
| [`frontend-agent-brief.md`](frontend-agent-brief.md) | AI agent building the web page | A one-page brief and an opening prompt |
| [`ai-usage.md`](ai-usage.md) | Judges, readers | Where AI was used in the project and which decisions people made |
| [`anomaly-cases.json`](anomaly-cases.json) | Front end | The 25 standard test cases for the anomaly indicator |

## Process records (for audit and reproduction; usually not needed)

| File or directory | Contents |
|---|---|
| [`decisions/`](decisions/) | Decision records (ADR 0001–0013): every technical decision the plan did not cover, with background, options and reasons |
| [`preregistration.md`](preregistration.md) | Pre-registration: the scoring, data splits and model-selection rule fixed before any result was seen (frozen) |
| [`execution-plan.md`](execution-plan.md) | The execution plan for the data track, the single source of truth for AI sessions |
| [`sessions/`](sessions/) | Task cards: which stages each AI session does |
| `data-manifest.csv`, `ingest-ledger.csv`, `api-ledger.csv` | Download and import manifests, with file hashes |
| `crosscheck-api-vs-yearly.csv` | Row-by-row spot check of the FIRMS API against the annual archives |
| `cleaning-counts.csv`, `removed-sample.csv` | How many rows each cleaning rule removed, and the spot check of removed samples |
| `firms-missing-data.csv`, `month-status.csv` | The FIRMS missing-data list, and whether each sensor is complete in each month |

These files are referenced by path from the code and from frozen files, so they were not moved into subdirectories.
