# reports: result reports

> Start with `validation.md` (the main report) and `final-test.md` (the one-shot blind test).
> Each `.md` has a `.json` twin with the same numbers for machines; `figures/` holds the PNGs.

| Read first | Contents |
|---|---|
| [`validation.md`](validation.md) | **Main report**: 6 core figures, every check, limitations |
| [`final-test.md`](final-test.md) | External blind-grading scores: taken only once, in the GitHub cloud |
| [`global-scores.md`](global-scores.md) | Global validation scores, listed by the 14 GFED regions |
| [`global-review.md`](global-review.md) | Checks and review points before the global dataset was published |

| Process reports | Contents |
|---|---|
| [`cleaning.md`](cleaning.md) | Cleaning: how many rows each rule removed, spot-check results |
| [`findings.md`](findings.md) | Findings of the data health check (S06) |
| [`judge-check.md`](judge-check.md) | Self-check of the grader |
| [`scores-v1.md`](scores-v1.md) | Baseline score table (S08) |
| [`scores-s10.md`](scores-s10.md) | Score table of the top 3 LightGBM (S10) |
| [`model-review.md`](model-review.md) | Independent review of the top 3: leakage checks, risks |

Figures are in [`figures/`](figures/): `a5-*` are the data health check, `d1-*` the validation report, and `s10-*` the model explanation.
