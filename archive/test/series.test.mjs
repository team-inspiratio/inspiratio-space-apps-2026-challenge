import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { gunzipSync } from "node:zlib";
import {
  annualTotals,
  spliceGapReason,
  spliceSource,
} from "../src/series.js";

test("a year is only summed when all of its months are usable", () => {
  const months = ["2011-11", "2011-12", "2012-01", "2012-02"],
    values = [1, 2, 3, null];
  const a = annualTotals(months, values);
  assert.deepEqual(a.get(2011), {
    total: 3,
    complete: true,
    months: 2,
    partial: true,
  });
  assert.equal(a.get(2012).total, null, "one missing month blanks the year");
  const custom = annualTotals(months, values, (t) => t !== 0);
  assert.equal(custom.get(2011).total, null);
});

test("direct splice sensors follow the v1 definition", () => {
  assert.equal(spliceSource("2001-05"), "Terra MODIS as recorded");
  assert.equal(spliceSource("2012-01"), "Aqua MODIS as recorded");
  assert.equal(spliceSource("2014-01"), "S-NPP VIIRS as recorded");
});

const file = (r) => new URL(`../public/data/v1/${r}.json.gz`, import.meta.url);
const load = (r) => JSON.parse(gunzipSync(fs.readFileSync(file(r))));

test(
  "training region: the splice is blank exactly in 2012-02–2013-12 and outages, each with a reason",
  { skip: !fs.existsSync(file("california")) },
  () => {
    const d = load("california");
    const annual = annualTotals(d.months, d.totals.est_m0);
    assert.equal(annual.get(2012).total, null, "2012 (January only) not summed");
    assert.equal(annual.get(2013).total, null);
    assert.ok(annual.get(2011).total > 0 && annual.get(2014).total > 0);
    // The splice jumps several-fold at the sensor switch; the harmonized series does not.
    const h = annualTotals(d.months, d.totals.est);
    const mean = (a, ys) => ys.reduce((s, y) => s + a.get(y).total, 0) / ys.length;
    const pre = [2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011],
      post = [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021];
    assert.ok(mean(annual, post) / mean(annual, pre) > 3);
    d.months.forEach((m, t) => {
      const reason = spliceGapReason(d, d.totals.est_m0, t);
      if (d.totals.est_m0[t] != null) assert.equal(reason, null);
      else if (m >= "2012-02" && m <= "2013-12") assert.match(reason, /blind test/);
      else assert.match(reason, /outage/, m);
    });
    assert.ok(h.get(2012).total > 0, "harmonized 2012 is a full model year");
  },
);

test(
  "holdout region: the splice stops in 2012-01 and says why",
  { skip: !fs.existsSync(file("indo_gangetic")) },
  () => {
    const d = load("indo_gangetic");
    const t = d.months.indexOf("2018-06");
    assert.equal(d.totals.est_m0[t], null);
    assert.match(spliceGapReason(d, d.totals.est_m0, t), /held out/);
  },
);
