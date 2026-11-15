import test from "node:test";
import assert from "node:assert/strict";
import { approx, count, int, ordinal, roundEstimate } from "../src/format.js";

test("estimates never show decimals", () => {
  assert.equal(approx(11623.85), "≈ 11,600");
  assert.equal(approx(935.99), "≈ 936");
  assert.equal(approx(37.4), "≈ 37");
  assert.equal(approx(125460.2), "≈ 125,000");
  assert.equal(approx(0.3), "< 1");
  assert.equal(approx(0), "0");
  assert.equal(approx(null), "—");
  assert.equal(roundEstimate(1234567), 1230000);
  for (const v of [0.6, 3.14159, 99.5, 1234.5678, 98765.4321])
    assert.doesNotMatch(approx(v), /\.\d/, String(v));
});

test("exact counts stay exact; estimates and fractions are approximate", () => {
  assert.equal(count(125460, false), "125,460");
  assert.equal(count(125460, true), "≈ 125,000");
  assert.equal(count(4237.94, false), "≈ 4,240");
  assert.equal(int(1520), "1,520");
});

test("ordinal percentiles", () => {
  assert.deepEqual(
    [0, 1, 2, 3, 4, 11, 12, 13, 21, 22, 79.6, 100].map(ordinal),
    ["0th", "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "80th", "100th"],
  );
});
