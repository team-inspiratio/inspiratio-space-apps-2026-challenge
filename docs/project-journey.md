# Project journey: methods, results, and decisions

> **Summary:** a distilled record of the data/algorithm track: stages,
> numbers, the decisions that mattered and why, known weaknesses, and what a v2 or a paper would
> need. It replaces reading the raw AI conversation logs: it keeps the reasoning, not the chatter.
> Each claim points to the report or ADR that holds the evidence.

The data track was completed by a person and several AI sessions in relay: one session per task card, plus a top-level session that coordinated. The raw conversations were not uploaded; they are too long and too messy. Only what later readers (front end, proposal writers, demo makers, v2 developers) really need is kept here. The evidence is in the reports and in [`docs/decisions/`](decisions/).

## 1. Development stages

| Stage | Result |
|---|---|
| S00 environment | uv, three layers of guardrails (hook, pre-commit, CI), relay documents |
| Task card 1: S01–S06 | Pre-registration and freeze; downloaded 529 million hotspot records, 444 million after cleaning; 0.25° × month gridding; data health check |
| Task card 2: S07–S09 | Grader (frozen); baselines M0, M1s, QM; dataset v0; milestone A |
| Task card 3: S10 | 37 rounds of LightGBM experiments (E000–E036), selecting the two-stage E028 |
| Task card 4: S11–S12 | Freeze; a person pushed the `final-test` tag; one blind grading run in the GitHub cloud; final dataset v1 |
| Task card 5: S13–S15 | Validation report, delivery files; one-command reproduction (87 minutes, all 37 checks pass); merged into main; Release `v1` |
| G: global rerun | 278,000 cells worldwide; validation scores; intervals; Release `global-v1` |

## 2. Results at a glance

- **Blind grading (taken only once)**: on Test 1 (training regions, 2012–2013), E028's error is 22% lower than M1s's; on Test 2 (holdout regions never seen), 25% lower. But the error in the holdout regions is 2.5 times that in the training regions, and totals are too low ([`reports/final-test.md`](../reports/final-test.md)).
- **Global validation**: after retraining on global data, MALE is 0.534 versus 0.619 for M1s, 14% lower; it wins in 10 of the 14 GFED regions ([`reports/global-scores.md`](../reports/global-scores.md)).
- **No break**: 16.0 million hotspots globally in 2013 (model) and 16.6 million in 2014 (observed) ([`reports/global-review.md`](../reports/global-review.md)).
- **Reproducible**: from a fresh clone, the single command `pipeline.py all` matches all 37 checks bit for bit (ADR 0012).

## 3. Key decisions and the reasons

1. **Pre-registration + freeze + external blind grading taken only once**: this machine never downloads the 2012–2013 S-NPP data; only GitHub Actions can download it and score. The aim is to prevent "changing the model after seeing the answers". The cost is that once the test is taken, this data can no longer be used to prove improvements; the benefit is that the scores stand up, which is where we are more rigorous than most entries.
2. **Two-stage (hurdle) LightGBM**: most cell-months have 0 hotspots. A plain regression sprinkles small fractional estimates where there is no fire and gets caught by the "zero-hotspot guardrail": among rectangles whose true value is 0, the share with an estimate ≥ 1 may be at most 5 percentage points higher than M1s's. So first decide "is there fire", then estimate "how much" (ADR 0007, 0008).
3. **Cutting the S10 budget**: Optuna went from 30 trials to 15, two experiments ran in parallel, a deadline was set, and the two candidates closest to passing (E016, E021) were rerun with 30 trials, with the rerun scores used in the selection. The reason was limited time; the rules were fixed before the results were seen (ADR 0007).
4. **Fixed 8 threads, no GPU**:
   - LightGBM's results depend on the thread count, and only a fixed thread count reproduces bit for bit.
   - The pip build of LightGBM has no GPU support; GPUs also use a different floating-point order, which would break bit-for-bit reproduction.
   - At the data size at the time (a few million rows), a GPU would not have been much faster.
5. **The global version is retrained on global data**: a model trained on only 3 demo regions underestimates in places it has not seen. After the global retrain, the global validation score dropped from 0.563 to 0.534. The cost is that the global version's model is not the one that took the blind test, which the interface document states (ADR 0013 item 3).
6. **Global intervals use only 50 resamples**: the plan was 100, but memory was enough for only one process at a time (each process peaks at 17–21 GB at startup on a 31 GB machine). The first 50 of the S11 sealed draws were used, which still reproduces bit for bit (ADR 0013 item 5 addendum).
7. **Re-deriving the interval widening factor**: resampled intervals reflect only "how much a different set of training years would change things" and are too narrow. They are calibrated on the validation windows to actually cover 90%: 5.37 for the demo regions, 16.75 globally.

## 4. Known weaknesses (written up honestly in the reports)

- **Too low in places not seen before**: the error in the holdout regions is 2.5 times that in the training regions, and totals are 20–35% too low. The global retrain improves this, but the boreal forests (BOAS, BONA) are still the worst.
- **The tropical forest regions do worse than the baseline**: Central America, the northern and southern parts of South America, and equatorial Asia are 3–14% worse than M1s. Possibly because fire there is mainly slash-and-burn clearing of rainforest, which follows different patterns from savanna fire.
- **Bias in regional annual totals**: the global version is off by 10% on average, M1s by 5–7%. Individual cells are more accurate, but the sums are biased.
- **Scattered false hotspots**: where the true value is 0, the share with an estimate ≥ 1 is 4.9%, versus 1.7% for M1s. Within what the guardrail allows.
- **Very wide intervals**: a typical global interval is 0.5–1.6 times the estimate wide. On the web page they can only be called a "rough range".

## 5. Looking back: what could have been done better

- **The plan was a first draft written by an AI, not a rule.** We should have asked "is there a faster or better way?" before freezing. For example, intervals could have used **conformal prediction** (using validation errors directly, with no retraining) or **quantile regression** (2 extra trainings), computable in minutes instead of hundreds of retrainings. Raising this before the freeze costs almost nothing; after the freeze, one can only wait.
- **The global stage was limited by memory, not CPU.** 31 GB of memory is enough for only one global resampling process at a time. Next time, running on a machine with 64 GB or more, or reading the table in chunks to lower the peak, would help more than a different CPU or a GPU.
- **A GPU only pays off at tens of millions of rows.** To use one, first take the time to compile the CUDA build of LightGBM, and accept "consistent within a tolerance" instead of "bit-for-bit consistent", written into a decision record.

## 6. What a v2 or a paper still needs

What we have now is a solid engineering prototype: pre-registered, blind-graded and reproducible, which already goes beyond many papers in this field. A paper would still need:

| What is missing | How to add it |
|---|---|
| Comparison with prior work | A literature review; head-to-head comparison with existing MODIS/VIIRS harmonization methods and the FireCCI and GFED products |
| Novelty | Argue the case for a "pre-registered, blind-graded cross-sensor harmonization pipeline", and ask an expert advisor whether it is enough |
| Independent validation | Landsat or Sentinel burned area, ground records |
| Ablation experiments | Remove features one by one and swap models, to see how results change |
| Explaining causes | Add features such as land cover, and analyze why the tropical regions and boreal forests do worse |
| A new blind test | After improving the model (land-cover features, regional-total calibration, a higher "fire" threshold, conformal intervals), hold out **a new, untouched block of data** and test once more |

Rough estimate: the part an AI can do is 1–2 weeks (including machine run time); the review cycle is 3–9 months.

## 7. Decisions people made

Confirmed the holdout regions; pushed the `final-test` tag; agreed to publish `v1`, merge into main and choose CC BY 4.0; authorized the AI to decide technical details on its own; approved using 50 resamples for the global intervals; agreed to publish `global-v1`. Everything else was decided by the AI under that authorization and recorded in the ADRs; see [`docs/ai-usage.md`](ai-usage.md).
