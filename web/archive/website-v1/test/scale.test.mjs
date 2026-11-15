import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { gunzipSync } from "node:zlib";
import {
  logPercentileScale,
  rampColor,
  RAMP,
  ZERO_COLOR,
} from "../src/scale.js";

test("ramp endpoints are the lightest and darkest palette colours", () => {
  assert.equal(rampColor(0), RAMP[0]);
  assert.equal(rampColor(1), RAMP.at(-1));
  assert.equal(rampColor(-3), RAMP[0]);
  assert.equal(rampColor(7), RAMP.at(-1));
});

test("log scale spans the 5th–99th percentile of positive values", () => {
  const values = Array.from({ length: 101 }, (_, i) => 10 ** (i / 25)); // 1 … 10^4
  const s = logPercentileScale([...values, 0, null]);
  assert.ok(Math.abs(Math.log10(s.lo) - 0.2) < 1e-9);
  assert.ok(Math.abs(Math.log10(s.hi) - 3.96) < 1e-9);
  assert.equal(s.position(s.lo), 0);
  assert.equal(s.position(s.hi), 1);
  assert.ok(Math.abs(s.position(10 ** 2.08) - 0.5) < 1e-9);
  assert.equal(s.color(1e9), RAMP.at(-1), "above P99 clamps to darkest");
  assert.equal(s.color(1e-3), RAMP[0], "below P5 clamps to lightest");
  assert.equal(s.color(0), ZERO_COLOR, "zero has its own neutral colour");
  assert.equal(s.color(null), null, "missing stays missing");
});

test("degenerate inputs do not divide by zero", () => {
  const flat = logPercentileScale([5, 5, 5]);
  assert.ok(Number.isFinite(flat.position(5)));
  const empty = logPercentileScale([0, null]);
  assert.equal(empty.color(0), ZERO_COLOR);
});

const california = new URL(
  "../public/data/v1/california.json.gz",
  import.meta.url,
);
test(
  "California: the 2020-09 peak and a quiet May are far apart on the ramp",
  { skip: !fs.existsSync(california) },
  () => {
    const d = JSON.parse(gunzipSync(fs.readFileSync(california)));
    const s = logPercentileScale(d.totals.est);
    const at = (m) => s.position(d.totals.est[d.months.indexOf(m)]);
    assert.equal(at("2020-09"), 1);
    assert.ok(at("2020-05") < 0.2, `2020-05 at ${at("2020-05")}`);
    // The ramp is actually used: every fifth of it holds at least 5% of months.
    const bins = [0, 0, 0, 0, 0];
    for (const v of d.totals.est)
      if (v > 0) bins[Math.min(4, Math.floor(s.position(v) * 5))]++;
    for (const n of bins) assert.ok(n >= 0.05 * d.months.length, `${bins}`);
  },
);
