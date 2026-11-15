import test from "node:test";
import assert from "node:assert/strict";
import { cellAt, cellIndex } from "../src/cell-layer.js";

test("hover lookup finds the 0.25° cell under a point", () => {
  // Cell lat_idx 500 (south edge 35°N), lon_idx 240 (west edge 120°W).
  const index = cellIndex({ lat_idx: [500, 501], lon_idx: [240, 240] });
  assert.equal(cellAt(35.1, -119.9, index), 0);
  assert.equal(cellAt(35.249, -119.751, index), 0);
  assert.equal(cellAt(35.26, -119.9, index), 1);
  assert.equal(cellAt(34.99, -119.9, index), -1, "outside the grid");
});
