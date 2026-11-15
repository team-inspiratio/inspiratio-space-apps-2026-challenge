# Project page draft

> **草稿。11/13 官方指南发布后逐项核对。** DRAFT: check every item against the official Project Submission Guide published on November 13. The structure follows `docs/proposal.md` (2025 rules).
>
> Square brackets mark things only people can fill in. Every number comes from `reports/`; see "Where the numbers come from" at the end. Do not add a number that is not in that table.

---

## Title and one-line summary

**Fire Atlas: one fire record across two satellite generations**

We put 26 years of NASA satellite fire detections on one consistent scale, so fire activity before and after the 2012 sensor change can be compared, and built a web page to explore it month by month.

## The problem

NASA's FIRMS fire record comes from two sensor generations. MODIS has flown since 2000. VIIRS joined in 2012 and sees far more: in southern Africa, S-NPP VIIRS recorded 4.8–5.6 times as many detections per year as Aqua MODIS over the same fires in 2014–2021.

Join the two records as they are and fire activity appears to jump about five times at 2012. Nothing happened on the ground. The sensor changed.

The timing matters. S-NPP stopped delivering data to FIRMS on November 2, 2026, and NASA says Terra and Aqua will stop operating between late 2026 and early 2027. Without a common scale, the long fire record breaks exactly at this handover.

## What we did

1. **A harmonization model** that estimates what S-NPP VIIRS would have recorded, using MODIS inputs only.
2. **An open dataset**: monthly counts on a 0.25° grid, November 2000 to October 2026 (312 months), for six study regions. Every value is flagged as observed or estimated. A separate global version covers 278,192 cells.
3. **Fire Atlas, a web page**: pick a region or draw your own, read a calendar of 26 years, check whether the latest month is above or below its usual level, and download the data.

## Method

We processed 529 million FIRMS records (444 million after cleaning) from four satellites: Terra, Aqua, S-NPP and NOAA-20.

- **Learn from the overlap.** In 2014–2021 both sensors were flying. A two-stage LightGBM model first decides whether VIIRS would see any fire in a cell-month, then estimates how many detections. Inputs are MODIS only. Year, region name and any VIIRS information are forbidden as inputs.
- **Estimate the earlier years.** The model runs on MODIS inputs back to 2000. Months with only Terra are flagged low confidence.
- **Keep the observations.** In the training regions, complete S-NPP months from January 2014 are shown as observed.

## How we know it works

**Rules first, then a single blind test.** Metrics, data splits and the selection rule were pre-registered and frozen before any model was fitted. The test answers were never on the development machine during the project: a GitHub Actions grader downloaded them and scored our sealed submission once. The model was not changed afterwards.

Scores are MALE, a log error where lower is better. It is not an accuracy percentage.

| Method | Test 1: training regions, 2012–13 | Test 2: regions the model never saw, 2012–21 |
|---|---:|---:|
| Our model (LightGBM E028) | **0.258** | **0.644** |
| Simple ratio (M1s) | 0.332 | 0.857 |
| Quantile mapping | 0.431 | 0.866 |
| Direct splice | 1.813 | 2.263 |

- **Training regions:** 22% lower error than the simple ratio, matching the validation result. Yearly totals were within 9% of true VIIRS.
- **Regions the model never saw:** still better than the simple ratio, but errors are about **2.5 times larger**. Yearly totals ran 22–35% low in the Indo-Gangetic Plain and 14–45% low in central Siberia. Northern Australia stayed within 5% through 2019. Two guardrail checks on low-fire months failed here. We report that rather than hide it.
- **Independent check:** against GFED burned area, detections per km² keep the same level across 2012 after harmonization (southern Africa 2.77 before, 2.92 after), while the direct splice jumps about five times. GFED only reaches 2016 here and is itself derived from MODIS, so this is a plausibility check.
- **For the page's actual job:** "above, near or below normal" labels agree with true VIIRS at Cohen's κ 0.69 in training regions (good) and 0.53 in unseen regions (moderate).

**The global version has not been blind-tested.** It is a separate refit of the same frozen settings on global training cells. On validation windows only, its MALE is 0.534 against 0.619 for the simple ratio, and it beats the ratio in 10 of 14 GFED regions. The simple ratio did better in the other four: Central America, Equatorial Asia, and both South American regions.

## Impact and users

**Intended users** are fire and emergency planners and researchers who need to compare a recent month with a long history on one scale. A planner could see which months usually see the most detections, check whether the latest month is unusual, and take the table into a report alongside weather and ground information.

**[We have not tested this with real users. Replace this sentence only if that changes.]** The scenario above is illustrative. This is a record of past detections. It does not predict fires, measure burned area or judge damage.

## NASA data used

| Data | Link | How we used it |
|---|---|---|
| MODIS Collection 6.1 active fires, Aqua (FIRMS) | <https://firms.modaps.eosdis.nasa.gov/download/> | Main model input, 2002-07 to 2026-10 |
| MODIS Collection 6.1 active fires, Terra (FIRMS) | <https://firms.modaps.eosdis.nasa.gov/download/> | Model input; the only input before Aqua has complete months |
| VIIRS S-NPP 375 m active fires, VNP14IMG (FIRMS) | <https://firms.modaps.eosdis.nasa.gov/download/> | The target scale: training labels 2014-01 to 2021-06; observed months from 2014-01 |
| VIIRS NOAA-20 375 m active fires, VJ114IMG (FIRMS) | <https://firms.modaps.eosdis.nasa.gov/download/> | Scaled to stand in for S-NPP months with missing days |
| FIRMS API and missing-data list | <https://firms.modaps.eosdis.nasa.gov/api/> | 2026 data; marks incomplete months so they are never treated as zero |
| FIRMS attribute documentation | <https://earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs> | Field definitions and quality filters |

**Other data (not NASA-hosted):** GFED4.1s burned area, based on MODIS MCD64A1, used only as a plausibility check. Map tiles from OpenStreetMap; land outlines from Natural Earth.

## Limits and next steps

- **Reliable in the three training regions** (California, Córdoba, southern Africa). Elsewhere, treat values as low-confidence estimates.
- **Training regions in 2012-02 to 2013-12 are estimates**, because those years were the locked test.
- **Ranges are rough.** They show how much an estimate moves with other training years. They are not error bars. After calibration they covered the truth 95.5% of the time in training regions but only 55.9% in unseen regions. Global ranges are wider still: a typical width is 0.5–1.6 times the estimate.
- **Weakest places:** boreal forests (central Siberia MALE 1.14) and places with very little fire, where the model can invent small counts.
- **Latitude acts as a region label** in the model, one reason unseen regions do worse.
- **NOAA-20 months are scaled.** [Do not call them seamless unless the team accepts the criterion in ADR 0005 item 4.]
- **Next:** more varied training regions, land-cover inputs, and a new blind test on untouched data before claiming improvement.

## SI usage statement

Space Apps asks every team to describe how it used Super Intelligence (SI) tools.

- **Claude Code (Anthropic)** wrote and ran the data pipeline, ran 37 model experiments, and drafted the reports and decision records. Commits it made are marked in the git history.
- **A fresh-context Claude sub-agent** independently reviewed the top three models for leakage.
- **Codex (OpenAI)** generated the first version of the web page; Claude Code then revised it.
- **[Add here any SI used for the video, slides or images.]**

**What people did:** approved the plan and scope, chose the holdout regions on geography and ecology alone, reviewed the grading code before freezing it, decided to cut the experiment budget, pushed the tag that started the one-time test, and approved releases.

**How we kept the AI honest:** pre-registration, a test the AI could not see, three layers of automated guardrails, frozen files that only a person can change, and full reporting of weak results. Most code was checked by tests, CI and the independent AI review rather than read line by line by a person.

## Links and references

- **Web page:** [final URL, see ADR 0016]
- **Code:** [repository URL; the repository is private today]
- **Dataset:** [Release v1 and global-v1 URLs], CC BY 4.0
- **Code license:** [none yet; the team must choose one]
- **Validation report:** [URL of `reports/validation.md`]

**Data acknowledgement.** We acknowledge the use of data and imagery from NASA's Fire Information for Resource Management System (FIRMS) (<https://www.earthdata.nasa.gov/firms>), part of NASA's Earth Science Data and Information System (ESDIS).

**References.**

- Schroeder, W., Oliva, P., Giglio, L., & Csiszar, I. A. (2014). The New VIIRS 375 m active fire detection data product: Algorithm description and initial assessment. *Remote Sensing of Environment*, 143, 85–96.
- van der Werf, G. R., et al. (2017). Global fire emissions estimates during 1997–2016. *Earth System Science Data*, 9, 697–720.
- [Complete list required: the rules ask teams to cite every source, including open-source software. See `checklist.md`.]

---

## Where the numbers come from（提交前删掉这一节）

| 数字 | 出处 |
|---|---|
| 4.8–5.6 倍；跳约 5 倍 | `reports/validation.md` 结论第 1 条 |
| S-NPP 11-02 停止、Terra/Aqua 退役时间 | `docs/proposal.md` “三条会改变设计的最新情况”（FIRMS 和 Earthdata 公告） |
| 312 个月、六区 | `docs/data-card.md` “At a glance” |
| 278,192 个格子 | `reports/global-review.md` 第 1 节 |
| 5.29 亿 → 4.44 亿；四颗卫星 | `PROGRESS.md` S04、`docs/data-card.md` 第 1 节 |
| 成绩表 | `reports/validation.md` 第 1 节（M0 取 1.813，原始值 1.8135） |
| 低 22%；±9%；2.5 倍 | `reports/final-test.md` 第 1、3 节，`reports/validation.md` 结论 |
| −22～−35%、−14～−45%、北澳 ±5% | `reports/final-test.md` 第 3 节 |
| 两项护栏不合格 | `reports/final-test.md` 第 3 节 |
| 2.77 / 2.92；GFED 到 2016 | `reports/validation.md` 第 4 节、局限第 8 条 |
| κ 0.69 / 0.53 | `reports/validation.md` 第 3 节（原始 0.686 / 0.534） |
| 0.534 / 0.619；四个区 | `reports/global-scores.md` 第 1、2 节 |
| 95.5% / 55.9% | `reports/validation.md` 第 5 节 |
| 全球区间 0.5–1.6 倍 | `reports/global-review.md` 第 3 节（“0.50 倍”到“约 1.6 倍”） |
| 中西伯利亚 1.14 | `reports/final-test.md` 第 2 节 |
| 37 次实验 | `docs/ai-usage.md`、`reports/validation.md` 第 7 节 |

**写作注意**：不要写 accuracy 或“准确率 XX%”；不要写 error bar、forecast、burned area；不要把 22% 说成全球成绩。
