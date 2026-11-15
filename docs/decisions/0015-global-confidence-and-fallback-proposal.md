# 0015 Proposal: confidence levels, M1s fallback and web-page labels for the global product

> **This is a proposal and has not been implemented.** No data, model or web page is changed. The facts about the global version come from `reports/global-scores.md`, `reports/global-review.md` and `docs/data-interface-global.md`, which were merged into `main` with PR #6.

## Background

`global-v1` is published: 278,192 cells × 312 months worldwide. Now we need to decide how it is presented on the web page and the project page, because the strength of the evidence differs greatly between cells:

| Evidence | Score | Which model it belongs to |
|---|---|---|
| Blind Test 1 (training regions) | MALE 0.258, M1s 0.332 | **The three-region model E028 (S11)** |
| Blind Test 2 (holdout regions) | MALE 0.644, M1s 0.857 | **The three-region model E028 (S11)** |
| Global validation windows | MALE 0.534, M1s 0.619 | The global retrain, **with no test scores** |

Three things are easy to get wrong:

1. **The global version never took the blind test.** ADR 0013 item 3 has confirmed this; the blind-test scores must not be credited to the global version.
2. **The three training boxes have different values in the global version than in v1.** The global version's boxes are cut out of the global model. On validation scores, the global model scores 0.352 on the demo regions and the three-region model 0.295, so the global version is actually worse there.
3. **Complete months from 2014 on are observations.** Apart from the holdout regions, every global cell is an S-NPP observation from 2014-01 on, so the confidence levels apply only to model-estimated months.

## Question 1: a confidence level for each cell

### Options

1. **Three levels**: training regions / holdout regions / rest of the world, exactly the split that was proposed.
2. **Three levels, with the third subdivided**: split the third level further by validation results, flagging the known worst regions and those where "M1s did better".
3. **No levels**, just one general explanation.

### Recommendation: option 2

| Level | Scope | Basis | Web-page label (English) |
|---|---|---|---|
| **1 Blind-tested regions** | The three boxes California, Córdoba, southern Africa | Test 1: annual total bias within ±9%, κ 0.69. **Holds only when v1 values are shown** | `Blind-tested region` |
| **2 Holdout regions: low confidence** | Northern Australia, central Siberia, Ganges Plain | Test 2: error 2.5 times the training regions'; interval coverage only 55.9%; every month is an estimate in the global version | `Held out · low confidence` |
| **3a Validation scores only** | The other GFED regions | Better than M1s on the validation windows, no blind test | `Validation only` |
| **3b Validation scores only, and the simple method did better** | CEAM, EQAS, NHSA, SHSA | See question 2 | `Validation only · simple ratio did better here` |
| **3c Low confidence** | BOAS, BONA, MIDE | Validation MALE 1.030, 0.648 and 0.896, among the worst (`docs/data-interface-global.md` section 4) | `Low confidence` |

Additional rules:

- **Judge again per month**: months with `source = snpp` are observations and always show `Observed`, with no level. Levels appear only on model-estimated months.
- **Terra-only months** (`model_terra_bridge`) are marked low confidence at every level.
- **A cell's level** is computed from three existing fields, `role`, `gfed_region` and `source`, so **no data needs to be republished**.
- **When an area the user draws spans several levels**, show the lowest one, with the note "the selected area includes low-confidence cells".
- Level 1's three boxes: in the six-region view the web page keeps using v1 values, and in the global view the global values; never mix the two in one calculation. When switching, note "two models, different values".

### Impact if not handled

Users will treat any point on the globe as having the "22% in the blind test" level of credibility. This is where we are most likely to be challenged.

## Question 2: fall back for the four regions where M1s did better?

In global validation, M1s beats E028 in 4 regions (MALE averaged over both windows, lower is better):

| Region | E028 global retrain | M1s | Difference | E028 above M1s by | QM | Three-region model (reference) |
|---|---:|---:|---:|---:|---:|---:|
| NHSA (northern South America) | 0.415 | 0.350 | +0.065 | 18.6% | 0.385 | 0.387 |
| CEAM (Central America) | 0.465 | 0.405 | +0.060 | 14.8% | 0.471 | 0.459 |
| SHSA (southern South America) | 0.519 | 0.456 | +0.063 | 13.8% | 0.490 | 0.593 |
| EQAS (equatorial Asia) | 0.491 | 0.479 | +0.012 | 2.5% | 0.484 | 0.515 |

The differences and percentages are computed from the numbers in the table. The report gives confidence intervals only for the three scopes all / GFED / demo, **not per region**, so we cannot tell whether these gaps are stable; the EQAS gap is especially small.

In addition, M1s also has smaller annual total bias at global scope (main window 0.055 versus 0.101, auxiliary window 0.069 versus 0.113).

### Options

| Option | What it does | Pros | Cons |
|---|---|---|---|
| **F0 No fallback** | Use E028 everywhere and label these 4 regions 3b | Consistent with ADR 0013 item 4, "whatever the scores, the production version is the global retrain"; no new data needed | The estimates for these 4 regions are known not to be the best |
| F1 Fall back in four regions | Use M1s for the model months of these 4 regions | Better validation scores in these 4 regions | It is **picking a model per region after seeing the validation scores**, which was not pre-registered; there is no test data to confirm it; the method would change abruptly at GFED region boundaries; the 16.75 interval factor was computed for E028 and would need recomputing; a new version must be published |
| F2 Show both | Keep the main values, and also provide an M1s column or CSV for these 4 regions | The main product is unchanged and users can compare for themselves | Another dataset must be published, and the web page needs another layer of explanation |

**Why F1 is not just a technical question**:

- Red line 5 says "may not be changed after seeing scores". ADR 0013 item 4 says these scores are "not used to pick a model", but also "written truthfully and left to a person to decide", so this is something a person can decide, not something an AI can just go ahead and do.
- Falling back in the losing regions picked out of 14 easily mistakes random fluctuation for a pattern.

### Recommendation: F0, no fallback

- Keep `global-v1` as it is, label the 4 regions 3b, and state truthfully on the project page "better than M1s in 10 of 14 regions, worse in 4".
- If a fallback is wanted, leave it for v2: **write the rule first** (for example, the gap must exceed some threshold, and which data confirms it), then test it on untouched data. The global version left no such test data, so this is genuine follow-up work.

## Question 3: how to label things on the web page and project page

- **Calendar and map**: put the level label next to the region title; for 3b, 3c and level 2, use a dashed frame or a pale hint, reusing PR #5's "low-confidence estimate" visual (hatching + dashed frame).
- **Hover text**: write the source and level like `Model estimate · Validation only`.
- **Explanatory text** (expanded by clicking the label, one or two sentences):
  - Level 1: `This region was part of a one-time blind test on 2012–13 data.`
  - Level 2: `This region was held out from training. Errors in the blind test were 2.5 times larger and totals ran low.`
  - 3a: `Compared with VIIRS on 2014–17 validation years only. No blind test.`
  - 3b: `On validation years a simple ratio did better here than the model.`
  - 3c: `Validation scores here are among the weakest worldwide. Treat as a rough estimate.`
- **Intervals**: call them a `rough range`, hidden by default. Do not call them an error bar or confidence interval (the median width of a global interval is 0.5–1.6 times the estimate, and about 19% have a lower bound of 0).
- **Project page**: write the blind-test scores and the global validation scores separately, stating clearly that "the global version has not been through the blind test".
- **Do not say**: "global accuracy", "accuracy", "validated everywhere".

## Status

**Awaiting human confirmation.** A person must decide:

1. The level scheme (three levels, or subdivided);
2. The fallback option (F0, F1 or F2);
3. Whether level 1's three boxes show v1 values or global values in the global view;
4. The English wording of the labels and explanations.

This record affects only presentation. Choosing F1 or F2 requires a new data version and a new ADR.
