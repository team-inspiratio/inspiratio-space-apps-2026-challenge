import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { gunzipSync } from "node:zlib";
import { aggregateIntervals } from "../src/aggregate.js";
const root = new URL("../public/data/v1/", import.meta.url);
const regions = [
  "california",
  "cordoba",
  "southern_africa",
  "north_australia",
  "central_siberia",
  "indo_gangetic",
];
for (const region of regions)
  test(
    `published data conservation: ${region}`,
    { skip: !fs.existsSync(new URL(region + ".json.gz", root)) },
    () => {
      const d = JSON.parse(
        gunzipSync(fs.readFileSync(new URL(region + ".json.gz", root))),
      );
      assert.equal(d.months.length, 312);
      const bytes = gunzipSync(
        fs.readFileSync(new URL(region + ".raw.f32.gz", root)),
      );
      const raw = new Float32Array(
        bytes.buffer,
        bytes.byteOffset,
        bytes.byteLength / 4,
      );
      d.months.forEach((m, t) => {
        const sum = d.est.reduce((s, row) => s + row[t], 0);
        assert.ok(
          Math.abs(sum - d.totals.est[t]) <= d.est.length * 0.0051,
          `${m}: rounded cells must conserve totals within declared 0.01 rounding`,
        );
        for (const [j, key] of [
          "est_m0",
          "aqua_count",
          "terra_count",
          "snpp_count",
        ].entries()) {
          let total = 0,
            missing = false;
          for (let i = 0; i < d.est.length; i++) {
            const v = raw[(i * 312 + t) * 4 + j];
            if (!Number.isFinite(v)) missing = true;
            else total += v;
          }
          if (d.totals[key][t] == null)
            assert.equal(
              missing,
              true,
              `${m}/${key}: preserve unavailable values`,
            );
          else {
            assert.equal(missing, false);
            assert.equal(total, d.totals[key][t], `${m}/${key}`);
          }
        }
      });
    },
  );
test("custom stability bands use empirical draw quantiles even if point estimate is outside them", () => {
  const d = { months: ["2001-01"], est: [[100]], month_source: ["model_aqua"] };
  const result = aggregateIntervals(d, [[0, 1]], new Float32Array([1, 2]), 2);
  assert.ok(Math.abs(result.lo_90[0] - 1.05) < 1e-12);
  assert.ok(Math.abs(result.hi_90[0] - 1.95) < 1e-12);
});
