// Builds src/methods-data.json for the method & validation page from files that are
// already committed in this repository (reports/validation.json and the one-time
// grader output results/final-test/scores.json). Read-only: no network, no model,
// no FIRMS or VIIRS download. Run `npm run methods:data` after those reports change;
// test/methods-data.test.mjs fails if the committed JSON drifts from its sources.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
export const SOURCES = ["reports/validation.json", "results/final-test/scores.json"];
const r3 = (v) => (v == null ? null : Math.round(v * 1000) / 1000);
const r1 = (v) => (v == null ? null : Math.round(v * 10) / 10);
const roundAll = (o) =>
  Object.fromEntries(Object.entries(o).map(([k, x]) => [k, r3(x)]));
const pick = (o, keys) => Object.fromEntries(keys.map((k) => [k, o[k]]));
const REGIONS = [
  "california",
  "cordoba",
  "southern_africa",
  "north_australia",
  "central_siberia",
  "indo_gangetic",
];

export function buildMethodsData(repoRoot = path.resolve(here, "../..")) {
  // Text mode: a Windows checkout (core.autocrlf) must hash like the committed LF file.
  const read = (rel) =>
    fs.readFileSync(path.join(repoRoot, rel), "utf8").replaceAll("\r\n", "\n");
  const v = JSON.parse(read(SOURCES[0]));
  const ft = JSON.parse(read(SOURCES[1]));
  const m = v.scores.methods;
  const windows = ["main", "aux", "test1", "test2"];
  const ciOf = (x) => ({
    diff: r3(x.diff),
    lo: r3(x.ci95[0]),
    hi: r3(x.ci95[1]),
  });
  const totals = [];
  for (const test of ["test1", "test2"]) {
    const final = ft[test].scores.est_final.total_bias,
      m1s = ft[test].scores.est_m1s.total_bias;
    final.forEach((row, i) => {
      if (m1s[i].region !== row.region || m1s[i].year !== row.year)
        throw Error("Unexpected total_bias order in final-test scores");
      totals.push({
        test,
        region: row.region,
        year: +row.year,
        viirs: Math.round(row.V),
        E028: Math.round(row.H),
        M1s: Math.round(m1s[i].H),
      });
    });
  }
  const top = (gain, n) =>
    Object.entries(gain)
      .sort((a, b) => b[1] - a[1])
      .slice(0, n)
      .map(([feature, share]) => ({ feature, share: r1(share) }));
  return {
    sources: Object.fromEntries(
      SOURCES.map((rel) => [
        rel,
        crypto.createHash("sha256").update(read(rel)).digest("hex"),
      ]),
    ),
    grader: {
      run: "https://github.com/team-inspiratio/inspiratio-space-apps-2026/actions/runs/41768696897",
      answer_commit: "674b3f5",
      result_commit: "742547e",
      result_time_utc: "2026-11-04 03:50",
    },
    scores: {
      windows,
      male: Object.fromEntries(
        ["E028", "M1s", "QM", "M0"].map((k) => [
          k,
          Object.fromEntries(windows.map((w) => [w, r3(m[k][w].male)])),
        ]),
      ),
      diff: Object.fromEntries(
        ["validation_combined", "test1", "test2"].map((w) => [
          w,
          {
            M1s: ciOf(v.scores.diff_positive_means_E028_better[w].vs_M1s),
            QM: ciOf(v.scores.diff_positive_means_E028_better[w].vs_QM),
          },
        ]),
      ),
      by_region: Object.fromEntries(
        REGIONS.map((reg) => {
          const test = m.E028.test1.male_by_region[reg] != null ? "test1" : "test2";
          return [
            reg,
            {
              test,
              ...Object.fromEntries(
                ["E028", "M1s", "QM"].map((k) => [
                  k,
                  r3(m[k][test].male_by_region[reg]),
                ]),
              ),
            },
          ];
        }),
      ),
      aux: Object.fromEntries(
        ["test1", "test2"].map((w) => [
          w,
          Object.fromEntries(
            ["E028", "M1s"].map((k) => [
              k,
              Object.fromEntries(
                Object.entries(
                  pick(m[k][w], [
                    "zero_ge1",
                    "zero_ge5",
                    "low_mae",
                    "total_bias_mean_abs",
                    "season_corr_mean",
                  ]),
                ).map(([a, b]) => [a, r3(b)]),
              ),
            ]),
          ),
        ]),
      ),
      kappa: Object.fromEntries(
        Object.entries(v.scores.kappa).map(([w, o]) => [
          w,
          Object.fromEntries(Object.entries(o).map(([k, x]) => [k, r3(x)])),
        ]),
      ),
      coverage: Object.fromEntries(
        Object.entries(v.scores.coverage).map(([w, o]) => [
          w,
          {
            raw: r3(o.region_month_coverage),
            calibrated: r3(o.region_month_coverage_calibrated),
            scale: o.interval_scale,
            n: o.n_region_months,
          },
        ]),
      ),
    },
    totals,
    problem: {
      region: v.fig1_problem.region,
      ratio_min: r1(v.fig1_problem.snpp_over_aqua_yearly_2014_2021.min),
      ratio_max: r1(v.fig1_problem.snpp_over_aqua_yearly_2014_2021.max),
    },
    explain: {
      gain_count: top(v.fig4_explain.gain_share_pct.reg, 8),
      gain_detect: top(v.fig4_explain.gain_share_pct.clf, 8),
      deciles_aqua_count: {
        x: v.fig4_explain.deciles.aqua_count.x.map(r3),
        observed: v.fig4_explain.deciles.aqua_count.obs.map(r3),
        model: v.fig4_explain.deciles.aqua_count.model.map(r3),
      },
    },
    gfed: Object.fromEntries(
      ["california", "cordoba", "southern_africa"].map((reg) => [
        reg,
        Object.entries(v.gfed.regions[reg].per_year).map(([year, o]) => ({
          year: +year,
          harmonized: r3(o.harmonized_per_km2),
          // The splice has no S-NPP values in 2012-13 (withheld for the blind test),
          // so those years are left empty instead of plotting January alone or zero.
          splice: +year >= 2012 && +year <= 2013 ? null : r3(o.splice_per_km2),
          source: o.main_source,
        })),
      ]),
    ),
    drift: {
      eras: v.drift.eras,
      train: {
        auc: r3(v.drift.train.auc),
        by_region: roundAll(v.drift.train.auc_by_region),
        control: roundAll(v.drift.train.control_2022_2026.auc_by_region),
        control_auc: r3(v.drift.train.control_2022_2026.auc),
      },
      holdout: {
        auc: r3(v.drift.holdout.auc),
        by_region: roundAll(v.drift.holdout.auc_by_region),
        control: roundAll(v.drift.holdout.control_2022_2026.auc_by_region),
        control_auc: r3(v.drift.holdout.control_2022_2026.auc),
      },
    },
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const out = path.resolve(here, "../src/methods-data.json");
  fs.writeFileSync(out, JSON.stringify(buildMethodsData(), null, 1) + "\n");
  console.log("Wrote", path.relative(process.cwd(), out));
}
