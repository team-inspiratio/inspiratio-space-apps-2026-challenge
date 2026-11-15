# Inspiratio Version 2

Independent website source in `frontend-v2/`. The original website in `web/` and its deployment remain unchanged.

## Public website

**[Open Inspiratio V2](https://inspiratio-fire-activity-v2.hushedotter14.chatgpt.site)** — publicly accessible without a local development server.

The public site is hosted separately with Sites. GitHub stores the source; merging changes into `main` does not automatically update this deployment. Rebuild with the verified `global-v1` release assets and publish the resulting static output to update the public site.

## Local setup

Requires Node.js 22.16+ and npm.

```sh
cd frontend-v2
npm ci
npm run data:prepare
npm run build
npm run dev -- --port 5176
```

Data preparation requires authenticated GitHub CLI access to the existing global-v1 release and the repository Python environment. All downloaded assets are verified against the pinned SHA256 manifest. Downloaded data, dependencies and build output are ignored by Git. Without prepared data, the interface explicitly shows real limited samples; spatial selection is unavailable.

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

V2 has its own public deployment at the link above and does not replace the original website. Build with npm run build -- --base=./ for a separately hosted static directory. Prepare verified release data before building the full site. Do not change the existing Pages deployment to publish V2 unless that replacement is explicitly intended.
