# harmonization: map of the code

> The pipeline code, grouped by stage. To rebuild everything, run `uv run python -X utf8
> pipeline.py all --from-release` from the repo root; you rarely need to call a module directly.
> Files marked 🔒 are frozen (listed in `config/frozen-manifest.json`); only a human may change them.

Data flows from left to right: **download → import → cleaning → gridding → baselines → model → freeze and blind grading → dataset → reports**. [`pipeline.py`](../pipeline.py) in the repository root calls these modules in order and checks the results.

| Stage | Files | What they do |
|---|---|---|
| Shared | `config.py` | Paths and settings; secrets are read only from `.env` and never printed |
| S02 download | `download.py`, `crosscheck.py` | FIRMS annual archives and API, missing-data list, GFED; row-by-row spot check of the API against the annual archives |
| S03 import | `ingest.py` | Streams CSVs into Parquet; **holdout-region VIIRS is dropped right here** |
| S04 cleaning | `clean.py` | Cleaning by the rules in `config/settings.yaml` |
| S05 gridding | `grid.py` | 0.25° cell × calendar month × sensor counts, MODIS features |
| S06 health check | `explore.py` | The 4 figures of the data health check |
| S07 grader | `prepare.py` 🔒, `evaluate.py` 🔒, `final_test.py` 🔒, `judge_check.py` | Splitting the validation windows, scoring, the one-time blind grading (runs only on GitHub Actions) |
| S08 baselines | `baselines.py` | M0, M1s, QM, and the bridge and continuation |
| S10 model | `harmonize.py` 🔒, `autoexp.py`, `program.md`, `experiments.csv`, `s10_scores.py`, `model_review.py` | Implementations of all methods; the AI-driven automated experiment loop and its rules; the record of the 37 experiments; the score table; the independent review of the top 3 |
| S11 freeze | `freeze.py` 🔒 | Freezes the selected model (E028) and seals the blind-grading answer sheet |
| S09, S12 datasets | `series.py` (v0), `series_v1.py` (v1) | Generate the final monthly series, intervals and front-end files |
| S13 report | `validation.py` | The numbers and the 6 core figures of the validation report |
| S14 web page | `anomaly.py` | Reference implementation of the anomaly indicator, which the front end follows |
| G global | `global_grid.py`, `series_global.py` | Global grid and global rerun |

The full code of each experiment is on the `exp/lightgbm` branch; `experiments.csv` records all the experiments.
