import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { anomaly } from "../src/anomaly.js";
const doc = JSON.parse(
  fs.readFileSync(new URL("./fixtures/anomaly-cases.json", import.meta.url)),
);
for (const c of doc.cases)
  test(`repository contract: ${c.id}`, () => {
    const { series, target, as_of, baseline } = c.input;
    const got = anomaly(series, target, as_of, baseline);
    for (const [k, v] of Object.entries(c.expected)) {
      if (typeof v === "number")
        assert.ok(
          Math.abs(got[k] - v) <= 1e-9 * Math.max(1, Math.abs(v)),
          `${k}: ${got[k]} != ${v}`,
        );
      else assert.deepEqual(got[k], v, k);
    }
    assert.deepEqual(Object.keys(got).sort(), Object.keys(c.expected).sort());
  });
