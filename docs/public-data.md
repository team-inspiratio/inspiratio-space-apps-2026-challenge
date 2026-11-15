# Public data and source availability

This public repository contains the V2 website, scientific documentation, reports and global frontend data. Website documentation and evidence links point to files in this repository.

## Run V2 from a public clone

Node.js 22.16+ and npm are required.

```sh
cd frontend-v2
npm ci
npm run data:prepare
npm test
npm run build
```

`data:prepare` reads the bundled files under `inspiratio-site/public/data/global-v1/`. It verifies `index.json` and the 20 regional JSON gzip files against `results/expected/dataset-global-v1.sha256`, then copies them into V2's ignored `public/data/global-v1/` directory. No account, token, GitHub CLI, Python or external data download is required. It removes an existing readiness marker before checking files, and writes a new marker only after verification and copying succeed.

The catalog covers the global partitions and six demonstration boxes. V2 loads partitions on demand and excludes overlapping demonstration boxes when aggregating a custom area. Custom areas retain the existing point estimates and do not manufacture uncertainty intervals.

## Files available here

- [Bundled global frontend data](../inspiratio-site/public/data/global-v1/): the catalog and 20 compressed regional files used by V2, under CC BY 4.0.
- [SHA256 manifest](../results/expected/dataset-global-v1.sha256): the required frontend files are checked against this manifest; its other entries are not all distributed here.
- [Data card](data-card.md), [global data interface](data-interface-global.md) and [validation report](../reports/validation.md).
- [Recorded blind-test outputs](../results/final-test/): public scores and summaries. These are result files, not a new grading run.

The separate `meta.json` file, full processed Parquet/CSV tables, raw detections and resample assets are not included in this frontend bundle. V2 does not require them. This repository currently has no GitHub Release assets. The legacy `web/` data preparation and `pipeline.py all --from-release` require the appropriate assets to be published in this public repository before those optional paths can work. Do not substitute the global bundle for the legacy v1 data: they describe different model versions.

Reproduction from raw NASA FIRMS data uses `pipeline.py all` and the existing scientific guardrails, with the operator's own FIRMS key and data directory. V2 setup does not run that pipeline or change scientific results.

## Hosting

V2 is published by [GitHub Pages](https://team-inspiratio.github.io/inspiratio-space-apps-2026-challenge/) under this repository. The [deployment workflow](../.github/workflows/pages-v2.yml) verifies the bundled data, tests the production build under the repository path, and publishes `frontend-v2/dist/` after relevant changes merge into `main`. Pull requests validate without publishing. Initial setup requires GitHub Pages to use GitHub Actions as its source; see [V2 deployment](../frontend-v2/README.md#deployment).
