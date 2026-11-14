# SIMULATION: this is a rehearsal repository

## What this is

- Team Inspiratio built this whole project (data track S00-S15, the global stage G, two versions
  of the web page, and the submission drafts) in a private draft repository on **2026-11-02 to
  2026-11-08**, before NASA Space Apps 2026 (November 14-15).
- This repository **replays that finished work in stages, in the order it was really done**, to
  rehearse publishing an entry: one push per stage, then a check that CI, links and files work.
- **Commit times in this repository are replay times, not development times.** Nothing here was
  developed during the event window. Every commit message names the draft snapshot it comes from
  and that snapshot's original commit time.
- At each stage the files are identical to the draft snapshot, with two additions: this file and
  the notice at the top of `README.md`.

## Replay schedule

Planned times are US Central Time (CST, UTC-6). The commit log has the actual push times.

| Stage | Planned CST | Planned UTC | Content | Draft snapshot | Original commit time | State |
|---|---|---|---|---|---|---|
| P00 | 11-14 16:01 | 11-14 22:01 | Kickoff: proposal, README overview, env template | `c90e9b1` | 2026-11-02 21:34 | pushed |
| P01 | 11-14 16:52 | 11-14 22:52 | S00: environment, three-layer guardrails, CI, relay docs; holdout regions recorded (ADR 0001) | `2c37cf3` | 2026-11-03 13:44 | planned |
| P02 | 11-14 17:26 | 11-14 23:26 | S01: preregistration, frozen before any modelling (settings, holdout regions, scoring rectangles, grader.yml) | `569256a` | 2026-11-03 14:05 | planned |
| P03 | 11-14 18:16 | 11-15 00:16 | S02-S03: download and ingest (holdout-region VIIRS dropped at import) | `84abd8c` | 2026-11-03 15:52 | planned |
| P04 | 11-14 19:07 | 11-15 01:07 | S04-S06: cleaning, gridding and features, data health check; task card 1 done | `aa48ed0` | 2026-11-03 16:56 | planned |
| P05 | 11-14 19:54 | 11-15 01:54 | S07: judge code (prepare, evaluate, final_test), frozen after human review | `e19f26c` | 2026-11-03 17:38 | planned |
| P06 | 11-14 20:49 | 11-15 02:49 | S08-S09: baselines M0/M1s/QM, dataset v0; milestone A | `25d7785` | 2026-11-03 17:50 | planned |
| P07 | 11-14 22:23 | 11-15 04:23 | S10: LightGBM, 37 experiments, model review | `1922079` | 2026-11-03 21:52 | planned |
| P08 | 11-14 23:31 | 11-15 05:31 | S11: select E028 by the preregistered rule, freeze, seal the final-test submission | `674b3f5` | 2026-11-03 22:36 | planned |
| P09 | 11-15 00:08 | 11-15 06:08 | S11 blind-test results; S12 final dataset v1 | `13c19b9` | 2026-11-03 23:32 | planned |
| P10 | 11-15 01:44 | 11-15 07:44 | S13-S14: validation report, data card, AI usage statement, anomaly reference implementation; first pipeline.py | `c856c50` | 2026-11-04 00:18 | planned |
| P11 | 11-15 02:42 | 11-15 08:42 | S15: one-command reproduction; milestone B | `e8a260e` | 2026-11-04 01:56 | planned |
| P12 | 11-15 03:19 | 11-15 09:19 | G: global rerun (global validation scores, interval calibration, global dataset) | `5b2f73b` | 2026-11-04 17:51 | planned |
| P13 | 11-15 04:31 | 11-15 10:31 | Submission prep: review packet, ADRs 0014-0016, submission drafts, demo routes | `39a0298` | 2026-11-04 17:12 | planned |
| P14 | 11-15 05:39 | 11-15 11:39 | Web v1 (Fire Atlas): source, fixes, methods and validation page | `1ecdb87` | 2026-11-04 17:53 | planned |
| P15 | 11-15 06:11 | 11-15 12:11 | Web V2 and final README | `35e8bd0` | 2026-11-08 17:09 | planned |

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

The replay is run by Claude Code at a team member's request. For AI use in the project itself see
`docs/ai-usage.md` (from P10).
