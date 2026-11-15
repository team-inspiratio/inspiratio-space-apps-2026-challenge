# 0011 S14: formats of the delivery files and details of the anomaly indicator

## Background

S14 on the task card requires delivering: the dataset (CSV and Parquet), the data card, the AI usage statement, a reference implementation of the anomaly indicator with standard test cases (for the front end to check its answers item by item), and an updated `HANDOFF.md`. The proposal's "Anomaly indicators" and section 6 of `docs/data-interface.md` set the rules, but for the front end and the reference implementation to produce the same answers item by item, a few more points have to be pinned down. None of the following changes any value in the dataset, and none touches the model or the evaluation.

## 1. Anomaly indicator: added details (`harmonization/anomaly.py`)

| Question | What was decided | Reason |
|---|---|---|
| When does the current month count as ended | When the as-of date (UTC) is no earlier than the 1st of the next month | Consistent with "calendar months counted in UTC" |
| How to judge floating-point "equality" | \|x − h\| ≤ 0.005 counts as equal, x < h − 0.005 as smaller | The front-end JSON gives only 2 decimal places, and an area the user draws sums many cells, so JS and Python additions may differ in the last digit; the tolerance keeps the same number from being judged two ways |
| Whether Terra bridge months belong in the reference set | Yes (as long as `input_complete = true`) | The rule excludes only years with missing data; bridge months are already flagged as low confidence in the data |
| The "S-NPP only" baseline period | Keep only months with `source = snpp` | The proposal's wording is "only complete S-NPP months"; 2012–2013 in the training regions are model estimates in v1 and do not count |
| Median of 0 | No multiple (none for anything < 5); the percentile as usual | Avoids division by 0; the proposal requires showing only the percentile when the median is small |
| Output format | A fixed set of 10 fields and 6 statuses (see section 6 of `docs/data-interface.md`) | So the front end can check its answers field by field |

- **Standard test cases** `docs/anomaly-cases.json`: 19 edge cases with expected values worked out by hand (the expected values are written in the code and were computed by hand, not by running the program), plus 6 examples using real regional totals from dataset v1 (their expected values are the reference implementation's output, to lock in its behavior on real data). `tests/test_anomaly.py` checks that the reference implementation matches every case, and that the hand-worked cases in the file are the same as in the code.
- **Needs confirmation from the front end**: the front end must follow these details too. If the front end has already done it differently, this record prevails, or a person decides which side to change.

## 2. CSV format (`dataset_v1.csv.gz`)

- The same table as the Parquet, with the same column order; gzip-compressed (about 18 MB; about 260 MB uncompressed); UTF-8, LF line endings; the gzip timestamp is fixed at 0, so the same input gives the same bytes on any machine.
- An empty field = no data (consistent with nulls in the Parquet); numbers are kept to 6 significant digits (relative error below 5 × 10⁻⁶ compared with the Parquet's float32, checked column by column); booleans are written as `True`/`False`.
- Generated with `uv run python -X utf8 -m harmonization.series_v1 package` (it only builds the CSV from the existing Parquet, copies the documents and recomputes the SHA256, without retraining the model); `build` also does this step along the way.

## 3. Data card and AI usage statement

- `docs/data-card.md` follows the structure of an ESSD data paper (sources, processing, uncertainty, validation, limitations, suitable and unsuitable uses, citation) and is **written in English**, because it is published with the public data and its readers are not limited to the team; a summary in Chinese was at the end (replaced by an English short summary in the English translation).
- `docs/ai-usage.md` had an English and a Chinese version (the English translation keeps only the English one); its content comes from the repository's records (Co-Authored-By lines in git commits, `experiments.csv`, the decision records), and it covers only what this line of work (data analysis and algorithms) used.
- **The license awaits a person's decision**: the proposal suggests CC BY 4.0. Choosing a license is the team's call; the data card says "CC BY 4.0 suggested; to be confirmed by the team before public release".

## Status

The technical details in items 1–3 were decided by the AI under the user's authorization (ADR 0007 item 5), 2026-11-04. **The license has been confirmed by the user: CC BY 4.0** (2026-11-04, published with Release v1). The front end must be told about the anomaly indicator details (item 1).
