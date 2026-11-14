# Decision records (decisions)

This folder holds decisions that neither the task cards nor the execution plan cover and that need a person to confirm. When an AI runs into one of these, it writes a record, adds an item "Awaiting human confirmation: …" to `needs_human` in `PROGRESS.md`, and then stops to ask a person (see "When something is unclear" in `AGENTS.md`).

- **File name**: `NNNN-short-title.md`, numbered in order starting from `0001`, for example `0001-holdout-regions.md`.
- **Each record has four parts**:
  1. **Background**: what problem came up, and why the task cards and the plan do not cover it.
  2. **Options**: the possible approaches, with the pros and cons of each.
  3. **Recommendation**: which option is recommended, and why.
  4. **Status**: `Awaiting human confirmation`, or `Confirmed` (state who confirmed it and when, for example "Confirmed: Zhang San, 2026-11-05").
- After confirmation the record is not deleted; only its status changes. If a decision is overturned, write a new record and note this in the old one.
