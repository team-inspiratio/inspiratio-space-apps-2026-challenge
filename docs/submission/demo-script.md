# Demo script draft

> **DRAFT: check against the official guide published on November 13.** The format (30-second captioned video, or up to 7 slides) comes from the 2025 rules in `docs/proposal.md`.
>
> The video must be the team's original work. If any team member is under 18, their photo, voice or likeness must not appear (official FAQ). This script uses screen recording and captions only.

## Storyline

Problem (a 5-fold jump in 2012) → fix (the harmonization toggle) → use (pick a region, check the current month's anomaly, download) → validation (test scores).

**Before recording**: use the website as deployed after PR #5 is merged. The old live version has no methods page, and the current-month card still uses the old wording.

## 30-second video

Captions are the only text channel. Keep each on screen for its full duration.

| # | Time | Length | Screen | Action | Caption |
|---|---|---|---:|---|---|
| 1 | 0:00–0:05 | 5 s | Fire Atlas home, map in view | Slow scroll | S-NPP just stopped. MODIS is retiring. 26 years of fire records are at a handover. |
| 2 | 0:05–0:11 | 6 s | Southern Africa, Direct splice calendar | Click Southern Africa, click Direct splice | Join the old and new sensors as they are, and fire jumps about 5× at 2012. |
| 3 | 0:11–0:16 | 5 s | Same calendar | Click Harmonized | That was the sensor, not more fire. Harmonized: one scale, no jump. |
| 4 | 0:16–0:23 | 7 s | Córdoba, month card, then Download data | Click Córdoba, point at card, click Download data, click Selected monthly series | Pick a region. See if the latest month is unusual. Download the data. |
| 5 | 0:23–0:28 | 5 s | `/methods.html`, score table | Scroll to Primary score | One blind test: 22% lower error in training regions. Unseen regions: 2.5× larger error. |
| 6 | 0:28–0:30 | 2 s | Logo and web address | Hold | Fire Atlas · Team Inspiratio · NASA FIRMS data |

**Checks after editing:**

- Total length is 30 seconds or less in a player, not just in the editor.
- Caption 5 stays as written. Cutting the second sentence would overstate accuracy outside the training regions.
- Do not add "predicts", "accuracy", "error bars" or "burned area".

**Why each number is safe:**

| Caption | Source |
|---|---|
| S-NPP stopped, MODIS retiring | `docs/proposal.md`, FIRMS and Earthdata notices |
| 26 years | Release v1 covers 2000-11 to 2026-10 |
| About 5× | `reports/validation.md`, conclusion 1 |
| 22% lower, 2.5× larger | `reports/final-test.md`, sections 1 and 6 |

## Demo routes

On 2026-11-04 all three routes were walked through with real mouse clicks on the production build of PR #5 (`7da3a4a`, Release v1 data); all of them work, with no console errors.

**What "one click" really means**: each of the six preset region buttons on the left takes you to its region in one click. But the web page has **no** entry point that goes straight to a given region and month in one click, and the address does not record the region or month, so each route takes 1–3 clicks. This is not a bug; deep links would be a new feature and, as instructed, were not built. A person decides whether one is needed.

| Route | Steps | What the page shows | Voice-over |
|---|---|---|---|
| **A California's 2020 fire season** | Open the home page (California by default) → click the 2020 Sep cell in the calendar | September 2020, 125,460, Above normal · 100th percentile, 21.9× | September 2020 is the biggest month in California's record: 125,460 detections, about 22 times the median of earlier Septembers. |
| **B Córdoba's latest month** | Reload the page → click Córdoba | October 2026, 1,272, Below normal · 0th percentile, 0.3×, marked Preliminary | Córdoba's latest month reads below normal: 1,272 detections against a usual 4,220 or so, and the figure is still preliminary. |
| **C Southern Africa's 2012 jump** | Click Southern Africa → click Direct splice → click Harmonized | Direct splice: 266,145 in 2011, 1,195,314 in 2014; harmonized: about 1.29 million in 2011 | Joined as-is, 2011 shows about 266,000 detections and 2014 about 1.2 million; harmonized, 2011 is about 1.29 million and the jump is gone. |

**Backup for route B**: after clicking Córdoba, click the 2020 Sep cell in the calendar, which shows 19,346, Above normal · 100th percentile, 2.4×.

**Recording notes**:

- The selected month is kept across regions: after route A, clicking Córdoba still shows September 2020. Reload the page to see the latest month.
- For route C's jump, scroll the calendar to around 2014 and 2012; the line chart below shows it more clearly.
- "Download data" opens a dialog; you then have to click "Selected monthly series" to download (for Córdoba this gives the 310-row `cordoba-monthly-v1.csv`).
- Route B's 2026-10 is near real-time data; the page marks it Preliminary, and it may be revised slightly later. If the data is updated, check the numbers again before recording.
- Use only these three training regions. Do not tell stories with the holdout regions; every month there is a low-confidence estimate.
- Once the global version is added, the numbers above may differ (the global model's values differ from v1), so walk the routes again.

**Sources of the numbers**: the values in the routes are the Release v1 data shown on the web page, and the comparison of California 2020-09 with 2020-05 is also in `web/archive/website-v1/test/scale.test.mjs`; for southern Africa's jump factor, `reports/validation.md` prevails.

## Backup: slide outline (7 slides maximum)

Use this if the team submits slides instead of a video. All slides in English.

| # | Title | Content | Visual |
|---|---|---|---|
| 1 | One fire record across two satellite generations | S-NPP has stopped and MODIS is retiring. The record needs one scale | Atlas home screenshot |
| 2 | The 2012 jump is not real | Same fires, VIIRS records 4.8–5.6× more detections than Aqua (southern Africa, 2014–21). Joined as-is, fire jumps about 5× | `reports/figures/d1-1-problem.png` or the redrawn Figure 1 |
| 3 | Harmonized: one scale, MODIS inputs only | Two-stage LightGBM learned on the overlap. Estimates flagged, observations kept | Calendar with the Harmonized / Direct splice switch |
| 4 | Use it: region, month, download | Pick a region or draw one. Compare a month with its history. Take the CSV | Month card and calendar |
| 5 | Tested once, blind | Pre-registered. Sealed submission graded by GitHub Actions. Test 1 MALE 0.258 vs 0.332 for the simple ratio | Score table |
| 6 | Where it holds, and where it doesn't | Training regions: within 9% yearly. Unseen regions: 2.5× larger error, totals run low. Global version: validation only, no blind test | `reports/figures/d1-2-test-totals.png` |
| 7 | Open data, open method | Dataset CC BY 4.0, reproducible pipeline, SI use disclosed. Next: more training regions and a new blind test | Links |

**Do not add a slide 8.** If one more point is needed, merge it into slide 7.
