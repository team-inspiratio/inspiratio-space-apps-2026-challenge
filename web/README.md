# Fire Atlas front end (web/)

The Fire Atlas front end provides maps, monthly calendars, anomaly summaries, exports, and methods documentation.

Current address: <https://inspiratio-fire-atlas.hybrid-0f7b5-5906.chatgpt.site> (Sites private access).

## Running, building and testing locally

Requires **Node.js 22.16+** and npm. The source code in this repository is public. Preparing the full dataset also requires GitHub CLI: run `gh auth login` with an account that can access the repository hosting the Release v1 assets (see "Data sources" below). The front end needs no Python, FIRMS MAP_KEY, GPU or database.

```sh
git clone https://github.com/team-inspiratio/inspiratio-space-apps-2026-challenge.git
cd inspiratio-space-apps-2026-challenge
cd web
npm ci
npm run data:prepare                # first prepare the Release v1 data the web page needs
npm test
npm run dev
```

Vite prints the local address, usually `http://127.0.0.1:5173/`; the methods and validation page is at `/methods.html`. The download source recorded in `package-lock.json` is `registry.npmmirror.com`; if it cannot be reached, use `npm ci --registry=https://registry.npmjs.org/ --replace-registry-host=always` (which does not change the lock file). Production build and local production preview:

```sh
npm run build                      # output: web/dist/ (two pages: index.html, methods.html)
npm run preview
npm run methods:data               # only after reports/ or results/final-test/ change: regenerates src/methods-data.json
```

**In a clean environment, `npm ci && npm run build` succeeds directly, but without the scientific data.** `build` itself does not fetch data; for the browser to load the six-region data properly, or to publish the full website, you must first run `npm run data:prepare` separately and then build. Do not deploy a `dist/` without prepared data. Dependencies are pinned exactly by `package-lock.json`.

The tests are in `test/`:

- `anomaly.test.mjs`: the 25 official anomaly indicator cases, with a snapshot in `test/fixtures/anomaly-cases.json` matching the root `docs/anomaly-cases.json`; answers are checked field by field, covering ties, insufficient history, missing data, near real-time and baseline periods.
- `aggregate.test.mjs`: full/partial cell weights, no-coverage not treated as zero, each resample summed before taking the interval.
- `data.test.mjs`: conservation of the real data for six regions and 312 months, and interval bounds. Without prepared data the real-data checks are skipped and must not be taken as a full acceptance.
- `scale.test.mjs`: the calendar's log color scale over the 5th–99th percentiles of the current region (California 2020-09 at the darkest end, 2020-05 at the light end).
- `series.test.mjs`: annual totals count only years with all months present; every gap month in the direct splice has a reason (2012–13 withheld for the blind test, S-NPP outage, holdout region).
- `format.test.mjs`: estimates shown without decimals ("≈ 11,600"), percentile ordinals.
- `cell-layer.test.mjs`: hover lookup for the map cells.
- `methods-data.test.mjs`: `src/methods-data.json` must agree with `reports/validation.json`, `results/final-test/scores.json` and the conclusions of `reports/final-test.md`.

The repository root's Python tests and pre-commit run separately as described in `AGENTS.md`; they and the front end's `npm test` are two separate sets of checks.

## Data sources, when data is fetched, and the Git boundary

The data comes from the [full Release v1](https://github.com/team-inspiratio/inspiratio-space-apps-2026-challenge/releases/tag/v1). **The scientific data is not in the source repository, and it is not fetched automatically at build time.** `npm run data:prepare` calls `scripts/prepare-data.mjs`, which fetches through the GitHub CLI login the person taking over already has:

| Release file | Purpose / local location |
| --- | --- |
| `california.json.gz`, `cordoba.json.gz`, `southern_africa.json.gz`, `north_australia.json.gz`, `central_siberia.json.gz`, `indo_gangetic.json.gz` | Put as is into `public/data/v1/`; the web page reads cells, months, estimates, sources, coverage and regional totals per region |
| `meta.json` | Model and interval metadata, put into `public/data/v1/` |
| `SHA256SUMS.txt` | Checksum list of the release files; the script also pins this list's own SHA256 |
| `anomaly-cases.json`, `data-card.md`, `data-interface.md` | Test contract, data description and interface document, put into `public/data/v1/` |
| `region_totals_v1.csv` | Published regional monthly totals, put into `public/data/v1/` |
| `dataset_v1.parquet` | Fetched into `.source-data/`, to extract the per-cell raw counts and direct-splice values needed for custom selections |
| `resamples20_v1.parquet` | Fetched into `.source-data/`, providing the 20-resample approximate intervals for custom selections |

The script verifies the SHA256 of every file, retries failed fetches file by file, and reuses files that are already correct. It rearranges the two Parquet files into per-region `*.raw.f32.gz` and `*.draws.f32.gz`, and also writes `browser-assets.json`, all in `public/data/v1/`; this changes only the format sent to the browser, without retraining the model or changing any estimate. At build time Vite copies the prepared `public/` contents into `dist/`.

`.source-data/`, `public/data/`, `node_modules/`, `dist/`, test artifacts and local environment files are all ignored by Git. The repository keeps only the test snapshot, validation figures and source files. Never commit any secret, and never write a GitHub/FIRMS token into the browser or a configuration file.

## Directory structure and main components

This **Vite + plain JavaScript single-page app** keeps its main views in `src/main.js`.

```text
web/
├── index.html                   Page entry point
├── package.json                 dev / build / preview / test / data:prepare
├── package-lock.json            Exact dependency lock
├── .gitignore                   Ignore rules for dependencies, outputs, data, environment files
├── .openai/hosting.json          Existing Sites project ID, static directory dist
├── AGENTS.md                    Front-end scope and limits
├── PROGRESS.md                  Original front-end acceptance record (historical)
├── src/
│   ├── main.js                  Page template, views, interaction, loading, downloads
│   ├── style.css                Desktop and mobile layout
│   ├── anomaly.js               JS version of the anomaly indicator reference implementation
│   └── aggregate.js             Cell polygons, area weights, sums, resampled intervals
├── scripts/prepare-data.mjs      Fetches and verifies v1, generates the browser data
├── public/
│   ├── favicon.svg              Icon
│   └── methods/*.png            Original analysis figures (linked from the methods page)
└── test/
    ├── anomaly.test.mjs
    ├── aggregate.test.mjs
    ├── data.test.mjs
    └── fixtures/anomaly-cases.json
```

| Component | Where the code is / what it does |
| --- | --- |
| Map | Leaflet initialization, `draw`, `applySelection`, `renderMap` in `main.js` (cells drawn by the single canvas layer in `src/cell-layer.js`); region presets, drawing, coordinate input and monthly cells. Area calculations are in `aggregate.js` |
| Calendar | `renderCalendar`, `showTooltip`; year × month cells, year range, source/quality flags, harmonized vs direct-splice toggle |
| Current-month card | `renderInsight` calls `anomaly.js`; historical same-month percentile, median, multiple, baseline period, number of reference years, and missing/preliminary data |
| Line chart | `renderTrend`; annual totals for harmonized, Aqua MODIS and S-NPP VIIRS, linked to the selected year |
| Methods page | The standalone page `methods.html` + `src/methods.js` (`/methods.html`, with an anchor per section, such as `#gfed`); the core figures are redrawn in the site's style by `src/charts.js`, with numbers from `src/methods-data.json`; the original figures are in `public/methods/` |
| Downloads / sources | `#downloads-dialog`, `csv`, `exportPNG`; monthly CSV, selection GeoJSON, calendar PNG, notes and the link to the full Release |

## Existing deployment and how to redeploy

It currently uses **Sites**, at <https://inspiratio-fire-atlas.hybrid-0f7b5-5906.chatgpt.site>. The project ID `appgprj_6aeb7d430ce081918f28cc355b227d73` is stored in `.openai/hosting.json`; it is not a secret.

**This time there is no redeployment, no change to access permissions, no GitHub Pages configuration and no automatic publishing.** Commits or merges in the team repository do not update the current web page automatically.

When a redeployment is needed, someone with edit/publish permission on that Sites project follows the existing process in Codex with the Sites plugin installed:

1. Take the `web/` to publish from the team repository and run `npm ci` → `npm run data:prepare` → `npm test` → `npm run build`.
2. Choose the **existing** Sites project above, read its access status and obtain a short-lived source write credential for the same project, without creating a new project. The credential is passed only through the publishing helper's hidden stdin, never saved to a file or written into command arguments.
3. Following the Sites skill, open the existing source with the source helper in a separate Sites checkout, then sync the contents of `web/` into it as that checkout's project root; do not nest it as `web/web/`, and do not overwrite `.git/`. Keep the project ID and `static.directory = dist`.
4. Prepare the same verified data in that checkout, test and build, then use the Sites source helper to push the project source and package the static output; the team repository's `dist/` does not go into Git.
5. Using the exact source commit and archive returned by the source helper, run the Sites save/private deploy operation, wait for it to succeed, then check the original address. Keep the existing private access scope; giving others access or publish permission needs separate authorization from the project owner.

This is a manual release process on the existing hosting service; it needs no GitHub Pages/Vercel configuration and no front-end secret.

## Known issues to fix

- The v1 web assets have no raw per-point hotspot files per region. What is provided now is a gridded monthly CSV, which must not be labeled as raw point data; later, the data owner needs to provide approved point files.
- It is currently the six-region v1, and `global-v1` is not yet integrated; global data work remains with its original owner.
- Custom selections are apportioned approximately by overlap area; the 20-resample intervals are uncalibrated approximations, not error bounds with guaranteed coverage.
- Fonts depend on Google Fonts and the basemap on OpenStreetMap; offline, it may fall back to other fonts and the local Natural Earth land outlines.
- A human usability check on separate devices is still for the team to actually do. Taking over the source needs team repository permission, and redeploying also needs Sites edit/publish permission.

Further issues are changed through separate PRs. For the anomaly indicator and the data contract, the root `docs/anomaly-cases.json` and `docs/data-interface.md` prevail.
