# Web frontend scope

The user explicitly assigned this work to the **web frontend** on 2026-11-04 and left G-global with its current data owner.

- Follow the root scientific and secret-handling restrictions. Use released frontend data and the existing anomaly contract; never alter frozen files, model inputs, splits, evaluations or test tags.
- Frontend source lives under `web/archive/website-v1/`. For this source-only handoff, append the user-requested frontend section to root `PROGRESS.md`; do not change its machine-readable data-task status or claim G-global.
- The user explicitly requested branch `feat/web` from latest main and a draft PR for this handoff. Do not push to the data owner's branch.
- Never commit release Parquet, generated data, credentials, node_modules, local runtime state or build output. `scripts/prepare-data.mjs` pins and checks the published input manifest.
- Before delivery, run `npm ci`, `npm run data:prepare`, the existing `npm test` and `npm run build`, plus the repository pre-commit, tests and guardrails. This handoff does not change functions or deployment and must not introduce new tests.
- Keep interval and source labels scientifically accurate. Do not manufacture raw point downloads, unavailable source observations, or custom-area uncertainty by adding cell quantiles.
