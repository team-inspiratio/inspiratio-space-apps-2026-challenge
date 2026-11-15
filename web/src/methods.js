// Method & validation page: a standalone, linkable page (/methods.html) with the
// six core analysis figures redrawn in the site's style, the blind-test scores,
// the independent checks, the process disclosure and the limits.
import "./style.css";
import "./methods.css";
import data from "./methods-data.json";
import {
  COLORS,
  groupedBars,
  legend,
  open,
  path,
  band,
  yAxisLinear,
  yAxisLog,
  linearScale,
  compact,
  tipAttr,
} from "./charts.js";
import { REPO, icon, siteHeader, gzipBytes } from "./ui.js";
import { approx, int } from "./format.js";

const NAMES = {
  california: "California",
  cordoba: "Córdoba",
  southern_africa: "Southern Africa",
  north_australia: "Northern Australia",
  central_siberia: "Central Siberia",
  indo_gangetic: "Indo-Gangetic Plain",
};
const REGIONS = Object.keys(NAMES);
const HOLDOUT = new Set(["north_australia", "central_siberia", "indo_gangetic"]);
const pct = (v) => Math.round(v * 100) + "%";
const pct1 = (v) => (v * 100).toFixed(1) + "%";
const signedPct = (v) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.round(Math.abs(v) * 100) + "%";
const f3 = (v) => v.toFixed(3);
const s = data.scores;
const improvement = 1 - s.male.E028.test1 / s.male.M1s.test1;
const harder = s.male.E028.test2 / s.male.E028.test1;
const WINDOW = {
  main: ["Validation", "2014–15"],
  aux: ["Validation", "2016–17"],
  test1: ["Test 1: training regions", "2012–13"],
  test2: ["Test 2: holdout regions", "2012–21"],
};

// Mean |yearly total bias| per region, straight from the grader's totals.
const totalsBy = (reg) => data.totals.filter((t) => t.region === reg);
const meanBias = (reg, key) => {
  const rows = totalsBy(reg);
  return rows.reduce((a, t) => a + Math.abs(t[key] / t.viirs - 1), 0) / rows.length;
};
const biasRange = (regs) => {
  const b = regs.flatMap((r) => totalsBy(r).map((t) => t.E028 / t.viirs - 1));
  return [Math.min(...b), Math.max(...b)];
};
const trainMaxAbs = Math.max(
  ...["california", "cordoba", "southern_africa"].flatMap((r) =>
    totalsBy(r).map((t) => Math.abs(t.E028 / t.viirs - 1)),
  ),
);
const lowRange = biasRange(["central_siberia", "indo_gangetic"]);

function fig({ id, n, title, sub, foot = "", png, table, legendHtml = "" }) {
  return `<figure class="fig" id="${id}">
    <figcaption><p class="fig-num">Figure ${n}</p><h3><a href="#${id}">${title}</a></h3><p class="fig-sub">${sub}</p></figcaption>
    ${legendHtml}<div class="fig-body" data-fig="${id}"><p class="fig-loading">Drawing…</p></div>
    ${foot ? `<p class="fig-foot">${foot}</p>` : ""}
    <div class="fig-links">${table ? `<details><summary>Data table</summary><div class="table-wrap">${table}</div></details>` : ""}${png ? `<a href="/methods/${png}" target="_blank" rel="noopener">Original analysis figure (PNG) ${icon("arrow")}</a>` : ""}</div>
  </figure>`;
}
const table = (head, rows, cls = "") =>
  `<table class="m-table ${cls}"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c, i) => (i === 0 ? `<th>${c}</th>` : `<td>${c}</td>`)).join("")}</tr>`).join("")}</tbody></table>`;

// ---------- page ----------
const tiles = [
  [`${Math.round(improvement * 100)}% lower`, `test error than the ratio baseline in the training regions (MALE ${f3(s.male.E028.test1)} vs ${f3(s.male.M1s.test1)})`],
  [`${harder.toFixed(1)}× larger`, `error in regions the model never saw (MALE ${f3(s.male.E028.test2)}) — read those regions with care`],
  ["Pre-registered", "metrics, data splits and the selection rule were fixed on 2026-11-03, before any model was fitted"],
  ["Tested once", `by an external grader (${data.grader.result_time_utc} UTC); the model was not changed afterwards`],
];
const toc = [
  ["how", "How it works"],
  ["findings", "What we found"],
  ["scores", "Test scores"],
  ["checks", "Independent checks"],
  ["process", "How we kept it honest"],
  ["limits", "Limits"],
  ["reports", "Full reports"],
];

const scoreRows = ["E028", "M1s", "QM", "M0"].map((k) => [
  { E028: "<strong>LightGBM E028</strong> (final model)", M1s: "Ratio baseline M1s", QM: "Quantile mapping QM", M0: "Direct splice M0" }[k],
  ...s.windows.map((w) => (k === "E028" ? `<strong>${f3(s.male[k][w])}</strong>` : f3(s.male[k][w]))),
]);
const diffCell = (d) => `${f3(d.diff)} <small>(${f3(d.lo)} to ${f3(d.hi)})</small>`;
const aux = s.aux;
const auxRow = (label, key, fmt, better = "lower") => [
  `${label} <small>${better} is better</small>`,
  fmt(aux.test1.E028[key]),
  fmt(aux.test1.M1s[key]),
  fmt(aux.test2.E028[key]),
  fmt(aux.test2.M1s[key]),
];

document.querySelector("#app").innerHTML = `${siteHeader("methods")}
<main class="methods-page">
  <section class="m-hero">
    <p class="eyebrow">METHOD & VALIDATION</p>
    <h1>Making the record comparable — and testing it honestly.</h1>
    <p class="m-lead">MODIS (since 2000) and VIIRS (since 2012) see the same fires very differently: VIIRS records about five times as many detections. Joining the two records as they are makes fire activity appear to jump at 2012. This atlas converts MODIS months to the S-NPP VIIRS scale with a model that was chosen by a fixed rule and then tested once, blind.</p>
    <div class="m-tiles">${tiles.map(([a, b]) => `<div><strong>${a}</strong><span>${b}</span></div>`).join("")}</div>
  </section>
  <nav class="m-toc" aria-label="On this page">${toc.map(([id, l]) => `<a href="#${id}">${l}</a>`).join("")}</nav>

  <section class="m-section" id="how"><h2>How it works</h2>
    <div class="method-steps"><div><span>01</span><strong>Learn from the overlap</strong><p>From 2014 to mid-2021, MODIS and S-NPP VIIRS watched the same three training regions. The model learns, per 0.25° cell and month, how many VIIRS detections correspond to what MODIS saw.</p></div><div><span>02</span><strong>Estimate the earlier years</strong><p>A two-stage LightGBM model (any VIIRS fire? then how many?) uses only MODIS inputs — never the year, the region name or any VIIRS information. Before Aqua (2000–02), Terra bridges the gap at lower confidence.</p></div><div><span>03</span><strong>Test backwards and elsewhere</strong><p>2012–13 in the training regions and three whole regions were locked away. The chosen model was scored on them once, by a grader running outside the analysis machine.</p></div></div>
  </section>

  <section class="m-section" id="findings"><h2>What we found</h2>
    <p class="m-intro">Each figure's title is its conclusion. Hover or tap a mark for values; every figure links to the original analysis plot.</p>
    ${fig({
      id: "sensor-jump",
      n: 1,
      title: `Joining MODIS to VIIRS as they are makes fire activity jump about 5× at 2012`,
      sub: `${NAMES[data.problem.region]}, monthly fire detections (log scale). Same fires, two sensors: in 2014–21 S-NPP VIIRS recorded ${data.problem.ratio_min}–${data.problem.ratio_max}× as many detections per year as Aqua MODIS.`,
      legendHtml: legend([
        { label: "Direct splice: Aqua MODIS until 2012-01, S-NPP VIIRS after", color: COLORS.splice, kind: "line" },
        { label: "Aqua MODIS, continued for comparison", color: COLORS.aqua, kind: "dash" },
      ]),
      foot: "2012-02 to 2013-12 is empty: S-NPP VIIRS for those months is withheld from the analysis for the blind test.",
      png: "d1-1-problem.png",
    })}
    ${fig({
      id: "test-totals",
      n: 2,
      title: `In the locked test years, yearly totals from MODIS alone came within ${Math.ceil(trainMaxAbs * 100)}% of true VIIRS in the training regions — but ${Math.round(-lowRange[1] * 100)}–${Math.round(-lowRange[0] * 100)}% too low in Central Siberia and the Indo-Gangetic Plain`,
      sub: "Yearly detections: true S-NPP VIIRS (computed by the external grader) against the final model and the ratio baseline. Test 1: training regions, 2012–13 (2012 = Feb–Dec). Test 2: holdout regions, 2012–21 (2021 = Jan–Jun).",
      legendHtml: legend([
        { label: "True S-NPP VIIRS (grader)", color: COLORS.viirs },
        { label: "LightGBM E028, MODIS inputs only", color: COLORS.harmonized },
        { label: "Ratio baseline M1s", color: COLORS.m1s },
      ]),
      table: table(
        ["Region", "Year", "True VIIRS", "E028", "E028 bias", "M1s", "M1s bias"],
        data.totals.map((t) => [NAMES[t.region], t.year, int(t.viirs), int(t.E028), signedPct(t.E028 / t.viirs - 1), int(t.M1s), signedPct(t.M1s / t.viirs - 1)]),
      ),
      png: "d1-2-test-totals.png",
    })}
    ${fig({
      id: "scores-chart",
      n: 3,
      title: `The model beats the ratio and quantile-mapping baselines in all four windows; the holdout regions are about ${harder.toFixed(1)}× harder for every method`,
      sub: "Left: primary score, MALE (mean absolute log error; lower is better). The direct splice is off the scale (MALE 1.8–2.3). Right: how much lower E028's error is, with 95% year × region block-bootstrap intervals; none crosses zero.",
      legendHtml: legend([
        { label: "LightGBM E028", color: COLORS.harmonized },
        { label: "Ratio baseline M1s", color: COLORS.m1s },
        { label: "Quantile mapping QM", color: COLORS.qm },
      ]),
      table: table(["Method", ...s.windows.map((w) => WINDOW[w].join(" "))], scoreRows),
      png: "d1-3-scores.png",
    })}
    ${fig({
      id: "explain",
      n: 4,
      title: "The model is mainly a MODIS-count converter: about 8 VIIRS detections per MODIS detection where MODIS sees one or two, about 5 in big clusters",
      sub: "Left: which inputs the count stage relies on (share of total gain). Right: VIIRS-scale detections per Aqua detection, by decile of Aqua detections in the cell-month, training rows 2014–21 (in-sample). Fire radiative power and pixel size shift the ratio by 20–30%; latitude mostly acts as a region label (see the full report).",
      legendHtml: legend([
        { label: "Observed S-NPP / Aqua (open squares)", color: COLORS.viirs, kind: "square" },
        { label: "Model / Aqua", color: COLORS.harmonized, kind: "line" },
      ]),
      table: table(
        ["Input", "Count stage (%)", "Detection stage (%)"],
        data.explain.gain_count.map((g) => [g.feature, g.share, data.explain.gain_detect.find((d) => d.feature === g.feature)?.share ?? "< top 8"]),
      ),
      png: "d1-4-explain.png",
    })}
    ${fig({
      id: "series",
      n: 5,
      title: "Harmonized history, 2000-11 to 2026-10, on the VIIRS scale: no step at 2012, seasons and year-to-year swings kept",
      sub: "Monthly detections per region (log scale). Holdout regions are model estimates in every month.",
      legendHtml: legend([
        { label: "Model estimate", color: COLORS.harmonized, kind: "line" },
        { label: "Stability band (calibrated 5–95%)", color: COLORS.band, kind: "band" },
        { label: "Observed VIIRS (S-NPP; scaled NOAA-20 in gaps)", color: COLORS.viirs, kind: "line" },
        { label: "MODIS as recorded, before 2012", color: COLORS.aqua, kind: "dash" },
        { label: "Terra-only bridge months (low confidence)", color: "#f1e6cc", kind: "band" },
      ]),
      png: "d1-5-series.png",
    })}
  </section>

  <section class="m-section" id="scores"><h2>Blind-test scores</h2>
    <p class="m-intro">Scored once by the grader workflow on GitHub Actions (<a href="${data.grader.run}" target="_blank" rel="noopener">run record</a>, results commit <code>${data.grader.result_commit}</code>, ${data.grader.result_time_utc} UTC). MALE is the mean of |ln(estimate + 1) − ln(VIIRS + 1)| over evaluation rectangle-months with at least 10 VIIRS detections; lower is better.</p>
    <h3 id="scores-primary">Primary score (MALE)</h3>
    <div class="table-wrap">${table(["Method", ...s.windows.map((w) => `${WINDOW[w][0]}<br/><small>${WINDOW[w][1]}</small>`)], scoreRows, "scores")}</div>
    <h3 id="scores-advantage">How much lower E028's error is <small>(difference in MALE, 95% interval)</small></h3>
    <div class="table-wrap">${table(
      ["Compared with", "Validation (both windows)", "Test 1", "Test 2"],
      [
        ["Ratio baseline M1s", diffCell(s.diff.validation_combined.M1s), diffCell(s.diff.test1.M1s), diffCell(s.diff.test2.M1s)],
        ["Quantile mapping QM", diffCell(s.diff.validation_combined.QM), diffCell(s.diff.test1.QM), diffCell(s.diff.test2.QM)],
      ],
    )}</div>
    <h3 id="scores-regions">By region</h3>
    <div class="table-wrap">${table(
      ["Region", "Test", "E028", "M1s", "QM"],
      REGIONS.map((r) => [NAMES[r] + (HOLDOUT.has(r) ? " <small>holdout</small>" : ""), s.by_region[r].test === "test1" ? "1" : "2", `<strong>${f3(s.by_region[r].E028)}</strong>`, f3(s.by_region[r].M1s), f3(s.by_region[r].QM)]),
    )}</div>
    <p class="m-note">Central Siberia (boreal forest, far outside the training latitudes) has the largest error for every method; estimates there are not reliable.</p>
    <h3 id="scores-checks">Other checks</h3>
    <div class="table-wrap">${table(
      ["Check", "Test 1 · E028", "Test 1 · M1s", "Test 2 · E028", "Test 2 · M1s"],
      [
        auxRow("Zero-fire months given ≥ 1 detection", "zero_ge1", pct1),
        auxRow("Zero-fire months given ≥ 5 detections", "zero_ge5", pct1),
        auxRow("Error in months with 1–9 fires (detections)", "low_mae", (v) => v.toFixed(1)),
        auxRow("Yearly total bias, mean of |bias|", "total_bias_mean_abs", pct1),
        auxRow("Seasonal correlation", "season_corr_mean", f3, "higher"),
        ["Anomaly-grade agreement with VIIRS (κ) <small>higher is better</small>", f3(s.kappa.test1.E028), f3(s.kappa.test1.M1s), f3(s.kappa.test2.E028), f3(s.kappa.test2.M1s)],
        [`Stability bands covering the truth <small>nominal 90%, after ×${s.coverage.test1.scale} calibration</small>`, pct1(s.coverage.test1.calibrated), "—", pct1(s.coverage.test2.calibrated), "—"],
      ],
      "checks",
    )}</div>
    <p class="m-note"><strong>Two of the selection guardrails fail in Test 2.</strong> In unseen regions the model gives zero-fire months detections more often than the ratio baseline (${pct1(aux.test2.E028.zero_ge1)} vs ${pct1(aux.test2.M1s.zero_ge1)}, beyond the 5-point tolerance), and its error in months with 1–9 fires is about twice as large. These are reported, not fixed: the model was not changed after the test.</p>
  </section>

  <section class="m-section" id="checks"><h2>Independent checks</h2>
    ${fig({
      id: "gfed",
      n: 6,
      title: "Against an independent reference (GFED4.1s burned area, 2003–16), harmonized detections per burned km² keep their level across 2012; the direct splice jumps about 5×",
      sub: "Detections per km² of burned area, by year. GFED is a separate burned-area product, so a level step at the sensor switch would show up here. Clearest in Southern Africa and Córdoba; California has few burned km² per year and is noisy.",
      legendHtml: legend([
        { label: "Harmonized (model estimate to 2013)", color: COLORS.harmonized, kind: "line" },
        { label: "Observed S-NPP VIIRS (2014–16)", color: COLORS.viirs, kind: "dot" },
        { label: "Direct splice (Aqua, then S-NPP)", color: COLORS.splice, kind: "dash" },
      ]),
      table: table(
        ["Region", "Year", "Harmonized per km²", "Direct splice per km²"],
        Object.entries(data.gfed).flatMap(([r, rows]) => rows.map((x) => [NAMES[r], x.year, x.harmonized.toFixed(2), x.splice == null ? "withheld" : x.splice.toFixed(2)])),
      ),
      png: "d1-s1-gfed.png",
    })}
    ${fig({
      id: "era-shift",
      n: 7,
      title: `Era-shift check: the MODIS inputs of 2002–11 and 2014–21 are hard to tell apart (AUC ${data.drift.train.auc.toFixed(2)} training, ${data.drift.holdout.auc.toFixed(2)} holdout); the same test does catch the known drift after 2022`,
      sub: "The model learned on 2014–21 and is applied to 2002–11. A classifier tries to tell from MODIS inputs alone which era a cell-month comes from: 0.5 means it cannot. As a control, it easily separates 2002–11 from 2022–26, when the MODIS orbits are known to drift.",
      legendHtml: legend([
        { label: "2002–11 vs 2014–21 (the question)", color: COLORS.harmonized },
        { label: "2002–11 vs 2022–26 (control: known drift)", color: COLORS.qm },
        { label: "0.5 = cannot tell the eras apart", color: COLORS.rule, kind: "dash" },
      ]),
      table: table(
        ["Region", "2002–11 vs 2014–21", "2002–11 vs 2022–26"],
        REGIONS.map((r) => {
          const g = HOLDOUT.has(r) ? data.drift.holdout : data.drift.train;
          return [NAMES[r], g.by_region[r].toFixed(3), g.control[r].toFixed(3)];
        }),
      ),
      png: "d1-6-era-shift.png",
    })}
  </section>

  <section class="m-section" id="process"><h2>How we kept it honest</h2>
    <ol class="m-timeline">
      <li><time>2026-11-03</time><strong>Pre-registration before any model.</strong> Metrics, data splits, the selection rule and its thresholds were written down and frozen before any model was fitted or any validation score was seen (<a href="${REPO}/blob/main/docs/preregistration.md" target="_blank" rel="noopener">pre-registration</a>, commit <a href="${REPO}/commit/7d1aa0c" target="_blank" rel="noopener"><code>7d1aa0c</code></a>).</li>
      <li><time>Throughout</time><strong>The test answers never reached the analysis machine.</strong> S-NPP VIIRS for 2012–13 and all VIIRS data of the three holdout regions are blocked at download and import by three layers of guardrails (an editor hook, a pre-commit check and CI on every push). Only the grader workflow downloads them.</li>
      <li><time>Before the test</time><strong>Model chosen on validation data only.</strong> 37 LightGBM experiments plus the baselines were scored by a frozen judge on two validation windows, and the winner had to pass a fixed rule: at least 10% better than the ratio baseline, by more than one standard error, no window or region worse, guardrail metrics within tolerance. The loop was stopped early for time (37 of up to 150 experiments). A fresh AI reviewer checked the top three for leakage before the choice.</li>
      <li><time>2026-11-04</time><strong>The test ran once.</strong> A person pushed the <code>final-test</code> tag — the AI is not allowed to. The first push did not reach GitHub and was repeated; the grader workflow ran once (<a href="${data.grader.run}" target="_blank" rel="noopener">run record</a>) and its scores were committed at ${data.grader.result_time_utc} UTC (<code>${data.grader.result_commit}</code>). The weak holdout results are reported in full and the model was not changed.</li>
      <li><time>AI use</time><strong>Who did what.</strong> Claude Code (Anthropic) wrote and ran the data and modelling code, the experiments and the reports. This web front end was generated by Codex (OpenAI) and then revised by Claude (colour scale, sensor-switch chart, estimate marking, this page). People approved the plan, chose the holdout regions, reviewed the judge before it was frozen, pushed the test tag and approve every merge. Details: <a href="${REPO}/blob/main/docs/ai-usage.md" target="_blank" rel="noopener">AI usage statement</a>.</li>
    </ol>
  </section>

  <section class="m-section" id="limits"><h2>Read the limits alongside the results</h2>
    <ul class="limits">
      <li><strong>Detections are not individual fires.</strong> They do not measure burned area, disaster severity or future fire risk.</li>
      <li><strong>Unseen regions have much larger errors.</strong> Holdout MALE is about ${harder.toFixed(1)} times the training-region result. Yearly totals run low by about 22–35% in the Indo-Gangetic Plain and 14–45% in Central Siberia; Northern Australia stays within ±5% until 2019. The same will apply to any new region.</li>
      <li><strong>Few-fire places are the weak spot.</strong> In unseen regions the model gives zero-fire months detections more often than the ratio baseline and errs more in months with 1–9 fires.</li>
      <li><strong>Stability is not total uncertainty.</strong> Bands show variation when the training years are resampled. After calibration they cover the truth 95.5% of the time in training regions but only 55.9% in holdouts, so they are not 90% error bounds there. Custom-area bands use 20 draws and are approximate and uncalibrated.</li>
      <li><strong>Coverage matters.</strong> Cloud and smoke can hide fires. A zero means no recorded detections. Known partial months are excluded from anomaly grades.</li>
      <li><strong>Near-real-time values are preliminary.</strong> NOAA-20 values are scaled, and sensor continuity has not yet passed human review. Terra-only estimates (2000-11 to mid-2002) carry lower confidence.</li>
      <li><strong>Area selection is approximate.</strong> Partial cells are allocated by overlap area, assuming detections are spread evenly inside each 0.25° cell.</li>
    </ul>
  </section>

  <section class="m-section" id="reports"><h2>Full reports</h2>
    <div class="m-links">
      <a href="${REPO}/blob/main/reports/validation.md" target="_blank" rel="noopener">${icon("info")}<span><strong>Validation report</strong><small>All figures, checks and their reasoning</small></span>${icon("arrow")}</a>
      <a href="${REPO}/blob/main/reports/final-test.md" target="_blank" rel="noopener">${icon("check")}<span><strong>Final blind-test report</strong><small>Every score from the one-time grader run</small></span>${icon("arrow")}</a>
      <a href="${REPO}/blob/main/docs/preregistration.md" target="_blank" rel="noopener">${icon("clock")}<span><strong>Pre-registration</strong><small>Rules fixed before any model</small></span>${icon("arrow")}</a>
      <a href="${REPO}/blob/main/docs/ai-usage.md" target="_blank" rel="noopener">${icon("spark")}<span><strong>AI usage statement</strong><small>What the AI did and what people did</small></span>${icon("arrow")}</a>
      <a href="/data/v1/data-card.md" download>${icon("download")}<span><strong>Dataset card</strong><small>Methods, interpretation, limitations and citation</small></span>${icon("arrow")}</a>
    </div>
    <p class="small muted">The code and data repository is public; the one-time grading run record stays in the team's private development repository.</p>
  </section>

  <footer><span class="footer-brand">Team Inspiratio <span>NASA Space Apps 2026</span></span><span>NASA FIRMS · MODIS & VIIRS · Dataset CC BY 4.0</span><a class="text-button" href="/">Back to the atlas ${icon("arrow")}</a></footer>
</main><div id="tooltip" role="tooltip" hidden></div>`;

// ---------- shared tooltip for [data-tip] marks ----------
const tip = document.querySelector("#tooltip");
function placeTip(e) {
  tip.style.left = Math.min(window.innerWidth - tip.offsetWidth - 12, Math.max(12, e.clientX + 14)) + "px";
  tip.style.top = Math.min(window.innerHeight - tip.offsetHeight - 12, e.clientY + 16) + "px";
}
function showTip(html, e) {
  tip.innerHTML = html;
  tip.hidden = false;
  placeTip(e);
}
document.addEventListener("pointerover", (e) => {
  const el = e.target.closest?.("[data-tip]");
  if (el) showTip(el.dataset.tip, e);
});
document.addEventListener("pointermove", (e) => {
  if (!tip.hidden && e.target.closest?.("[data-tip], .crosshair")) placeTip(e);
});
document.addEventListener("pointerout", (e) => {
  if (e.target.closest?.("[data-tip]")) tip.hidden = true;
});

// ---------- figure renderers (each draws at its container's width) ----------
const monthsLabel = (m) =>
  new Date(m + "-15T00:00:00Z").toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });

/** Monthly log-scale panel with a hover crosshair. */
function monthlyPanel({ w, h, months, lines, bands = [], shades = [], marks = [], label, tipFor, lo, hi }) {
  const pad = { l: 44, r: 10, t: 14, b: 24 },
    x = linearScale([0, months.length - 1], [pad.l, w - pad.r]),
    ax = yAxisLog({ lo, hi, top: pad.t, bottom: h - pad.b, left: pad.l, right: w - pad.r }),
    at = (m) => months.indexOf(m),
    step = x(1) - x(0);
  let svg = open(w, h, label);
  for (const sh of shades) {
    const a = x(at(sh.from)) - step / 2,
      b = x(at(sh.to)) + step / 2;
    svg += `<rect class="${sh.cls || "shade"}" x="${a}" y="${pad.t}" width="${b - a}" height="${h - pad.t - pad.b}"/>${sh.label && b - a > sh.label.length * 5.5 ? `<text class="shade-label" x="${(a + b) / 2}" y="${pad.t + 12}" text-anchor="middle">${sh.label}</text>` : ""}`;
  }
  svg += ax.svg;
  for (const b of bands)
    svg += `<path d="${band(months.map((m, i) => [x(i), b.lo[i] == null ? null : ax.y(Math.max(lo, b.lo[i])), b.hi[i] == null ? null : ax.y(Math.max(lo, b.hi[i]))]))}" fill="${b.color}" opacity="0.8"/>`;
  for (const mk of marks) {
    const xm = x(at(mk.at)) - step / 2;
    svg += `<line class="rule" x1="${xm}" x2="${xm}" y1="${pad.t - 4}" y2="${h - pad.b}"/>${mk.label ? `<text class="rule-label" x="${xm + 5}" y="${pad.t + 6}">${mk.label}</text>` : ""}`;
  }
  for (const l of lines)
    svg += `<path d="${path(months.map((m, i) => [x(i), l.values[i] == null ? null : ax.y(Math.max(lo, l.values[i]))]))}" fill="none" stroke="${l.color}" stroke-width="${l.width || 1.5}" ${l.dash ? `stroke-dasharray="${l.dash}"` : ""} stroke-linejoin="round"/>`;
  months.forEach((m, i) => {
    if (m.endsWith("-01") && +m.slice(0, 4) % (w < 520 ? 8 : 4) === 0)
      svg += `<text class="tick" x="${x(i)}" y="${h - 7}" text-anchor="middle">${m.slice(0, 4)}</text>`;
  });
  svg += `<line class="crosshair-line" x1="0" x2="0" y1="${pad.t}" y2="${h - pad.b}" visibility="hidden"/><rect class="crosshair" x="${pad.l}" y="0" width="${w - pad.l - pad.r}" height="${h}" fill="transparent"/></svg>`;
  return {
    svg,
    wire(root) {
      const r = root.querySelector(".crosshair"),
        line = root.querySelector(".crosshair-line");
      const move = (e) => {
        const box = r.ownerSVGElement.getBoundingClientRect(),
          px = ((e.clientX - box.left) / box.width) * w,
          i = Math.max(0, Math.min(months.length - 1, Math.round(x.invert(px))));
        line.setAttribute("x1", x(i));
        line.setAttribute("x2", x(i));
        line.setAttribute("visibility", "visible");
        showTip(`<strong>${monthsLabel(months[i])}</strong>${tipFor(i)}`, e);
      };
      r.addEventListener("pointermove", move);
      r.addEventListener("pointerdown", move);
      r.addEventListener("pointerleave", () => {
        line.setAttribute("visibility", "hidden");
        tip.hidden = true;
      });
    },
  };
}
const tipLine = (color, label, v, estimate) =>
  `<small><i class="tip-key" style="background:${color}"></i>${label}: ${v == null ? "—" : estimate ? approx(v) : int(v)}</small>`;
const decades = (vals) => {
  const pos = vals.filter((v) => v > 0);
  return [10 ** Math.floor(Math.log10(Math.min(...pos))), 10 ** Math.ceil(Math.log10(Math.max(...pos)))];
};

const RENDER = {
  "sensor-jump"(el, w) {
    const sa = loaded.southern_africa;
    if (!sa) return;
    const t = sa.totals,
      [lo, hi] = decades([...t.est_m0, ...t.aqua_count].filter((v) => v != null));
    const p = monthlyPanel({
      w,
      h: w < 640 ? 250 : 300,
      months: sa.months,
      lo: Math.max(lo, 10),
      hi,
      label: "Southern Africa monthly detections: direct splice vs Aqua MODIS",
      shades: [{ from: "2012-02", to: "2013-12", label: "S-NPP withheld" }],
      marks: [{ at: "2012-02", label: "sensor switch" }],
      lines: [
        { values: t.aqua_count, color: COLORS.aqua, dash: "4 3", width: 1.5 },
        { values: t.est_m0, color: COLORS.splice, width: 1.75 },
      ],
      tipFor: (i) => tipLine(COLORS.splice, "Direct splice", t.est_m0[i]) + tipLine(COLORS.aqua, "Aqua MODIS", t.aqua_count[i]),
    });
    el.innerHTML = p.svg;
    p.wire(el);
  },
  "test-totals"(el, w) {
    const cols = w >= 960 ? 3 : w >= 620 ? 2 : 1,
      pw = (w - (cols - 1) * 18) / cols;
    el.innerHTML = `<div class="multiples" style="--cols:${cols}">${REGIONS.map((r) => {
      const rows = totalsBy(r),
        short = pw / rows.length < 46;
      return `<div class="panel-fig"><p class="panel-title">${NAMES[r]}${HOLDOUT.has(r) ? " <small>holdout · test 2</small>" : " <small>test 1</small>"}</p><p class="panel-sub">mean |yearly bias|: E028 ${pct(meanBias(r, "E028"))}, M1s ${pct(meanBias(r, "M1s"))}</p>${groupedBars({
        width: pw,
        height: 190,
        label: `${NAMES[r]}: yearly totals, true VIIRS vs E028 vs M1s`,
        groups: rows.map((t) => ({
          label: short ? "’" + String(t.year).slice(2) : String(t.year),
          values: { viirs: t.viirs, E028: t.E028, M1s: t.M1s },
          tips: Object.fromEntries(
            ["viirs", "E028", "M1s"].map((k) => [k, `<strong>${NAMES[r]} ${t.year}</strong>${tipLine(COLORS.viirs, "True VIIRS", t.viirs)}${tipLine(COLORS.harmonized, `E028 (${signedPct(t.E028 / t.viirs - 1)})`, t.E028, true)}${tipLine(COLORS.m1s, `M1s (${signedPct(t.M1s / t.viirs - 1)})`, t.M1s, true)}`]),
          ),
        })),
        keys: [
          { key: "viirs", label: "True VIIRS", color: COLORS.viirs },
          { key: "E028", label: "E028", color: COLORS.harmonized },
          { key: "M1s", label: "M1s", color: COLORS.m1s },
        ],
        pad: { l: 42, r: 6, t: 10, b: 24 },
      })}</div>`;
    }).join("")}</div>`;
  },
  "scores-chart"(el, w) {
    const wide = w >= 760,
      lw = wide ? Math.round(w * 0.58) : w,
      rw = wide ? w - lw - 28 : w;
    const bars = groupedBars({
      width: lw,
      height: 260,
      label: "MALE by evaluation window and method",
      max: 0.9,
      fmt: (v) => v.toFixed(2),
      valueLabels: lw >= 560,
      groups: s.windows.map((wd) => ({
        label: lw >= 560 ? WINDOW[wd][0].replace("Test 1: training regions", "Test 1 · training").replace("Test 2: holdout regions", "Test 2 · holdout") : { main: "Valid.", aux: "Valid.", test1: "Test 1", test2: "Test 2" }[wd],
        sublabel: WINDOW[wd][1],
        values: { E028: s.male.E028[wd], M1s: s.male.M1s[wd], QM: s.male.QM[wd] },
      })),
      keys: [
        { key: "E028", label: "E028", color: COLORS.harmonized },
        { key: "M1s", label: "M1s", color: COLORS.m1s },
        { key: "QM", label: "QM", color: COLORS.qm },
      ],
      pad: { l: 40, r: 6, t: 18, b: 40 },
    });
    // Dot-and-whisker: E028's advantage (positive = E028 better).
    const rows = [
      ["validation_combined", "Validation"],
      ["test1", "Test 1"],
      ["test2", "Test 2"],
    ];
    const H = 260,
      pad = { l: 78, r: 14, t: 18, b: 40 },
      x = linearScale([0, 0.3], [pad.l, rw - pad.r]),
      rowH = (H - pad.t - pad.b) / rows.length;
    let dw = open(rw, H, "Difference in MALE, E028 better than baselines, with 95% intervals");
    for (let v = 0; v <= 0.3001; v += 0.1)
      dw += `<line class="grid" x1="${x(v)}" x2="${x(v)}" y1="${pad.t}" y2="${H - pad.b}"/><text class="tick" x="${x(v)}" y="${H - pad.b + 16}" text-anchor="middle">${v.toFixed(1)}</text>`;
    dw += `<text class="tick" x="${(pad.l + rw - pad.r) / 2}" y="${H - 6}" text-anchor="middle">MALE difference (baseline − E028)</text>`;
    rows.forEach(([k, l], i) => {
      const cy = pad.t + rowH * (i + 0.5);
      dw += `<text class="tick" x="${pad.l - 10}" y="${cy + 4}" text-anchor="end">${l}</text>`;
      [["M1s", COLORS.m1s, -9], ["QM", COLORS.qm, 9]].forEach(([b, c, off]) => {
        const d = s.diff[k][b],
          y = cy + off;
        dw += `<g ${tipAttr(`<strong>${l}: E028 vs ${b}</strong><span>E028's MALE is ${d.diff.toFixed(3)} lower</span><small>95% interval ${d.lo.toFixed(3)} to ${d.hi.toFixed(3)}</small>`)}><line x1="${x(d.lo)}" x2="${x(d.hi)}" y1="${y}" y2="${y}" stroke="${c}" stroke-width="2"/><line x1="${x(d.lo)}" x2="${x(d.lo)}" y1="${y - 4}" y2="${y + 4}" stroke="${c}" stroke-width="2"/><line x1="${x(d.hi)}" x2="${x(d.hi)}" y1="${y - 4}" y2="${y + 4}" stroke="${c}" stroke-width="2"/><circle cx="${x(d.diff)}" cy="${y}" r="5" fill="${c}" stroke="#fffefa" stroke-width="2"/><rect x="${x(d.lo) - 6}" y="${y - 8}" width="${x(d.hi) - x(d.lo) + 12}" height="16" fill="transparent"/></g>`;
      });
    });
    dw += `<line class="axis" x1="${x(0)}" x2="${x(0)}" y1="${pad.t}" y2="${H - pad.b}"/></svg>`;
    el.innerHTML = `<div class="split ${wide ? "wide" : ""}"><div><p class="panel-title">Primary score in every window <small>MALE, lower is better</small></p>${bars}</div><div><p class="panel-title">How much better E028 is <small>vs M1s (purple) and QM (grey)</small></p>${dw}</div></div>`;
  },
  explain(el, w) {
    const wide = w >= 760,
      lw = wide ? Math.round(w * 0.42) : w,
      rw = wide ? w - lw - 28 : w;
    const g = data.explain.gain_count,
      bh = 22,
      padL = 132,
      H1 = g.length * bh + 30,
      x1 = linearScale([0, 70], [padL, lw - 36]);
    let bars = open(lw, H1, "Share of total gain in the count stage, top inputs");
    g.forEach((d, i) => {
      const y = 6 + i * bh;
      bars += `<text class="tick" x="${padL - 8}" y="${y + 13}" text-anchor="end">${d.feature}</text><path class="bar" fill="${COLORS.harmonized}" d="M${padL},${y + 3}H${x1(d.share) - Math.min(4, x1(d.share) - padL)}Q${x1(d.share)},${y + 3} ${x1(d.share)},${y + 7}V${y + 13}Q${x1(d.share)},${y + 17} ${x1(d.share) - Math.min(4, x1(d.share) - padL)},${y + 17}H${padL}Z" ${tipAttr(`<strong>${d.feature}</strong><span>${d.share}% of the count stage's gain</span>`)}/><text class="value" x="${x1(d.share) + 5}" y="${y + 14}">${d.share.toFixed(1)}%</text>`;
    });
    bars += `<line class="axis" x1="${padL}" x2="${padL}" y1="2" y2="${H1 - 22}"/></svg>`;
    const dc = data.explain.deciles_aqua_count,
      H2 = Math.max(H1, 240),
      pad = { l: 44, r: 12, t: 12, b: 38 },
      lx = (v) => Math.log10(v),
      x = linearScale([lx(1), lx(120)], [pad.l, rw - pad.r]),
      ax = yAxisLinear({ max: 8.5, min: 4, top: pad.t, bottom: H2 - pad.b, left: pad.l, right: rw - pad.r, fmt: (v) => v.toFixed(0) });
    let curve = open(rw, H2, "VIIRS-scale detections per Aqua detection by decile of Aqua detections") + ax.svg;
    for (const v of [1, 3, 10, 30, 100])
      curve += `<text class="tick" x="${x(lx(v))}" y="${H2 - pad.b + 16}" text-anchor="middle">${v}</text>`;
    curve += `<text class="tick" x="${(pad.l + rw - pad.r) / 2}" y="${H2 - 5}" text-anchor="middle">Aqua detections in the cell-month (log)</text>`;
    curve += `<path d="${path(dc.x.map((v, i) => [x(lx(v)), ax.y(dc.model[i])]))}" fill="none" stroke="${COLORS.harmonized}" stroke-width="2"/>`;
    dc.x.forEach((v, i) => {
      const tipHtml = `<strong>Decile ${i + 1}: ~${v.toFixed(1)} Aqua detections</strong>${tipLine(COLORS.viirs, "Observed VIIRS per Aqua", null).replace("—", dc.observed[i].toFixed(2))}${tipLine(COLORS.harmonized, "Model per Aqua", null).replace("—", dc.model[i].toFixed(2))}`;
      curve += `<circle cx="${x(lx(v))}" cy="${ax.y(dc.model[i])}" r="3.5" fill="${COLORS.harmonized}"/><rect x="${x(lx(v)) - 6}" y="${ax.y(dc.observed[i]) - 6}" width="12" height="12" rx="1.5" fill="transparent" stroke="${COLORS.viirs}" stroke-width="1.75" ${tipAttr(tipHtml)}/>`;
    });
    curve += "</svg>";
    el.innerHTML = `<div class="split ${wide ? "wide" : ""}"><div><p class="panel-title">Inputs the count stage relies on <small>share of total gain</small></p>${bars}</div><div><p class="panel-title">VIIRS detections per Aqua detection <small>by decile, training rows 2014–21</small></p>${curve}</div></div>`;
  },
  series(el, w) {
    const rows = loaded.totals;
    if (!rows) return;
    const cols = w >= 900 ? 2 : 1,
      pw = (w - (cols - 1) * 22) / cols;
    const parts = REGIONS.map((r) => {
      const d = rows[r],
        model = d.source.map((s) => s.startsWith("model_")),
        obsIdx = d.source.findIndex((s) => !s.startsWith("model_")),
        est = d.est.map((v, i) => (model[i] || i === obsIdx - 1 ? v : null)),
        obs = d.est.map((v, i) => (!model[i] ? v : null)),
        modis = d.est_m0.map((v, i) => (d.months[i] < "2012-02" ? v : null)),
        terraRuns = [];
      d.source.forEach((src, i) => {
        if (src !== "model_terra_bridge") return;
        const last = terraRuns.at(-1);
        if (last && last.end === i - 1) last.end = i;
        else terraRuns.push({ start: i, end: i });
      });
      if (obsIdx > 0) obs[obsIdx - 1] = d.est[obsIdx - 1];
      const [lo, hi] = decades(d.est);
      const p = monthlyPanel({
        w: pw,
        h: 170,
        months: d.months,
        lo: Math.max(1, Math.min(lo, 10)),
        hi,
        label: `${NAMES[r]}: harmonized monthly history`,
        shades: terraRuns.map((run) => ({ from: d.months[run.start], to: d.months[run.end], cls: "shade terra" })),
        marks: [{ at: "2012-02" }],
        bands: [{ lo: d.lo.map((v, i) => (model[i] ? v : null)), hi: d.hi.map((v, i) => (model[i] ? v : null)), color: COLORS.band }],
        lines: [
          { values: modis, color: COLORS.aqua, dash: "3 3", width: 1.2 },
          { values: est, color: COLORS.harmonized, width: 1.4 },
          { values: obs, color: COLORS.viirs, width: 1.4 },
        ],
        tipFor: (i) =>
          `${tipLine(model[i] ? COLORS.harmonized : COLORS.viirs, model[i] ? "Model estimate" : "Observed VIIRS", d.est[i], model[i])}${model[i] ? `<small>Stability band ${approx(d.lo[i])} to ${approx(d.hi[i])}</small>` : ""}${modis[i] != null ? tipLine(COLORS.aqua, "MODIS as recorded", modis[i]) : ""}`,
      });
      return { r, p };
    });
    el.innerHTML = `<div class="multiples" style="--cols:${cols}">${parts.map(({ r, p }) => `<div class="panel-fig" data-region="${r}"><p class="panel-title">${NAMES[r]}${HOLDOUT.has(r) ? " <small>holdout: model estimate every month</small>" : ""}</p>${p.svg}</div>`).join("")}</div>`;
    parts.forEach(({ r, p }) => p.wire(el.querySelector(`[data-region="${r}"]`)));
  },
  gfed(el, w) {
    const cols = w >= 900 ? 3 : 1,
      pw = (w - (cols - 1) * 18) / cols;
    el.innerHTML = `<div class="multiples" style="--cols:${cols}">${Object.entries(data.gfed)
      .map(([r, rows]) => {
        const H = 220,
          pad = { l: 40, r: 10, t: 12, b: 26 },
          x = linearScale([2003, 2016], [pad.l + 6, pw - pad.r - 6]),
          ax = yAxisLinear({ max: Math.max(...rows.map((d) => Math.max(d.harmonized, d.splice ?? 0))), top: pad.t, bottom: H - pad.b, left: pad.l, right: pw - pad.r, fmt: (v) => v.toFixed(0) });
        let svg = open(pw, H, `${NAMES[r]}: detections per burned km²`);
        svg += `<rect class="shade" x="${x(2011.5)}" y="${pad.t}" width="${x(2013.5) - x(2011.5)}" height="${H - pad.t - pad.b}"/>` + ax.svg;
        svg += `<line class="rule" x1="${x(2011.5)}" x2="${x(2011.5)}" y1="${pad.t}" y2="${H - pad.b}"/>`;
        svg += `<path d="${path(rows.map((d) => [x(d.year), d.splice == null ? null : ax.y(d.splice)]))}" fill="none" stroke="${COLORS.splice}" stroke-width="1.75" stroke-dasharray="4 3"/>`;
        svg += `<path d="${path(rows.map((d) => [x(d.year), ax.y(d.harmonized)]))}" fill="none" stroke="${COLORS.harmonized}" stroke-width="2"/>`;
        rows.forEach((d) => {
          const obs = d.source === "snpp",
            t = `<strong>${NAMES[r]} ${d.year}</strong>${tipLine(obs ? COLORS.viirs : COLORS.harmonized, obs ? "Observed S-NPP per km²" : "Harmonized per km²", null).replace("—", d.harmonized.toFixed(2))}${tipLine(COLORS.splice, "Direct splice per km²", null).replace("—", d.splice == null ? "withheld" : d.splice.toFixed(2))}`;
          if (d.splice != null && !obs) svg += `<circle cx="${x(d.year)}" cy="${ax.y(d.splice)}" r="3" fill="${COLORS.splice}" ${tipAttr(t)}/>`;
          svg += `<circle cx="${x(d.year)}" cy="${ax.y(d.harmonized)}" r="${obs ? 4.5 : 3.5}" fill="${obs ? COLORS.viirs : COLORS.harmonized}" stroke="#fffefa" stroke-width="1.5" ${tipAttr(t)}/>`;
        });
        for (const yr of [2004, 2008, 2012, 2016]) svg += `<text class="tick" x="${x(yr)}" y="${H - 8}" text-anchor="middle">${yr}</text>`;
        return `<div class="panel-fig"><p class="panel-title">${NAMES[r]}</p>${svg}</svg></div>`;
      })
      .join("")}</div>`;
  },
  "era-shift"(el, w) {
    el.innerHTML = groupedBars({
      width: w,
      height: 250,
      min: 0.4,
      max: 0.85,
      fmt: (v) => v.toFixed(2),
      label: "Classifier AUC per region: era question vs control",
      ref: { value: 0.5, label: "" },
      groups: REGIONS.map((r) => {
        const g = HOLDOUT.has(r) ? data.drift.holdout : data.drift.train;
        const short = { california: "Calif.", cordoba: "Córdoba", southern_africa: "S. Africa", north_australia: "N. Aust.", central_siberia: "C. Sib.", indo_gangetic: "Indo-Gang." };
        return { label: w < 640 ? short[r] : NAMES[r], sublabel: HOLDOUT.has(r) ? "holdout" : "", values: { q: g.by_region[r], c: g.control[r] } };
      }),
      keys: [
        { key: "q", label: "2002–11 vs 2014–21", color: COLORS.harmonized },
        { key: "c", label: "2002–11 vs 2022–26 (control)", color: COLORS.qm },
      ],
      pad: { l: 40, r: 8, t: 14, b: 40 },
    });
  },
};

// Region data for figures 1 and 5 (published v1 assets, same as the atlas).
const loaded = {};
const widths = new Map();
function draw(id, force) {
  const el = document.querySelector(`[data-fig="${id}"]`),
    w = Math.floor(el.clientWidth);
  if (!w || (!force && widths.get(id) === w)) return;
  widths.set(id, w);
  try {
    RENDER[id](el, w);
  } catch (e) {
    console.error(e);
    el.innerHTML = `<p class="fig-loading">This figure could not be drawn. The original is linked below.</p>`;
  }
}
const ro = new ResizeObserver((entries) => entries.forEach((en) => draw(en.target.dataset.fig)));
document.querySelectorAll("[data-fig]").forEach((el) => ro.observe(el));

gzipBytes("/data/v1/southern_africa.json.gz")
  .then((b) => {
    loaded.southern_africa = JSON.parse(new TextDecoder().decode(b));
    draw("sensor-jump", true);
  })
  .catch(() => {
    document.querySelector('[data-fig="sensor-jump"]').innerHTML = '<p class="fig-loading">Published data could not be loaded. The original figure is linked below.</p>';
  });
fetch("/data/v1/region_totals_v1.csv")
  .then((r) => {
    if (!r.ok) throw Error(r.status);
    return r.text();
  })
  .then((text) => {
    const [head, ...lines] = text.trim().split(/\r?\n/),
      cols = head.split(","),
      ix = Object.fromEntries(cols.map((c, i) => [c, i])),
      num = (v) => (v === "" ? null : +v),
      out = {};
    for (const line of lines) {
      const c = line.split(","),
        r = (out[c[ix.region]] ||= { months: [], est: [], est_m0: [], lo: [], hi: [], source: [] });
      r.months.push(c[ix.month]);
      r.est.push(num(c[ix.est]));
      r.est_m0.push(num(c[ix.est_m0]));
      r.lo.push(num(c[ix.lo_90]));
      r.hi.push(num(c[ix.hi_90]));
      r.source.push(c[ix.source]);
    }
    loaded.totals = out;
    draw("series", true);
  })
  .catch(() => {
    document.querySelector('[data-fig="series"]').innerHTML = '<p class="fig-loading">Published data could not be loaded. The original figure is linked below.</p>';
  });

// Deep links: the content is drawn by script, so scroll once it exists.
if (location.hash) requestAnimationFrame(() => document.querySelector(location.hash)?.scrollIntoView());
