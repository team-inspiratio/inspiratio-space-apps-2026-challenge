# Inspiratio Version 2

Website source in `frontend-v2/`. Documentation, evidence and required data are provided in this public repository.

## Public website

**[Open Inspiratio V2](https://team-inspiratio.github.io/inspiratio-space-challenges-2026/)** — hosted by GitHub Pages under this repository.

The [V2 deployment workflow](../.github/workflows/pages-v2.yml) verifies the bundled `global-v1` assets, runs unit and browser tests, and publishes the production build after relevant changes merge into `main`. Pull requests run the same checks without publishing. The workflow can also be run manually from GitHub Actions.

## Local setup

Requires Node.js 22.16+ and npm.

```sh
cd frontend-v2
npm ci
npm run data:prepare
npm run build
npm run dev -- --port 5176
```

Data preparation reads `../inspiratio-site/public/data/global-v1/` and verifies all 21 required files against `../results/expected/dataset-global-v1.sha256` before copying them into the ignored `public/data/global-v1/` directory. It uses local files only; no GitHub login, GitHub CLI, Python, network download or API key is required. The readiness marker is written only after all checks pass and is removed if preparation fails. The runtime does not need the separate `meta.json` asset. Without prepared data, the interface explicitly shows limited samples; spatial selection is unavailable.

Documentation and evidence links resolve to this public repository. See [public data availability](../docs/public-data.md).

## Features

English interface, monthly red activity calendar, opt-in accessible palettes, interactive Leaflet map, city labels, coordinate entry and left-button rectangle selection. Custom areas load matching global partitions automatically without double-counting demonstration boxes. Sources, missing data and uncertainty remain explicit. Includes date filters, anomaly comparisons, CSV and calendar image exports, and a Chongqing August 2022 example.

Street tiles require internet access and retain provider place names. Offline country outlines remain available. Data are monthly 0.25-degree detection counts, not individual fires or fire severity.

## Validation

```sh
npm test
npm run build
npm run test:browser
```

Browser tests require a running local server and prepared global-v1 data. Set FRONTEND_URL to the preview URL and BROWSER_EXECUTABLE to your Chromium or Edge executable (default /usr/bin/chromium). See REVIEW.md for evidence and limitations.

## Deployment

GitHub Pages serves V2 at `/inspiratio-space-challenges-2026/`. The workflow builds with this Vite base path so JavaScript, styles and on-demand data files resolve under the repository URL. Only `frontend-v2/dist/` is published.

For initial setup, a repository admin renames this public repository to **inspiratio-space-challenges-2026** in **Settings → General → Repository name**, then enables **Settings → Pages → Source: GitHub Actions**. GitHub Pages takes its path from the repository name. The workflow refuses to publish under a different name; pull requests still validate the requested path before the rename. The deployment job also attempts to enable Pages if needed. After a successful workflow run, the `github-pages` environment records the deployed commit and URL. Later source updates deploy automatically after merging into `main`; no Sites account or manual upload is needed.

To reproduce the Pages build locally, run `npm run data:prepare` followed by `npm run build -- --base=/inspiratio-space-challenges-2026/`. Use `npx vite preview --host 127.0.0.1 --port 4173 --base=/inspiratio-space-challenges-2026/` and set `FRONTEND_URL=http://127.0.0.1:4173/inspiratio-space-challenges-2026/` for `npm run test:browser`.
