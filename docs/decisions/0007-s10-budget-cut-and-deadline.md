# 0007 S10 experiment budget cut and deadline

## Background

S10's budget was originally "at most 150 experiments or 8 hours; stop after 30 consecutive runs without a keep" (plan section 5). By E012 (about 00:00 UTC on 2026-11-04), each experiment took 4–13 minutes because of Optuna; at that pace the 8 hours would not be used up, but the run would take a lot of the user's time. At that point no experiment had passed the guardrails yet; the main problem was the zero-hotspot guardrail (see `harmonization/experiments.csv`).

The user relayed a decision through the S00 session. The user's words (translated from Chinese): "I just don't think it needs to be this meticulous. Can training be made faster? If so, speed it up as much as possible, because I don't have that much time to spend on this project." The following changes were made on that basis.

## Decisions (made by the user for time reasons; fixed before the results of the experiments after E013 came in)

1. **Run 2 experiments at a time**, each still fixed at 8 threads (ADR 0006 item 4), so the results are as reproducible as running them one by one. The runner `autoexp.py queue --jobs 2` records results in list order. Experiments in the same batch all start from the same base version; when an experiment is kept, the next batch starts from it.
2. **Optuna per experiment cut from 30 trials to 15.**
3. **The next structural experiment is a "two-stage" LightGBM**: first a classifier decides whether VIIRS has any fire in this cell this month; for those judged to have fire, a count model estimates the number; those judged to have no fire get 0 directly. This is the last major attempt at the zero-hotspot guardrail.
4. **Hard deadline: 03:30 UTC on 2026-11-04** (22:30 user local time). After that, no new experiments are started, and those already running are allowed to finish. Then the model is selected by pre-registration section 4: if no experiment passes, M1s is used. The review of the top 3 is simplified, and the task card is wrapped up.
5. **Remedy rule** (added by the user, also fixed before seeing later results): about 20 minutes before the deadline (around 03:10 UTC), if the 1–2 candidates closest to passing were run with 15 Optuna trials, rerun each once with 30 Optuna trials and **use the rerun's score** in the final selection. The rerun is recorded as a new row in `experiments.csv`, and the original row is kept. "Closest to passing" is judged in this order: first, whether it passes every guardrail; if none does, the one whose total excess over the guardrail tolerances (for example, how many percentage points the zero-hotspot share is over) is smallest. The user's words (translated from Chinese): "You should understand what result I really want. Just figure it out yourself, don't worry about all the miscellaneous stuff; whatever you think is best is best." Accordingly, the technical details of the experiments and the wrap-up are judged by the AI itself, with the results written into PROGRESS and this record.
6. **The frozen thresholds are unchanged**: the selection rule and guardrail tolerances in pre-registration section 4, the grader code and the data splits are not touched. The original limits (150 experiments, 8 hours, 30 consecutive runs without a keep) still apply, and the run stops at whichever comes first.

## What happened (added 2026-11-04)

- With two experiments in parallel, each experiment took about 2–3 minutes. The three queued batches (E015–E034) finished around 00:45 UTC, more than 2 hours before the deadline.
- **Wrapped up early**: the user wanted to spend less time, and the later variants' scores were all bunched between 0.293 and 0.305, with differences smaller than the variation caused by tuning itself (see the next item), so no further batch was started. The remedy reruns were done immediately after this batch rather than waiting until 03:10. Under the user's authorization to "judge technical details yourself", this decision is recorded here.
- **Remedy reruns**: the two closest to passing were E021 (0.2933, already passing the guardrails) and E016 (0.2936, already passing the guardrails, and the only one kept). After rerunning with 30 Optuna trials:
  - E035 (rerun of E021): combined MALE 0.2921, but the zero-hotspot share in the main window is over by 5.7 percentage points: **fails**;
  - E036 (rerun of E016): combined MALE 0.2997, passes, better than M1s by 0.077 ± 0.014.
  - By the rule, the rerun scores replace the original scores, so the top 3 became E028, E018 and E032 (all with 15 Optuna trials, scores 0.2947–0.2954). The same setup with a different tuning budget differs by 0.006 in score, and the differences among the top few are all within this range.
- 37 experiments in total (E000–E036). E019 and E020 have exactly the same setup (E020 did not specify the number of internal months, and by then the base had changed to E016's 24 months); their two results are bit-for-bit identical, which happens to show that parallel runs are reproducible.

## Impact

- There are fewer experiments than originally planned; S11 and the report must state truthfully that the run was "cut short for time reasons".
- The budget cut does not affect how any experiment is scored, so results before and after it in `experiments.csv` are directly comparable; only the number of Optuna trials (30 → 15) differs, which is recorded in the `config` column.

## Status

Confirmed: the user (relayed through the S00 session, words quoted above), 2026-11-04.
