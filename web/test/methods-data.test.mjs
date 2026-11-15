import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { buildMethodsData } from "../scripts/methods-data.mjs";

const committed = JSON.parse(
  fs.readFileSync(new URL("../src/methods-data.json", import.meta.url)),
);

test("method page numbers match the committed reports (run npm run methods:data if not)", () => {
  assert.deepEqual(committed, JSON.parse(JSON.stringify(buildMethodsData())));
});

test("headline numbers on the method page agree with reports/final-test.md", () => {
  const m = committed.scores.male;
  assert.equal(m.E028.test1, 0.258);
  assert.equal(m.M1s.test1, 0.332);
  assert.equal(m.E028.test2, 0.644);
  assert.equal(Math.round((1 - m.E028.test1 / m.M1s.test1) * 100), 22);
  assert.equal(committed.scores.coverage.test1.calibrated, 0.955);
  assert.equal(committed.scores.coverage.test2.calibrated, 0.559);
  // Yearly totals: training regions within ±9%, Central Siberia / Indo-Gangetic 14–45% low.
  const bias = (r) =>
    committed.totals.filter((t) => t.region === r).map((t) => t.E028 / t.viirs - 1);
  for (const r of ["california", "cordoba", "southern_africa"])
    for (const b of bias(r)) assert.ok(Math.abs(b) < 0.09, `${r} ${b}`);
  const low = [...bias("central_siberia"), ...bias("indo_gangetic")];
  assert.equal(Math.round(-Math.max(...low) * 100), 14);
  assert.equal(Math.round(-Math.min(...low) * 100), 45);
});

test("GFED splice is left empty in the withheld 2012–13 years", () => {
  for (const rows of Object.values(committed.gfed))
    for (const r of rows)
      if (r.year === 2012 || r.year === 2013) assert.equal(r.splice, null);
});
