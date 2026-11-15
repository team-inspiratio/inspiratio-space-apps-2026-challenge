import test from "node:test";
import assert from "node:assert/strict";
import {
  cellPolygon,
  selectionWeights,
  aggregateSelection,
  aggregateIntervals,
} from "../src/aggregate.js";
const d = {
  cell_deg: 0.25,
  cells: { lat_idx: [360, 360], lon_idx: [720, 721] },
  months: ["2020-01", "2020-02"],
  est: [
    [10, 0],
    [20, 4],
  ],
  month_source: ["model_aqua", "snpp"],
  month_nrt: [false, false],
  month_input_complete: [true, false],
};
test("whole-cell selection conserves totals and keeps incomplete coverage", () => {
  const w = selectionWeights(d, cellPolygon(360, 720));
  assert.equal(w.length, 1);
  assert.ok(Math.abs(w[0][1] - 1) < 1e-10);
  assert.deepEqual(
    aggregateSelection(d, w).map((s) => [s.value, s.input_complete]),
    [
      [10, true],
      [0, false],
    ],
  );
});
test("partial-cell selection uses spherical overlap area", () => {
  const cell = cellPolygon(360, 720);
  cell.geometry.coordinates[0].forEach((p) => {
    if (p[0] === 0.25) p[0] = 0.125;
  });
  const w = selectionWeights(d, cell);
  assert.ok(Math.abs(w[0][1] - 0.5) < 1e-10);
  assert.equal(aggregateSelection(d, w)[0].value, 5);
});
test("no overlap means no data, never zero", () => {
  assert.equal(
    aggregateSelection(d, selectionWeights(d, cellPolygon(100, 100)))[0].value,
    null,
  );
});
test("resampling aggregates each draw before its quantile, observed months stay fixed", () => {
  const r = aggregateIntervals(
    d,
    [
      [0, 1],
      [1, 1],
    ],
    new Float32Array([5, 15, 0, 0, 30, 10, 4, 4]),
    2,
  );
  assert.equal(r.lo_90[1], 4);
  assert.equal(r.hi_90[1], 4);
  assert.ok(r.lo_90[0] <= 30 && r.hi_90[0] >= 30);
});
