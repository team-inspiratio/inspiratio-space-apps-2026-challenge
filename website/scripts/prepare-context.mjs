// Read scientific source documents only. Never import the previous frontend.
import fs from "node:fs";
const read = (p) =>
  JSON.parse(fs.readFileSync(new URL("../../" + p, import.meta.url)));
const regions = read("config/regions.json").regions;
const cases = read("docs/anomaly-cases.json").cases;
const examples = regions
  .map((r) => {
    const c = cases.find((c) => c.id.startsWith("real_" + r.name + "_"));
    return c
      ? {
          ...r,
          series: c.input.series,
          target: c.input.target,
          version: "v1",
          sample: true,
        }
      : null;
  })
  .filter(Boolean);
fs.writeFileSync(
  new URL("../src/context.json", import.meta.url),
  JSON.stringify({
    examples,
    scores: read("reports/validation.json").scores,
    global: read("reports/global-scores.json"),
    provenance:
      "docs/anomaly-cases.json; reports/validation.json; reports/global-scores.json",
  }),
);
