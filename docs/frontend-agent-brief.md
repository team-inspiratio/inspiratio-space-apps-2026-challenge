# Brief for the front-end / web-page agent

> **Summary for agents:** you are building the burn-calendar website on top of a finished,
> published dataset. Read this file first (about 5 minutes), then only the docs it points to.
> Do **not** read the data-pipeline code, the execution plan or the task cards; they are history.
> The data is final: do not regenerate it, retrain anything or "fix" numbers on the front end.
> Section 7 has a prompt to paste into a fresh agent.

This file condenses the conclusions of the data track's two days into what a web-page agent needs to know. The data is done and published; the web page is only responsible for **using it well and explaining it clearly**. The full story of the data track and the reasons for each decision are in [`docs/project-journey.md`](project-journey.md); read it when you need to tell the story.

## 1. What the web page does

One workflow (the proposal's "What the web page delivers" section): **pick an area → view the burning calendar → judge whether the latest month is unusual → download**.

1. **Pick an area**: click a preset region on the map, or draw a box or polygon, or enter latitude and longitude.
2. **View the history**: a burning calendar with one row per year and one column per month, colored by the number of hotspots. Hovering shows the value, the source flag and the interval. Users can switch between "harmonized / direct stitching" to compare; this is the core view of the demo.
3. **Latest-month card**: how many times the historical same-month median the latest complete month is, which historical percentile it ranks at, written as "high / normal / low".
4. **Download**: monthly CSV, calendar image.

No fire forecasting.

## 2. Which data to use

| Purpose | Release | Documentation |
|---|---|---|
| **Main data: world map + any area** | `global-v1` (CC BY 4.0) | [`docs/data-interface-global.md`](data-interface-global.md) |
| Demo-region version (6 regions, the model that went through the external blind grading once) | `v1` (CC BY 4.0) | [`docs/data-interface.md`](data-interface.md) |

Use the bundled public frontend files in `inspiratio-site/public/data/global-v1/`. For V2, run `npm run data:prepare` inside `frontend-v2/`; it verifies the required files against `results/expected/dataset-global-v1.sha256` and copies them locally. No account, API key, Python or network download is needed. See [public data availability](public-data.md) for files that are not included.

**The web page usually needs only these files:**

- `frontend/index.json`: the list of all selectable regions, with names, roles, bounding rectangles and file names.
- `frontend/<name>.json.gz`: one per region, loaded on demand. 0.1–5 MB compressed; the largest, BOAS, is about 57 MB uncompressed, so **do not read them all at once**.
- `region_totals_global-v1.csv`: totals by region × month, very small, suitable for a world overview.
- `resamples20_global-v1.parquet` (663 MB): needed only when "an area the user draws should also show an interval". You can leave intervals out at first, or handle this on a back end.

The JSON format, fields and source flags are in sections 3–4 of `data-interface.md`; how the global version differs is in section 1 of `data-interface-global.md`.

## 3. Rules that must be followed

- **User-selected areas**: sum the cells that fall inside the area, month by month. The method is in section 5 of `data-interface.md`.
- **Anomaly indicator**: follow the rules of the reference implementation [`harmonization/anomaly.py`](../harmonization/anomaly.py) exactly. The front-end implementation must pass all 25 standard cases in [`docs/anomaly-cases.json`](anomaly-cases.json) field by field, written as front-end unit tests. The rules are in section 6 of `data-interface.md`.
- **0 and null are different**: `0` means "no hotspot recorded", null means "no data". Use two different colors on the calendar.
- **Units**: the values are "monthly hotspot counts on the VIIRS S-NPP 375 m scale", not numbers of fires and not burned area. Legends and hover text must say so.

## 4. How to show confidence

These are real limitations of the data; the web page must show them honestly, but need not dwell on them:

- **Source flags**: every value has a `source`. Show it on hover; on the calendar, patterns or corner marks can distinguish "observed" from "model estimate":
  - training cells from 2014 on are real observations;
  - before 2012 they are model estimates;
  - the early Terra-only months have low confidence.
- **Low-confidence regions**: BOAS and BONA (boreal forests), MIDE (Middle East), and the three holdout regions (`north_australia`, `central_siberia`, `indo_gangetic`). Suggest adding a "low confidence" label.
- **The intervals are very wide**: the widening factor for the global version's regional intervals is 16.75. A typical interval is 0.5–1.6 times the estimate wide, and about 19% have a lower bound of 0. Call them a "rough range", **not "error bars" or "confidence intervals"**. They can be hidden by default and shown on hover.
- **2012-02 to 2013-12**: model estimates everywhere, as dictated by the project rules.
- **Near real-time**: months with `nrt = true` (VIIRS from 2026-08) will be revised slightly later; a small marker can be added.

## 5. Numbers the demo and project page can use

Every number has a source and can be used directly:

- **The problem**: in 2012 VIIRS took over from MODIS, and for the same fires VIIRS counts several times as many hotspots. Stitched together directly, the historical series has a false step in 2012. Example: for southern Africa in 2003–2011, direct stitching gives only 250,000 per year, the harmonized series 1.25 million, which joins up with the 1.22 million observed in 2014–2021 (`reports/validation.md`).
- **No break globally**: 16.0 million hotspots globally in 2013 (model) and 16.6 million in 2014 (observed) (`reports/global-review.md`).
- **External blind grading, taken only once**: scored in the GitHub cloud; on Test 1 the error is **22%** lower than the baseline M1s, and on Test 2 (regions never seen) **25%** lower (`reports/final-test.md`).
- **Global validation**: **14%** lower than the baseline, winning in 10 of the 14 large regions (`reports/global-scores.md`).
- **Data scale**:
  - 529 million raw hotspot records, 444 million after cleaning;
  - 4 satellites (Terra, Aqua, S-NPP, NOAA-20), 2000-11 to 2026-10, 26 years in total;
  - 278,000 cells and 86.8 million cell-months worldwide.
- **Reproducible**: from a fresh clone, one command finishes in 87 minutes, with 37 checks matching bit for bit (ADR 0012).
- **Timing**: S-NPP has stopped and MODIS is about to retire; this dataset keeps the fire record unbroken through the handover. The proposal suggests putting this line in the first 5 seconds of the demo.

**Things not to say**: "predicting fires", "XX% accuracy" (our metric is the MALE error, not accuracy), "error bars", "burned area".

## 6. Where to look when in doubt

| Question | Look here |
|---|---|
| What a field means | `data-interface.md` section 2 |
| How the data was made, limitations | [`docs/data-card.md`](data-card.md) |
| Why things were done this way | [`docs/project-journey.md`](project-journey.md), then [`docs/decisions/`](decisions/) |
| Figures and scores | [`reports/validation.md`](../reports/validation.md), [`reports/figures/`](../reports/figures/) |
| How AI was used in the project | [`docs/ai-usage.md`](ai-usage.md); quote it directly when the project page needs an AI usage statement |

If something is wrong with the data, for example values that look off or a missing field: **do not change numbers on the front end**. Note the region, the month and what you see, and hand it to the data-track people.

## 7. Opening prompt for a new agent

Paste the following as is into the agent building the web page (Claude Code, Codex and Cursor all work):

```text
You are building the "burning calendar" web page for Team Inspiratio at NASA Space Apps 2026. The data is finished and publicly released; you are responsible only for the web page.
First read docs/frontend-agent-brief.md in the repository team-inspiratio/inspiratio-space-apps-2026-challenge (required, 5 minutes),
then, as needed, docs/data-interface-global.md and docs/data-interface.md, which it points to. Do not read the data-processing code or the execution plan.
Rules:
1) Download the data from GitHub Release global-v1; do not regenerate it or change any values on the front end;
2) The anomaly indicator must pass the 25 cases in docs/anomaly-cases.json, written as unit tests;
3) Show source flags and low confidence as in section 4 of the brief; call the intervals a "rough range", not error bars;
4) Use only the numbers in section 5 of the brief in any text.
First give me a short proposal for the page structure and technology choices (one page at most); start writing code after I confirm it.
```
