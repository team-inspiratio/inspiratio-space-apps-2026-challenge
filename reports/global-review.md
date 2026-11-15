# Global dataset global-v1: review before release

> The results of stage G, for a person to look over before Release `global-v1` is published (task card requirement).
>
> - Method: `docs/decisions/0013`; validation scores: `reports/global-scores.md`; notes for the front end: `docs/data-interface-global.md`.
> - The files are on the local machine in `D:/inspiratio-data/processed/global-v1/` and have not been uploaded yet.

## 1. Acceptance checks (all passed)

| Check | Result |
|---|---|
| Coverage | 278,192 cells × 312 months = 86,795,904 rows, no nulls |
| Observed rows equal S-NPP observations | All 38,867,104 rows equal |
| S-NPP recount: recount the cleaned raw hotspots by region × month and compare with the dataset | 1,988 region × months (2014-01 to 2026-10), 189 million hotspots: **0 mismatches** |
| Resampled years match those sealed in S11 | All three groups pass (first 50) |
| Frozen files, banned features, secrets, 2012/2013 S-NPP | Guardrails pass; frozen files untouched |

## 2. Is there a break in the series?

Global annual totals (millions of hotspots on the S-NPP scale, complete years only):

| Year | Total | Main source | | Year | Total | Main source |
|---|---:|---|---|---|---:|---|
| 2001 | 19.35 | Terra bridge | | 2014 | 16.58 | S-NPP observed |
| 2002 | 19.77 | Terra bridge | | 2015 | 17.58 | S-NPP observed |
| 2003 | 19.42 | Model (Aqua) | | 2016 | 16.56 | S-NPP observed |
| 2004 | 19.13 | Model (Aqua) | | 2017 | 16.25 | S-NPP observed |
| 2005 | 19.16 | Model (Aqua) | | 2018 | 15.47 | S-NPP observed |
| 2006 | 17.57 | Model (Aqua) | | 2019 | 17.28 | S-NPP observed |
| 2007 | 19.34 | Model (Aqua) | | 2020 | 16.97 | S-NPP observed |
| 2008 | 18.07 | Model (Aqua) | | 2021 | 16.60 | S-NPP observed |
| 2009 | 16.88 | Model (Aqua) | | 2022 | 14.76 | S-NPP observed |
| 2010 | 18.11 | Model (Aqua) | | 2023 | 17.95 | S-NPP observed |
| 2011 | 17.62 | Model (Aqua) | | 2024 | 18.94 | S-NPP observed |
| 2012 | 19.03 | Model (no S-NPP on this machine) | | 2025 | 14.81 | S-NPP observed |
| 2013 | 16.00 | Model (no S-NPP on this machine) | | | | |

There is no step going from model years to observed years (2013 → 2014). The 2000s are slightly higher, which matches the direction of the year-by-year decline in global burned area reported in the literature.

Mean annual totals by region, model years (2003–2011) compared with observed years (2014–2021):

| Region | 2003–2011 | 2014–2021 | Ratio | Region | 2003–2011 | 2014–2021 | Ratio |
|---|---:|---:|---:|---|---:|---:|---:|
| SHAF | 5,090,172 | 5,043,859 | 1.01 | AUST | 644,488 | 677,889 | 0.95 |
| NHAF | 4,047,723 | 3,670,017 | 1.10 | CEAM | 500,849 | 378,642 | 1.32 |
| SHSA | 2,900,705 | 1,857,688 | **1.56** | EQAS | 396,956 | 337,598 | 1.18 |
| SEAS | 1,154,272 | 1,201,115 | 0.96 | NHSA | 387,036 | 349,586 | 1.11 |
| CEAS | 973,242 | 701,861 | **1.39** | TENA | 380,317 | 395,346 | 0.96 |
| BOAS | 878,406 | 900,310 | 0.98 | BONA | 246,428 | 319,178 | 0.77 |
| EURO | 152,133 | 107,069 | **1.42** | MIDE | 131,885 | 166,302 | 0.79 |

Most of these differences are consistent with known trends: fewer deforestation fires in South America, less crop-residue burning in Central Asia and Europe, more large fires in the North American boreal forest in recent years. But the values for model years are estimates, and model bias cannot be fully ruled out. In four regions, Central America (CEAM), northern South America (NHSA), southern South America (SHSA) and equatorial Asia (EQAS), the simple ratio method M1s did better in validation (`reports/global-scores.md`).

## 3. Intervals: pay special attention

- The widening factor for regional intervals was re-derived with the frozen formula on the global validation windows, giving **16.75**. v1 has 5.37.
  - Without widening, only **14%** of the true region × month values on the validation windows fall inside the interval; after widening, 90%.
  - Reason: the regions are large and their totals high, so the variation from "a different set of training years" is relatively small, and the main error is the model's systematic bias in each region.
- As a result the global intervals are very wide. For region × month intervals in model years, the median width relative to the estimate is:
  - NHAF 0.50 times, SHAF 0.58 times;
  - BOAS, BONA, EURO, MIDE about 1.4–1.5 times;
  - the holdout regions about 1.6 times.
- About 19% of the model region × month intervals have a lower bound of 0.
- Only the first 50 sealed resamples were used (ADR 0013 item 5 addendum, approved by the user).
- Suggest that the web page describes the intervals as an "uncertainty range (very wide)" rather than as precise error bars.

## 4. Files

| File | Size |
|---|---:|
| `dataset_global-v1.parquet` | 201 MB |
| `dataset_global-v1.csv.gz` | about 398 MB |
| `resamples20_global-v1.parquet` | 663 MB |
| `frontend/` (17 regions + 3 boxes + `index.json`) | 32 MB (compressed) |
| `region_totals_global-v1.csv`, `box_totals_global-v1.csv`, `meta.json`, documents, `SHA256SUMS.txt` | Small |

Every file is within GitHub Release's 2 GB per-file limit.

## 5. Please decide

1. Can Release `global-v1` be published with the current results?
2. ADR 0013 item 3 (the production version uses the global retrain, not the three-region model that took the test) and item 5 (the interval factor is re-derived on the global validation windows) are still marked "awaiting human confirmation". Publishing amounts to confirming both at the same time.
