import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { anomaly, boxWeight, subset, csv, annual } from "../src/science.js";
const doc = JSON.parse(
  fs.readFileSync(new URL("../../docs/anomaly-cases.json", import.meta.url)),
);
for (const c of doc.cases)
  test(c.id, () => {
    const { series, target, as_of, baseline } = c.input,
      result = anomaly(series, target, as_of, baseline);
    assert.deepEqual(
      Object.keys(result).sort(),
      Object.keys(c.expected).sort(),
    );
    for (const [key, v] of Object.entries(c.expected))
      typeof v === "number"
        ? assert.ok(
            Math.abs(result[key] - v) <= 1e-9 * Math.max(1, Math.abs(v)),
            key,
          )
        : assert.deepEqual(result[key], v, key);
  });
test("area fractions preserve spherical cell area", () => {
  assert.equal(boxWeight(0, 0, [0, 0, 0.25, 0.25]), 1);
  assert.equal(boxWeight(0, 0, [0.25, 0, 0.5, 0.25]), 0);
  assert.ok(Math.abs(boxWeight(0, 0, [0, 0, 0.125, 0.25]) - 0.5) < 1e-10);
});
const d = {
  months: ["2020-01"],
  month_source: ["model_aqua"],
  month_nrt: [false],
  month_input_complete: [true],
  totals: { est: [30], lo_90: [10], hi_90: [50] },
  cells: { lat_idx: [360, 360], lon_idx: [720, 721] },
  est: [[10], [20]],
};
test("custom region weights counts and does not manufacture uncertainty", () => {
  const r = subset(d, [0, 0, 0.375, 0.25])[0];
  assert.equal(r.value, 20);
  assert.equal(r.lo, null);
  assert.equal(r.hi, null);
  assert.equal(r.raw, null);
});
test("no overlap and invalid boxes are errors, not zeros", () => {
  assert.throws(() => subset(d, [5, 5, 6, 6]));
  assert.throws(() => subset(d, [1, 0, 0, 1]));
});
test("annual series require all twelve complete months", () => {
  assert.equal(
    annual([{ month: "2020-01", value: 1, input_complete: true }])[0].value,
    null,
  );
});
test("CSV preserves nulls, coverage, source and release attribution", () => {
  const text = csv(
    [
      {
        month: "2020-01",
        value: 0,
        source: "snpp",
        input_complete: false,
        nrt: true,
      },
    ],
    'a"b',
    "global-v1",
  );
  assert.match(text, /"a""b"/);
  assert.match(text, /"0","","","","snpp","false","true"/);
});
