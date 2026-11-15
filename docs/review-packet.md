# Human review packet: get through every item awaiting confirmation in one hour

> **Status: to be filled in by people.** This document only organizes the items and makes recommendations; it does not mean any decision has been made. The sign-off fields are filled in by people; the AI does not fill them in for anyone.
>
> **Basis**: the project review items in `PROGRESS.md` and the decision records linked below.

## How to use this file

1. Ten minutes before the meeting, everyone reads "Terms you may not know" and the agenda below.
2. Follow the agenda: group A is discussed and decided item by item; for group B the owner gives a one-sentence conclusion; groups C and D are ticked off together.
3. For each item, write down the decision, the name and the date. After deciding, the data owner writes the results back into `PROGRESS.md` and the corresponding ADR.

## One-hour agenda

| Group | Contents | Time | Items |
|---|---|---|---|
| A | Must be decided in person | 35 minutes | X1, X2, items 1, 12, 14 |
| B | Everyone must be able to explain | 15 minutes | Items 7, 8, 10, 13 |
| C | Look over and tick | 7 minutes | Items 3, 4, 9, 15, 16, 17, 18 |
| D | Confirm they can be closed | 3 minutes | Items 2, 5, 6, 11, 19, 20 |

Suggested owners are given by role; the team fills in the names: **Data** (data owner qiuxue-yee), **Front end** (web page owner), **Whole team**.

| Role | Items they must be able to explain |
|---|---|
| Data | Items 2, 3, 4, 9, 12, 13, 14, 15, 16, 17, 18, 20 |
| Front end | X1, items 1, 5, 6, 11, 19 |
| Whole team (everyone must know these) | X2, items 7, 8, 10 |

## Terms you may not know

| Term | In plain words |
|---|---|
| Hotspot | When a satellite finds a small patch of ground that is especially hot, it records a point. A hotspot is not the same as a fire |
| MODIS / VIIRS | The old and new generations of satellite cameras. VIIRS sees finer detail and counts several times as many points for the same fires |
| Harmonization | Converting the old camera's records to the new camera's scale, so that before and after 2012 can be compared |
| Aqua, Terra, S-NPP, NOAA-20 | Satellite names. The first two carry MODIS, the last two VIIRS |
| MALE | Our error score; lower is better. **It is not accuracy and must not be described as "XX% accuracy"** |
| M1s | The simple ratio method, the fallback method used for comparison |
| E028 | The model finally chosen (two-stage LightGBM): first decide whether there is fire, then estimate how much |
| Training regions | California, Córdoba, southern Africa. The model learned from these three places |
| Holdout regions | Northern Australia, central Siberia, India's Ganges Plain. Deliberately hidden from the model and used for the test |
| Test 1 / Test 2 | Test 1: training regions, 2012–2013. Test 2: holdout regions. Each taken only once |
| Frozen | A locked file that only a person can unlock; the AI cannot change it |
| Interval | How much the estimate would move with a different set of training years; **not an error bar and not a confidence interval** |
| ADR | Decision record, in `docs/decisions/` |

---

## Group A: must be decided in person

### X1. Check the deployed front-end version

The front-end source is available in `archive/` and `website/`. Confirm that the public deployment matches the intended version; merging source does not automatically update the separately hosted site. See [web setup](../archive/README.md) and [V2 setup](../website/README.md).

### X2. The repository is private and has no LICENSE file

- **In one sentence**: the competition terms require the team's original content to be freely available or under an open-source license, and require all sources to be cited; our repository and Releases are currently private, and the code has no license file.
- **Options**:
  1. Make the repository public before submission, add a code license (for example MIT or Apache-2.0), and keep the data under CC BY 4.0.
  2. Make only a slimmed-down new repository public, with the code, data and documents.
  3. Keep it private.
- **Recommendation and reason**: choose 1. The direction of the terms is openness, and going public also opens up GitHub Pages as a deployment option. Before going public, a person should go through the history once (the secret-scanning CI has always passed). Which license to choose is the team's call.
- **Impact if not handled**: judges cannot open the code and data, which may not comply with the terms.
- **Related**: [Participant Terms & Conditions](https://www.spaceappschallenge.org/legal/); [ADR 0016](decisions/0016-deployment-options.md).
- **Suggested owner**: Whole team.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 1: should the web page use the global data global-v1?

- **In one sentence**: the global version is published (CC BY 4.0), and the web page currently has only six regions; decide whether to add the global version before the competition.
- **Options**:
  1. First get the six-region version fixed and online, and add the global version as a second step, skipping it if there is no time.
  2. Go all-out to switch to the global version before the competition.
  3. Do not add the global version.
- **Recommendation and reason**: choose 1. The six-region version has blind-test scores and has been verified; the global files are much larger (the largest is about 57 MB uncompressed), and how to label them is not yet decided (ADR 0015). Secure a version that can be demonstrated first.
- **Impact if not handled**: the front end does not know how far to go, and the submission materials cannot settle how to describe the "coverage".
- **Related**: [`docs/data-interface-global.md`](data-interface-global.md), [`reports/global-review.md`](../reports/global-review.md); [ADR 0015](decisions/0015-global-confidence-and-fallback-proposal.md).
- **Suggested owner**: Front end.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 12: the training regions use estimates for 2012–2013

- **In one sentence**: the plan originally used real observations for these two years, but the rules say this machine never fetches these two years of data (they are the test answers), so they are currently model estimates.
- **Options**:
  1. Keep things as they are (the recommendation in ADR 0009).
  2. The test is over, so a person unlocks them and replaces them with real observations (new proposal [ADR 0014](decisions/0014-unlock-2012-2013-snpp-observations-proposal.md)).
- **Recommendation and reason**: first confirm that "publishing the current v1 under option 1 is fine"; this only ratifies the status quo. Decide separately on unlocking under ADR 0014; do not mix the two.
- **Impact if not handled**: the status quo is unaffected, but the web page and data card keep showing "awaiting human confirmation".
- **Related**: [ADR 0009 item 1](decisions/0009-s12-production-model-and-final-series.md), [ADR 0014](decisions/0014-unlock-2012-2013-snpp-observations-proposal.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 14: does the NOAA-20 continuation count as "continuous"?

- **In one sentence**: months with missing S-NPP data are filled in with converted NOAA-20; the pass criterion was proposed **after seeing the test results**, so a person must decide whether to accept it.
- **Options**:
  1. Accept the suggested criterion: the median monthly total bias of each region within ±5%, and at least 80% of "region × year" units within ±10%. By this criterion it passes (medians −0.3% to +3.1%, 13 of 15 within ±10%).
  2. Do not accept it; use a stricter criterion or do not claim continuity.
- **Recommendation and reason**: choose 1, and externally say only "scaled NOAA-20", not "seamless". The criterion was proposed after the fact, which must be stated truthfully.
- **Impact if not handled**: until a person decides, neither the web page nor the project page may claim the NOAA-20 segment is continuous.
- **Related**: [ADR 0005 item 4](decisions/0005-fallback-bridge-continuation-v0-sources.md), section 5 of [`reports/scores-v1.md`](../reports/scores-v1.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

---

## Group B: everyone must be able to explain

### Item 7: read through the data card and the AI usage statement

- **In one sentence**: these two files are how the team describes the data and its AI use to the outside world, and the competition requires explaining how AI (officially called SI) was used when submitting.
- **Options**: agree after reading; or propose changes.
- **Recommendation and reason**: read and agree. Note that `docs/ai-usage.md` on `main` covers only the data track; the front-end part is on `feat/web` and will be complete only after merging.
- **Impact if not handled**: the description of AI use at submission may be incomplete, while the organizers require every project to provide one.
- **Related**: [`docs/data-card.md`](data-card.md), [`docs/ai-usage.md`](ai-usage.md).
- **Suggested owner**: Whole team.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 8: read through the validation report

- **In one sentence**: the report concludes that the three training regions are trustworthy, and other regions can only be treated as low-confidence estimates.
- **Options**: agree after reading; or raise questions.
- **Recommendation and reason**: everyone should remember three sentences: direct stitching conjures up a jump of about 5 times in 2012; in the training regions the blind test is 22% lower than the simple ratio method; in the holdout regions the error is 2.5 times that in the training regions.
- **Impact if not handled**: in the defense or on the project page, numbers may be overstated, especially accuracy outside the training regions.
- **Related**: [`reports/validation.md`](../reports/validation.md).
- **Suggested owner**: Whole team.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 10: look over the final test scores

- **In one sentence**: the blind test was taken only once: Test 1 MALE 0.258 (M1s 0.332), Test 2 MALE 0.644 (M1s 0.857); two guardrail metrics failed in the holdout regions, which was reported truthfully, and the model was not changed.
- **Options**: look over and agree; the scores can no longer be changed.
- **Recommendation and reason**: look over and agree. Externally, use the per-region figures in section 3 of `reports/final-test.md` for how far too low the holdout regions are: Ganges Plain about −22% to −35%, central Siberia about −14% to −45%, northern Australia within ±5% before 2019. "20–35%" is a summary that does not fully match the per-region figures; suggest not quoting it on its own.
- **Impact if not handled**: inconsistent external numbers invite questions.
- **Related**: [`reports/final-test.md`](../reports/final-test.md), [`results/final-test/`](../results/final-test/).
- **Suggested owner**: Whole team.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 13: look over the S10 model review notes

- **In one sentence**: all top 3 passed the "did it peek at the answers" review, but the review pointed out that latitude acts as a label for "which region this is", so new regions may do worse; Test 2 confirmed that the error does get larger.
- **Options**: look over and agree.
- **Recommendation and reason**: look over and agree. When explaining weaknesses externally, this item can be used directly to explain "why it gets worse in a different place".
- **Impact if not handled**: we cannot explain the model's limitations clearly and are on the back foot when judges ask.
- **Related**: [`reports/model-review.md`](../reports/model-review.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

---

## Group C: look over and tick

These have all been done as recommended; people only need to be aware of them. Objections are welcome and will be recorded separately.

### Item 3: the global version's model and interval factor (confirmed)

- **In one sentence**: when the user approved publishing global-v1, they also confirmed: the global version is retrained on global data, and **it is not the model that took the blind test**; the interval widening factor is recomputed, at 16.75 (5.37 for the six-region version).
- **Options**: be aware.
- **Recommendation and reason**: be aware. Everyone must remember that the global version has only validation scores (MALE 0.534, M1s 0.619) and no test scores; the blind test's 22% must not be presented as a global score. The global intervals are very wide: the median width is 0.5–1.6 times the estimate, and about 19% have a lower bound of 0.
- **Impact if not handled**: not blocking, but getting it wrong externally would be false advertising.
- **Related**: [ADR 0013 items 3 and 5](decisions/0013-g-global-rerun-method.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 4: the S15 acceptance did not rerun from the very raw data

- **In one sentence**: the acceptance started from the grid tables in the Release and all 37 checks passed, but the roughly 50 GB of raw data was not downloaded again.
- **Options**: accept; or arrange a full rerun separately.
- **Recommendation and reason**: accept. The reasons: the annual archives are pinned by hash, the 2026 API data changes on any re-download anyway, and it would use up FIRMS quota.
- **Impact if not handled**: not blocking. When saying "one-command reproduction" externally, state that it is the `--from-release` entry point.
- **Related**: [ADR 0012 item 1](decisions/0012-s15-one-command-reproduction-scope.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 9: the methods for S13's GFED check and era-shift investigation

- **In one sentence**: these two methods were fixed after the test and only describe the data, without changing any score.
- **Options**: accept; or ask for different methods and recompute the descriptive numbers.
- **Recommendation and reason**: accept. GFED only going to 2016 is a data limitation; the original source of "VIIRS counts 70% more in the literature" could not be found, so not comparing is right.
- **Impact if not handled**: not blocking.
- **Related**: [ADR 0010](decisions/0010-s13-validation-report-details.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 15: the Terra bridge in the holdout regions uses the local ratio (recorded)

- **In one sentence**: for early Terra-only months, the holdout regions are converted with their own MODIS ratio rather than the training regions' ratio; VIIRS is never touched.
- **Options**: be aware; raise objections if any.
- **Recommendation and reason**: be aware. This differs from the literal wording of the proposal's "no local ratio estimate", but the test period does not use the bridge, so the scores are not affected.
- **Impact if not handled**: not blocking.
- **Related**: [ADR 0005 item 6](decisions/0005-fallback-bridge-continuation-v0-sources.md), [ADR 0009 item 3](decisions/0009-s12-production-model-and-final-series.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 16: QM, λ, bridge years, v0 source rules

- **In one sentence**: these are technical details of the fallback models, all fixed before seeing scores.
- **Options**: accept; or point out an item that must change (which would require a new data version).
- **Recommendation and reason**: accept. They do not affect the final model's test scores.
- **Impact if not handled**: not blocking, but this item has been "awaiting human confirmation" for a long time; suggest closing it.
- **Related**: [ADR 0005 items 1–3 and 5](decisions/0005-fallback-bridge-continuation-v0-sources.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 17: details of the S10 LightGBM and experiment loop (recorded)

- **In one sentence**: the user authorized the AI to decide technical details, and the AI accordingly chose the tuning approach, the fixed 8 threads and so on.
- **Options**: be aware.
- **Recommendation and reason**: be aware. The write-up should mention that "two gray-area approaches were deliberately not taken", which is a plus.
- **Impact if not handled**: not blocking.
- **Related**: [ADR 0006](decisions/0006-lightgbm-and-experiment-loop-details.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 18: the S10 budget cut and deadline (recorded)

- **In one sentence**: the experiment budget was cut for time reasons, to 37 experiments in total (limit 150); this was the user's own decision.
- **Options**: be aware.
- **Recommendation and reason**: be aware. The AI usage statement already says so truthfully.
- **Impact if not handled**: not blocking.
- **Related**: [ADR 0007](decisions/0007-s10-budget-cut-and-deadline.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

---

## Group D: confirm they can be closed

These are "tell the front end" items or environment tips that the repository records show are out of date or done (item 1's notice about the global version is not done yet, so it is in group A). Please have the owner confirm and then remove them from `needs_human`.

### Item 2: merge the G-global PR (done)

- **In one sentence**: The global stage's code, reports and ADR 0013 are all on `main`.
- **Options**: close.
- **Recommendation and reason**: close; done.
- **Impact if not handled**: none.
- **Related**: [Global implementation decisions](decisions/0013-g-global-rerun-method.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 5: tell the front end that Release v1 is published

- **In one sentence**: the front end is already using Release v1 (`scripts/prepare-data.mjs` checks against v1's checksum list).
- **Options**: close.
- **Recommendation and reason**: close; done.
- **Impact if not handled**: none, only a longer list.
- **Related**: `archive/scripts/prepare-data.mjs` (`feat/web`).
- **Suggested owner**: Front end.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 6: tell the front end about the anomaly indicator reference implementation and the 25 cases

- **In one sentence**: the front end passes all 25 cases field by field (`archive/test/anomaly.test.mjs`, all passing when PR #5 was verified).
- **Options**: close.
- **Recommendation and reason**: close; done. The front end implemented the details in ADR 0011 item 1.
- **Impact if not handled**: none.
- **Related**: [ADR 0011 item 1](decisions/0011-s14-delivery-formats-and-anomaly-details.md), [`docs/anomaly-cases.json`](anomaly-cases.json).
- **Suggested owner**: Front end.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 11: tell the front end about the pre-release dataset-v1

- **In one sentence**: superseded by the full release v1, which is what the front end uses.
- **Options**: close.
- **Recommendation and reason**: close; out of date.
- **Impact if not handled**: none.
- **Related**: [`docs/data-interface.md`](data-interface.md).
- **Suggested owner**: Front end.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 19: tell the front end about the milestone-a pre-release

- **In one sentence**: an earlier version, likewise superseded by v1.
- **Options**: close.
- **Recommendation and reason**: close; out of date.
- **Impact if not handled**: none.
- **Related**: comment on PR #2.
- **Suggested owner**: Front end.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

### Item 20: GitHub CLI login tip

- **In one sentence**: this is an environment tip for relays, not an item awaiting decision.
- **Options**: close, or move it to `HANDOFF.md` (where it is already written).
- **Recommendation and reason**: close.
- **Impact if not handled**: none.
- **Related**: section 1 of [`HANDOFF.md`](../HANDOFF.md).
- **Suggested owner**: Data.

| Decision | Name | Date |
|---|---|---|
|  |  |  |

---

## Appendix: small issues found during the inventory (no meeting needed; the owner handles them)

| Issue | Current state | Suggestion |
|---|---|---|
| Last digits of numbers differ between reports | `reports/final-test.md` gives Test 1 total bias 4.8%, seasonal correlation 0.999 and Test 2 bias 18.4%; `reports/validation.md` gives 4.7%, 0.998 and 18.3%. The raw scores are 0.04746, 0.99848 and 0.18348 | Externally, follow `validation.md`, as the submission materials already do. Whether to change `final-test.md` is a person's decision |
| How the gap in the four tropical regions is described | `docs/project-journey.md` (data branch) says "3–14% worse than M1s"; computed from `reports/global-scores.md`, E028's MALE is higher than M1s's by about 2.5% (EQAS) to 18.6% (NHSA) | The data owner corrects it at the next update |
| Access scope of the live site | `archive/README.md` says "Sites private access", but on 2026-11-04 the home page and data files opened without logging in | Confirm in a private browsing window, then change the README or the access settings |
