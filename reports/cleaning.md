# Cleaning report (S04)

> The rules were pre-registered in S01 (`quality_control` in `config/settings.yaml`) and finalized before modeling; code in `harmonization/clean.py`; per-year counts in `docs/cleaning-counts.csv`; spot-check sample in `docs/removed-sample.csv`.
> Data scope: FIRMS annual archives (MODIS 2000–2025, S-NPP 2014–2025, NOAA-20 2018–2025) + the 2026 API (SP and NRT, up to 2026-11-02). Holdout-region VIIRS was already dropped at import and is not in the numbers below.

## Rules and their order

1. **Duplicate records**: keep only one record per satellite, date, time and latitude/longitude, with standard products (SP) taking priority over near real-time (NRT). The duplicates come from the same hotspot appearing in two countries' files in the annual archives (near borders), and from SP/NRT overlap. Adjacent pixels are not deleted, even within the same minute.
2. **Type**: keep only `type = 0` (vegetation fire), removing volcanoes, other static heat sources (factories, oil and gas fields) and offshore detections.
3. **NRT static heat-source mask**: NRT has no `type` column. A mask is built from the locations of `type = 2` for all satellites in the SP period from 2024 to 2026: small cells of about 0.01° (about 1 km) plus their 8 neighbors, 483,765 small cells in total; NRT points that fall inside the mask are removed. **This is an approximation for the NRT segment**: it may wrongly delete real vegetation fires next to static heat sources, and it misses heat sources that appeared after 2024.
4. **Confidence**: MODIS confidence ≥ 30; VIIRS keeps only nominal and high.

## How many rows each rule removed (all years combined)

| Satellite | Input | Duplicates | Type ≠ 0 | NRT mask | Low confidence | Kept |
|---|---:|---:|---:|---:|---:|---:|
| Terra MODIS | 40,576,702 | 1 | 2,186,537 (5.4%) | 20,788 (0.05%) | 2,096,434 (5.2%) | 36,272,942 |
| Aqua MODIS | 73,823,045 | 2 | 1,703,259 (2.3%) | 16,724 (0.02%) | 3,068,670 (4.2%) | 69,034,390 |
| S-NPP VIIRS | 247,843,716 | 139 | 16,879,458 (6.8%) | 444,825 (0.18%) | 27,353,203 (11.0%) | 203,166,091 |
| NOAA-20 VIIRS | 166,622,326 | 80 | 11,427,454 (6.9%) | 457,347 (0.27%) | 18,852,511 (11.3%) | 135,884,934 |
| **Total** | 528,865,789 | 222 | 32,196,708 (6.1%) | 939,684 (0.18%) | 51,370,818 (9.7%) | 444,358,357 |

**2026 NRT segment**: the share removed by the mask is close to the share of `type ≠ 0` in the same satellite's SP data, which suggests the mask neither removes clearly too much nor misses clearly too much:

| Satellite | NRT rows | Removed by mask | Comparison: share of `type ≠ 0` in SP |
|---|---:|---:|---|
| Terra | 226,349 | 20,788 (9.2%) | 11.8% in the 2026 SP segment |
| Aqua | 446,501 | 16,724 (3.7%) | 2.1%–3.6% per year, 2016–2025 |
| S-NPP | 6,460,800 | 444,825 (6.9%) | 6.2%–7.8% per year, 2016–2025 |
| NOAA-20 | 6,665,447 | 457,347 (6.9%) | 6.9% over all SP years combined |

## Manual spot check of 20 removed records

Sampling method: for each satellite-year, 50 records were drawn at random from the removed records; then up to 5 were taken per rule, and the rest was filled at random up to 20 (fixed seed). There are only 222 duplicate records across all years, and none was drawn; this does not affect the conclusion.

| Rule | Count | Finding |
|---|---:|---|
| Type ≠ 0 | 6 | All at known industrial or oil and gas facilities: the Basra oil fields in Iraq (30.45N 47.67E), the Magnitogorsk steelworks in Russia (53.45N 59.04E), the Tabasco oil and gas area in Mexico (17.85N 93.12W), the Pearl River Delta industrial zone (22.84N 113.49E), the Bukhara gas field area in Uzbekistan (38.93N 64.80E), and near the Kavadarci ferronickel plant in North Macedonia (41.42N 21.94E). **Correctly removed**. |
| NRT mask | 5 | The Monagas oil fields in Venezuela (9.73N 63.46W), the Gachsaran oil field in Iran (30.39N 50.62E), an oil and gas area in the Algerian desert (28.56N 7.47E), the Kerman industrial and mining area in Iran (29.13N 55.36E): 4 are static heat sources, correctly removed. 1 record in Minas Gerais, Brazil (18.85S 41.97W) could be either a heat source or a nearby vegetation fire; **this is the approximation error described above**. |
| Low confidence | 9 | All consistent with the rule (MODIS confidence 0–28, VIIRS low). Several are in fire-prone areas such as the DR Congo, Zambia, Paraguay and Mozambique, and are probably real small fires. This is the pre-registered trade-off: low confidence is removed for both sensors, so labels and inputs are consistent, and no further adjustment is made. |

**Conclusion**: no deletions that violate the rules were found. The main limitations are that the heat-source mask for the NRT segment (VIIRS from 2026-08, MODIS from 2026-09) is approximate, and that the low-confidence rule removes some real small fires; both points must also be stated in the data card.

## Other notes

- **Differences between the annual archives and the API** (S02 comparison, `docs/crosscheck-api-vs-yearly.csv`): the annual archives are split by country and exclude points that belong to no country; the API's global query returns about 0.4% more, and on the day spot-checked, 47 of the 51 extra points were `type = 3` (offshore), which the type rule removes. The 2026 NRT segment has no `type`, so a few such offshore points may remain; the effect is negligible.
- **MODIS versions**: in the annual archives MODIS has `version` 6.2 (standard product), and NRT has 6.1NRT; VIIRS is 2.
- Missing months are not handled during cleaning; they are flagged in S05 from the official missing-data list (`docs/month-status.csv`) and are never treated as 0.
