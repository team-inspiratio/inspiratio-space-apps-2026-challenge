# Data card: harmonized MODIS × VIIRS active-fire counts, dataset v1

> 中文摘要见文末。This card follows the structure an Earth System Science Data (ESSD) data
> description asks for: sources, processing, uncertainty, validation, limitations. Column-level
> details for developers are in [`data-interface.md`](data-interface.md); the full validation is
> [`reports/validation.md`](../reports/validation.md).

## At a glance

| | |
|---|---|
| **What** | Monthly counts of satellite active-fire detections on a 0.25° grid, on one consistent scale: what the S-NPP VIIRS 375 m sensor would have recorded. Before 2012 (MODIS only) the values are model estimates. |
| **Why** | VIIRS records about 5 to 10 times more fire pixels than MODIS for the same fires. Joining the two records as they are creates a false jump in 2012. This dataset removes that sensor jump so months can be compared across 2000-2026. |
| **Where** | Six 7°-10° boxes: three training regions (California, USA; Córdoba, Argentina; southern African miombo savanna) and three holdout regions never used in training (northern Australia; central Siberia; Indo-Gangetic Plain). Boxes in `config/regions.json`. |
| **When** | 2000-11 to 2026-10, calendar months (UTC), 312 months. |
| **Size** | 2,615,808 cell-months (8,384 cells × 312 months). |
| **Version** | v1, 2026-11-04. Model LightGBM E028, frozen before a one-time blind test. |
| **Files** | `dataset_v1.parquet` and `dataset_v1.csv.gz` (same table), `region_totals_v1.csv`, one `frontend/<region>.json.gz` per region, `resamples20_v1.parquet`, `meta.json`, `SHA256SUMS.txt`, on the GitHub release of this repository. |
| **License** | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (confirmed by the team, 2026-11-04). The input data are NASA FIRMS and GFED products; see "Citation". |

## 1. Sources

| Sensor / product | Role | Period used |
|---|---|---|
| Aqua MODIS active fires (Collection 6.1, 1 km), NASA FIRMS | model input | 2002-07 to 2026-10 |
| Terra MODIS active fires (Collection 6.1, 1 km), NASA FIRMS | model input; the only input before Aqua has complete months (2000-11 to 2002-09) | 2000-11 to 2026-10 |
| S-NPP VIIRS active fires (375 m, VNP14IMG), NASA FIRMS | target scale; observed values in training regions | training labels 2014-01 to 2021-06; observed months 2014-01 to 2026-10 |
| NOAA-20 VIIRS active fires (375 m, VJ114IMG), NASA FIRMS | stands in for S-NPP months with missing days | 2018-04 to 2026-10 |
| GFED4.1s burned area | independent plausibility check only, not a model input | 2003-2016 |

Yearly archive files (standard product) through 2025, the FIRMS API for 2026 (standard product
to 2026-07/08, near-real-time after). The 2012-2013 S-NPP years were never downloaded to the
development machine: they are the locked test set, graded once on GitHub Actions.

## 2. Processing

1. **Quality control** (fixed before any modelling, `config/settings.yaml`): vegetation fires only (`type = 0`); MODIS confidence ≥ 30; VIIRS confidence nominal or high; duplicate downloads merged (standard product wins over near-real-time). Near-real-time rows have no `type`: static heat sources are masked with the locations flagged `type = 2` in the standard product.
2. **Gridding**: each detection goes to the 0.25° cell containing it (`lat_idx = floor((lat + 90) / 0.25)`, `lon_idx = floor((lon + 180) / 0.25)`) and the calendar month of its UTC date. Months listed in the official FIRMS missing-data list are marked incomplete, never silently set to 0.
3. **Harmonization model** (LightGBM E028, two stages): a classifier decides whether VIIRS would see any fire in a cell-month, a count model (Tweedie loss) estimates how many. Inputs are MODIS only: Aqua and Terra counts, fire radiative power (median, 75th percentile, share below 10 MW), mean pixel area, night share, days with fire, neighbour-cell counts, plus latitude and calendar month. Year, region name and any VIIRS information are forbidden as inputs. Counts enter with a monotone increasing constraint. Trained on the three training regions, 2014-01 to 2021-06 (347,456 cell-months).
4. **Terra-only months** (2000-11 to 2002-09 and months when Aqua has missing days): Aqua inputs are built from Terra with a per-cell Terra-to-Aqua ratio fitted on MODIS only (2003-2019), then the model runs as usual. Flagged low confidence.
5. **Observed months**: in the training regions, every complete S-NPP month from 2014-01 is the observed count itself; S-NPP months with missing days use NOAA-20 scaled to S-NPP (a cell-month never adds two VIIRS satellites).
6. **Source flag** on every value (`source`): `snpp` (observed), `noaa20_scaled`, `model_aqua`, `model_terra_bridge`.

| Source | Training regions | Holdout regions |
|---|---:|---:|
| `snpp` (observed) | 554,368 | — |
| `noaa20_scaled` | 46,848 | — |
| `model_aqua` | 527,040 | 1,290,240 |
| `model_terra_bridge` (low confidence) | 89,792 | 107,520 |

## 3. Uncertainty

- **Stability interval** (`lo_90`, `hi_90`): the training years were resampled as whole calendar years 100 times and the model refitted each time; the interval is the 5th-95th percentile of the estimates. It answers "how much would the estimate move with another set of training years". It is **not** a 90% interval for the true value and does not include detection gaps (cloud, smoke, overpass time), long-term change, the Terra bridge or the NOAA-20 continuation.
- **Calibration**: region-month intervals were too narrow (38% coverage on the blind test), so, by a rule fixed before the test, they are widened around the estimate by a factor of 5.37 chosen on the validation years. After that, blind-test coverage of the true region-month totals was **95.5% in the training regions but only 55.9% in the holdout regions**. Cell-level intervals are not calibrated.
- Observed months carry no model interval (`lo_90 = hi_90 = est`).
- **Global release (`global-v1`)**: intervals come from the **first 50** of the same sealed year-block resamples, not all 100. This was done to save run time and is an approximation: the 5th–95th percentiles are a little noisier than with 100. The calibration factor was re-derived the same way on the global validation windows, again from 50 resamples each.
  - The factor is **16.75**, against 5.37 in v1.
  - Before widening, 14% of the true validation region-month totals fell inside the interval; after widening, 90%.
  - Global region intervals are therefore much wider than in v1.
  - See `docs/decisions/0013` item 5 addendum and `meta.json` `interval`.

## 4. Validation (summary of reports/validation.md)

Scores are MALE, the mean absolute difference of log(count + 1) on random 1°-5° rectangles × months with at least 10 VIIRS detections (lower is better). The blind test ran once, after the model was frozen.

| | Validation 2014-17 | Test 1: training regions 2012-13 | Test 2: holdout regions 2012-21 |
|---|---:|---:|---:|
| This dataset (LightGBM E028) | 0.295 | **0.258** | **0.644** |
| Simple ratio (M1s) | 0.377 | 0.332 | 0.857 |
| Quantile mapping | 0.463 | 0.431 | 0.866 |
| Direct splice (no harmonization) | 1.795 | 1.813 | 2.263 |

- Training regions: yearly totals within 9% of true VIIRS in the test years; agreement of "above / normal / below normal" monthly classes with true VIIRS: Cohen's κ 0.69.
- Holdout regions: errors 2.5 times larger; yearly totals 14-45% too low in central Siberia and the Indo-Gangetic Plain (within 5% in northern Australia up to 2019); more spurious small estimates where VIIRS saw no fire; κ 0.53.
- Independent check: detections per km² of GFED burned area keep the same level across 2012 after harmonization (southern Africa 2.77 before, 2.92 after), while the direct splice jumps about 5 times.
- Era shift: the MODIS inputs of 2002-2011 and 2014-2021 are hard to tell apart (classifier AUC 0.57), so backcasting does not leave the range the model was trained on.

## 5. Known limitations

1. Reliable in the three training regions; elsewhere treat values as low-confidence estimates (holdout errors 2.5× larger, totals biased low). The model's latitude input acts as a "which training region" label.
2. Training regions 2012-02 to 2013-12 are model estimates, not observations: those S-NPP years are the locked test set and never reached the development machine.
3. Terra-only months (2000-11 to 2002-09 and Aqua gaps) have about 1.6 times the error of months with Aqua.
4. Terra's orbit drifts after 2020; model estimates after 2022 (holdout regions only) are less reliable.
5. NOAA-20 months are scaled to S-NPP; whether the continuation counts as seamless is still awaiting the team's decision.
6. Near-real-time values (`nrt = true`: VIIRS from 2026-08, MODIS from 2026-09) will be revised slightly when standard products are released.
7. Neither sensor sees fires under thick cloud or smoke or between overpasses; this cannot be corrected.

## 6. Appropriate and inappropriate uses

**Appropriate**: comparing fire activity between months and years in the training regions on one scale, 2000-2026; seasonal calendars; "is this month above, near or below its usual level" (the project web page); teaching the effect of a sensor change.

**Not appropriate**: counting individual fires (one fire gives many detections); burned area or emissions; damage or hazard severity; precise totals for areas smaller than a few cells; holdout or other regions without the low-confidence caveat; treating the stability interval as a probability for the true value.

## 7. Citation and acknowledgement

- Dataset: Team Inspiratio (2026). *Harmonized MODIS × VIIRS monthly active-fire counts, 0.25°, 2000-11 to 2026-10, version 1.* GitHub release `v1` of `team-inspiratio/inspiratio-space-apps-2026` (https://github.com/team-inspiratio/inspiratio-space-apps-2026/releases/tag/v1). CC BY 4.0.
- FIRMS: "We acknowledge the use of data and imagery from NASA's Fire Information for Resource Management System (FIRMS) (https://www.earthdata.nasa.gov/firms), part of NASA's Earth Science Data and Information System (ESDIS)."
- GFED4.1s: van der Werf, G. R., et al. (2017). Global fire emissions estimates during 1997-2016. *Earth System Science Data*, 9, 697-720.
- VIIRS 375 m product: Schroeder, W., Oliva, P., Giglio, L., & Csiszar, I. A. (2014). The New VIIRS 375 m active fire detection data product: Algorithm description and initial assessment. *Remote Sensing of Environment*, 143, 85-96.

## 8. Reproduce

`uv sync`, fill `.env` (own FIRMS key and a data folder), then `uv run python -X utf8 pipeline.py all` from a clean clone (see `HANDOFF.md`). Every release file is listed with its SHA256 in `SHA256SUMS.txt`.

## 中文摘要

- **是什么**：0.25° 格子 × 自然月的卫星火点数，统一到 S-NPP VIIRS 375 m 的尺度；2012 年以前（只有 MODIS）是模型估计。范围：6 个区（3 个训练区、3 个留出区），2000-11 至 2026-10，共 261.6 万个格子-月份。
- **怎么来的**：只用 MODIS 输入的两段式 LightGBM（E028），在训练区 2014-01 至 2021-06 上训练，模型冻结后外部盲审只考了一次。训练区 2014 年以后用观测值；S-NPP 缺测月用 NOAA-20 换算；只有 Terra 的月份先用 Terra 造出 Aqua 输入。每个值都有来源标记。
- **有多准**：训练区测试年份 MALE 0.258（简单比例法 0.332），年总量偏差 9% 以内；留出区 0.644，误差是训练区的 2.5 倍，总量偏低 14%–45%（北澳除外）。
- **区间**：稳定性区间只表示“换一批训练年份估计会变多少”，不是“真实值有 90% 的可能落在其中”；区域区间按事先定的规则乘 5.37 后，训练区覆盖率 95.5%，留出区 55.9%。
- **适合**：在训练区内比较不同月份、年份的火点活动，做燃烧日历和“这个月火多不多”的判断。**不适合**：数火灾次数、算燃烧面积或排放、判断灾害严重程度，以及不加说明地用在训练区以外。
- **许可**：CC BY 4.0（团队 2026-11-04 确认）；原始数据来自 NASA FIRMS 和 GFED，引用方式见第 7 节。
