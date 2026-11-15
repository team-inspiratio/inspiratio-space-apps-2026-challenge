# Data health check findings (S06, proposal A5)

> Only the training regions (California, Córdoba, southern Africa) are examined, and VIIRS is used only from 2014-01 onward; the holdout regions and 2012–2013 VIIRS are not on this machine. Figures are in `reports/figures/`, numbers in `reports/a5-stats.json`, code in `harmonization/explore.py`. All ratios are ratios of "region × month" totals, using only months in which both sensors are complete. These figures are only for finding data problems and are **not used to choose methods or tune parameters**.

## The 4 figures

1. `a5-1-monthly-series.png`: monthly hotspot series for each training region (Terra and Aqua over the full period; S-NPP and NOAA-20 from 2014-01).
2. `a5-2-ratio-over-time.png`: monthly S-NPP/Aqua ratio, 2014–2026.
3. `a5-3-ratio-latitude-pixel.png`: the same ratio against latitude (2° bands) and Aqua mean pixel area, 2014-01 to 2021-06.
4. `a5-4-noaa20-snpp.png`: monthly NOAA-20/S-NPP ratio, from 2018-04.

## Findings

1. **The problem is real, and the gap is large.** S-NPP counts several times as many hotspots as Aqua: by annual totals, about 7–10× in California and about 4.6–5.7× in Córdoba and southern Africa. Direct stitching would create a large artificial step in 2012. Note that this is a ratio of "hotspot pixel counts" (375 m versus 1 km pixels) and cannot be compared directly with the literature's "VIIRS counts about 70% more", which is computed on a different basis; the S13 comparison with the literature must use a common basis.
2. **The ratio swings widely with the seasons.** Monthly ratios range from about 3 to 20×: high in months with few fires and low in the fire season. A simple fixed ratio is therefore not enough; the ratio must at least vary with month or fire volume, consistent with the proposal's choice of M1s (by calendar month) and LightGBM.
3. **No clear trend in the ratio over 2014–2021.** Annual trend of the log ratio from 2014-01 to 2021-06: California +1.7%/year, Córdoba +3.5%/year, southern Africa about 0; the annual ratio fluctuates within a range without drifting in one direction. The proposal requires that "if the ratio itself has a clear trend, find the cause first"; for now no extra handling is needed.
4. **Aqua's orbit drift from 2021-07 shows no clear effect in the training regions yet.** Median ratio after the second half of 2021: California 7.0 → 7.9 and southern Africa 5.9 → 7.0 rise somewhat, Córdoba 5.4 → 5.3 is unchanged. The rise is within the year-to-year fluctuation, but its direction is consistent with "Aqua's overpass time moves later, so it misses more". The training period ends at 2021-06 anyway, so modeling is not affected; data after 2021-07 is used only for display.
5. **The ratio differs clearly by latitude and region.** California (33–42°N) is about 7.5–9.2, the two southern-hemisphere regions about 4.7–5.6. Against Aqua pixel area the change is not monotonic (6.3 near nadir, lowest at 4.9 for 2–3 km², back to 5.3–5.8 for larger pixels), and it mixes different regions, so it cannot be read directly as "the more oblique the view, the bigger the gap". This suggests the model needs features such as latitude and pixel size, and is also a warning: **regional differences are large, so extrapolating to the holdout regions (Test 2) may be harder than extrapolating in time**.
6. **NOAA-20 and S-NPP are very close.** The median monthly ratio in the three regions is 0.98–1.00, with a 10%–90% range of about 0.89–1.08 and occasional single-month outliers (e.g. Córdoba 2019-01 at 1.64, a month with very few hotspots). Continuing S-NPP with NOAA-20 from 2026-11 looks feasible; S08 will test it formally as planned (day and night separately, monthly total bias and seasonal stability).
7. **The Terra/Aqua ratio has fallen fast in recent years.** Ratio of Terra/Aqua annual totals in the training regions: stable at 0.36–0.43 over 2003–2019, 0.50 in 2020, then falling to 0.29 in 2023, 0.21 in 2025 and 0.17 in 2026, consistent with Terra's orbit drift and upcoming retirement. **The Terra→Aqua bridge in S08 may use only overlap years with a stable ratio** (e.g. 2003–2019; the exact years are set in S08 under the training-period rules), never years from 2020 on.
8. **Missing data must be handled carefully.** In the official missing-data list, S-NPP is missing for the whole of 2026-05, partially missing in 2022-07/08 and in several months of mid-2024; Aqua is missing 16 days in 2022-04. These months are flagged in `docs/month-status.csv` and are never treated as 0 in the grid tables. The gaps in the NOAA-20/S-NPP ratio figure are these months.

## Problems not found

- No unusual whole-month gaps or order-of-magnitude jumps in the series (missing months excluded); the seasonal shape is very regular in all three regions.
- The 2026 NRT segment (VIIRS from August, MODIS from September) joins the earlier SP segment smoothly, with no visible step.

## Notes for later stages

- S08: the Terra→Aqua bridge uses only years with a stable ratio; the NOAA-20 continuation looks promising but must be tested as planned.
- S10: the ratio's seasonality and regional differences are both large, so month, latitude, pixel size and fire volume are all useful features; be wary of how well the model extrapolates outside the training regions.
