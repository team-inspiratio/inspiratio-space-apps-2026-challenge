# SIMULATION: this is a rehearsal repository

## What this is

- Team Inspiratio built this whole project (data track S00-S15, the global stage G, two versions
  of the web page, and the submission drafts) in a private draft repository on **2026-11-02 to
  2026-11-08**, before NASA Space Apps 2026 (November 14-15).
- This repository **replays that finished work in stages, in the order it was really done**, to
  rehearse publishing an entry: one push per stage, then a check that CI, links and files work.
- **Commit times in this repository are replay times, not development times.** Nothing in the
  replay stages was developed during the event window. Every replay commit message names the
  draft snapshot it comes from and that snapshot's original commit time.
- At each stage the files are identical to the draft snapshot, with two additions: this file and
  the notice at the top of `README.md`.
- Commits made after the last replay stage (for example the English translation of the documents)
  are new work and say so in their messages.

## Who replays what

Each stage is pushed by the team member whose work that snapshot mostly is in the draft history:

- **A**: data and algorithms track (S00-S15 and the global stage G)
- **B**: repository kickoff, submission preparation and web v1
- **C**: web V2

## Replay schedule

Planned times are US Central Time (CST, UTC-6). The commit log has the actual push times.

| Stage | By | Planned CST | Planned UTC | Content | Draft snapshot | Original commit time | State |
|---|---|---|---|---|---|---|---|
| P00 | B | 11-14 16:01 | 11-14 22:01 | Kickoff: proposal, README overview, env template | `c90e9b1` | 2026-11-02 21:34 | pushed |
| P01 | A | 11-14 17:16 | 11-14 23:16 | S00: environment, three-layer guardrails, CI, relay docs; holdout regions recorded (ADR 0001) | `2c37cf3` | 2026-11-03 13:44 | pushed |
| P02 | A | 11-14 17:37 | 11-14 23:37 | S01: preregistration, frozen before any modelling (settings, holdout regions, scoring rectangles, grader.yml) | `569256a` | 2026-11-03 14:05 | pushed |
| P03 | A | 11-14 17:58 | 11-14 23:58 | S02-S03: download and ingest (holdout-region VIIRS dropped at import) | `84abd8c` | 2026-11-03 15:52 | pushed |
| P04 | A | 11-14 18:21 | 11-15 00:21 | S04-S06: cleaning, gridding and features, data health check; task card 1 done | `aa48ed0` | 2026-11-03 16:56 | pushed |
| P05 | A | 11-14 18:39 | 11-15 00:39 | S07: judge code (prepare, evaluate, final_test), frozen after human review | `e19f26c` | 2026-11-03 17:38 | pushed |
| P06 | A | 11-14 19:02 | 11-15 01:02 | S08-S09: baselines M0/M1s/QM, dataset v0; milestone A | `25d7785` | 2026-11-03 17:50 | pushed |
| P07 | A | 11-14 19:26 | 11-15 01:26 | S10: LightGBM, 37 experiments, model review | `1922079` | 2026-11-03 21:52 | pushed |
| P08 | A | 11-14 19:44 | 11-15 01:44 | S11: select E028 by the preregistered rule, freeze, seal the final-test submission | `674b3f5` | 2026-11-03 22:36 | pushed |
| P09 | A | 11-14 20:07 | 11-15 02:07 | S11 blind-test results; S12 final dataset v1 | `13c19b9` | 2026-11-03 23:32 | pushed |
| P10 | A | 11-14 20:31 | 11-15 02:31 | S13-S14: validation report, data card, AI usage statement, anomaly reference implementation; first pipeline.py | `c856c50` | 2026-11-04 00:18 | pushed |
| P11 | A | 11-14 20:52 | 11-15 02:52 | S15: one-command reproduction; milestone B | `e8a260e` | 2026-11-04 01:56 | pushed |
| P12 | A | 11-14 21:13 | 11-15 03:13 | G: global rerun (global validation scores, interval calibration, global dataset) | `5b2f73b` | 2026-11-04 17:51 | planned |
| P13 | B | 11-14 21:34 | 11-15 03:34 | Submission prep: review packet, ADRs 0014-0016, submission drafts, demo routes | `39a0298` | 2026-11-04 17:12 | planned |
| P14 | B | 11-14 21:57 | 11-15 03:57 | Web v1 (Fire Atlas): source, fixes, methods and validation page | `1ecdb87` | 2026-11-04 17:53 | planned |
| P15 | C | 11-14 22:18 | 11-15 04:18 | Web V2 and final README | `35e8bd0` | 2026-11-08 17:09 | planned |

## What is not replayed

- **The `final-test` tag.** Project rules say only a person may push it, and the external blind
  test runs once. It ran on 2026-11-03 in the draft repository; its result files
  (`results/final-test/`) arrive unchanged at P09. The tag will not be pushed here.
- **GitHub Releases (data assets).** `data-v0`, `milestone-a`, `dataset-v1`, `v1` and `global-v1`
  live in the private draft repository. Project rules say a person approves each release, so they
  were not copied automatically. Until a person publishes them here, links to Releases in the
  documents do not open from outside.
- **Branches and pull requests.** The draft repository used branch, pull request, merge to main.
  This is a linear replay.
- **The original commit history.** It contains team members' personal email addresses and is not
  published.

## AI use

The replay is run with AI coding agents at the team members' request. For AI use in the project
itself see `docs/ai-usage.md` (from P10).
