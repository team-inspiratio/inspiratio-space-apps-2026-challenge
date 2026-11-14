# Task card 5-report: validation report, delivery, milestone B (S13–S15)

> Before starting, read progress, claim the card and run the preflight following the "Start-of-session routine" in [`AGENTS.md`](../../AGENTS.md).

## Prerequisites

- S11–S12 are done: the blind-grading scores have been committed back to the repository by CI, and the final dataset has been published as a Release asset.
- If this machine has no data: download it from the Release recorded in `PROGRESS.md` and check the SHA256.

## What a person must prepare

- Ask a person to read through the validation report and the data card.
- Before merging into main in S15, ask a person to confirm (repository convention: changes go through PRs, never pushed directly to main).

## Plan sections to read (only these)

From [`docs/execution-plan.md`](../execution-plan.md): section 1 (paper standards), section 3 (validation items 1–7), the S13–S15 rows of the table in section 6, section 8 (engineering validation), and section 10. For details, see the proposal's "D1", "D2", "D3" and "Anomaly indicators".

## Stages to do

### S13 Validation report (D1)

- Complete all of items 1–7 in section 3: the MALE main metric and auxiliary metrics; 95% block-resampling intervals for the score differences between LightGBM and M1s and QM (no p-values); validation by use case (Cohen's κ for high/normal/low); the plausibility check against the independent GFED reference; uncertainty coverage (calibrated with validation-set residuals if needed); the era-shift investigation; the record of how the selection rule was applied.
- 6 core figures, each able to make one point clearly on its own; write up the limitations. The report goes in `reports/validation.md`.

### S14 Delivery

- Dataset (CSV and Parquet), data card (ESSD style: sources, processing, uncertainty, limitations), AI usage statement, reference implementation of the anomaly indicators with standard test cases (so the front end can check its answers item by item), and an updated `HANDOFF.md`.

### S15 ★Milestone B

- One-command reproduction in a clean environment (for example `uv run python pipeline.py all`), with results matching the score table.
- Publish Release v1; after a person confirms, squash-merge `feat/data-harmonization` into main.

## Acceptance criteria

- Each figure makes one point clearly on its own; the front end can check its answers item by item against the standard test cases; reproduction in a clean environment matches the score table.

## Not allowed

- Changing already-reported test scores to make them look better; describing the stability interval as "the true value falls inside it 90% of the time".
- Merging into main without a person's confirmation.

## When finished, update

- `PROGRESS.md` stage table rows S13–S15; status block: if quota remains and a person agrees, change it to `current_card: docs/sessions/G-global.md`, `status: ready`; otherwise `status: done`. Update the README progress box to match. CI green.

## Next card

[`G-global.md`](G-global.md) (planned work; on 2026-11-03 the user agreed to extend to global coverage)
