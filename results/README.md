# results: freeze and blind-grading records

> Tamper-evident records of the freeze and the one-shot blind test. Do not edit; most of
> these files are frozen (see `config/frozen-manifest.json`).

| File | Contents |
|---|---|
| `freeze.json` 🔒 | The frozen model (E028), parameters, numbers of trees, resampling seeds, interval factor |
| `submission.parquet` 🔒 | The sealed blind-grading answer sheet: submitted after the freeze and before the test data was seen |
| `final-test/` | Raw output of the GitHub Actions grader: scores, provenance record, SHA256 of the locked data |
| `expected/` | Expected hashes for the reproduction check (`pipeline.py` uses them to verify that a rerun matches bit for bit) |

The readable version of the scores is in [`reports/final-test.md`](../reports/final-test.md).
