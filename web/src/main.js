import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import { feature as topoFeature } from "topojson-client";
import land from "world-atlas/land-110m.json";
import { area } from "@turf/area";
import { polygon } from "@turf/helpers";
import { anomaly, quantile } from "./anomaly.js";
import { logPercentileScale, rampGradient } from "./scale.js";
import { annualTotals, spliceGapReason, spliceSource } from "./series.js";
import { approx, count, ordinal, roundEstimate } from "./format.js";
import { REPO, icon, siteHeader, gzipBytes } from "./ui.js";
import { createCellLayer, cellAt, cellIndex } from "./cell-layer.js";
import {
  cellPolygon,
  selectionWeights,
  aggregateSelection,
  aggregateIntervals,
} from "./aggregate.js";
import "./style.css";

window.L = L;
await import("leaflet-draw");

const names = {
  california: ["California", "United States", "Mediterranean woodland"],
  cordoba: ["Córdoba", "Argentina", "Grassland & cropland"],
  southern_africa: [
    "Southern Africa",
    "Zambia & neighbouring regions",
    "Miombo savanna",
  ],
  north_australia: ["Northern Australia", "Australia", "Tropical savanna"],
  central_siberia: ["Central Siberia", "Russia", "Boreal forest"],
  indo_gangetic: ["Indo-Gangetic Plain", "South Asia", "Cropland"],
};
const sources = {
  snpp: ["VIIRS observation", "Observed"],
  model_aqua: ["MODIS-based estimate", "Estimated"],
  model_terra_bridge: ["Terra-bridged estimate", "Low confidence"],
  noaa20_scaled: ["NOAA-20 scaled observation", "Scaled"],
};
const monthsShort = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
const palette = [
  "#eeeedb",
  "#dce4a9",
  "#b8d677",
  "#7fbe67",
  "#4c9e72",
  "#2b7f78",
  "#286272",
  "#29495e",
  "#28394d",
];
const fmt = (n, d = 0) =>
  n == null || !Number.isFinite(n)
    ? "—"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: d }).format(n);
const compact = (n) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("en-US", {
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(n);
const fullMonth = (m) =>
  new Date(m + "-15T00:00:00Z").toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const state = {
  data: null,
  region: "california",
  series: [],
  totals: null,
  selected: "2026-10",
  baseline: "all",
  mode: "est",
  start: 2001,
  end: 2026,
  weights: null,
  selection: null,
  busy: false,
  epoch: 0,
  asOf: new Date().toISOString().slice(0, 10),
  timings: {},
};
const cache = new Map(),
  binaryCache = new Map();
let map, gridLayer, outline, selectionLayer, drawHandler;

document.querySelector("#app").innerHTML = `
  ${siteHeader("atlas")}
  <main id="explore"><section class="intro"><div><p class="eyebrow">A LONGER VIEW OF FIRE ACTIVITY</p><h1>Different satellites. One shared history.</h1><p class="intro-copy">Explore 26 years of fire detections, brought onto a comparable VIIRS scale.</p></div>
    <div class="intro-tools"><span class="dataset-badge"><span class="status-dot"></span>Dataset v1 <span>2000–2026</span></span><button class="button primary" id="download-csv">${icon("download")} Download data</button></div></section>
  <section class="workspace" aria-label="Region exploration">
    <aside class="region-sidebar"><div class="sidebar-heading"><span class="step">01</span><h2>Choose a region</h2></div><p class="small muted">Six regions. Different fire landscapes.</p><div class="region-list">${Object.entries(
      names,
    )
      .map(
        ([id, n], i) =>
          `<button class="region-button ${i === 0 ? "selected" : ""}" data-region="${id}" aria-pressed="${i === 0}"><span class="region-dot r${i}"></span><span><strong>${n[0]}</strong><small>${n[1]}</small></span>${icon("chevron")}</button>`,
      )
      .join("")}</div>
      <div class="sidebar-bottom"><span class="tiny-label">YOUR OWN AREA</span><p class="small muted">Draw inside the selected region.</p><div class="draw-buttons"><button class="button" id="draw-box">${icon("box")} Box</button><button class="button" id="draw-polygon">${icon("polygon")} Polygon</button></div>
      <details class="coordinates"><summary>Enter coordinates</summary><form id="coordinate-form"><div class="coord-grid">${["West", "South", "East", "North"].map((n) => `<label>${n}<input name="${n.toLowerCase()}" type="number" step="0.01" required aria-label="${n} longitude or latitude"/></label>`).join("")}</div><button class="button" type="submit">Apply bounds</button></form></details>
      <button class="text-button reset-selection" id="reset-selection" hidden>${icon("reset")} Reset to full region</button></div>
      <p class="sidebar-foot">0.25° grid · Monthly · UTC<br/>Satellite detections, not individual fires.</p></aside>
    <div class="map-panel panel"><div class="panel-heading"><div><p class="tiny-label" id="map-country">UNITED STATES</p><h2 id="region-title">California</h2><span class="small muted" id="ecosystem">Mediterranean woodland</span></div><span class="source-pill" id="region-role">Training region</span></div>
      <div class="map-wrap"><div id="map" aria-label="Interactive map of fire activity" role="region"></div><div class="map-month">${icon("clock")} <span id="map-month">October 2026</span></div><button class="map-fit" id="map-fit" aria-label="Fit map to selected region">${icon("map")}</button><div class="map-legend"><span>Fewer detections</span><span class="color-ramp"></span><span>More</span></div></div>
      <div class="map-footer"><span id="map-status" role="status" aria-live="polite">Loading published data…</span><span id="cell-count"></span></div></div>
    <aside class="insight-column"><div class="insight-card panel"><div class="insight-heading"><span class="step">02</span><span class="tiny-label">MONTH IN FOCUS</span></div><p class="focus-month" id="focus-month">October 2026</p><div class="big-value" id="focus-value">—</div><p class="metric-caption" id="focus-caption">VIIRS-equivalent detections</p><div id="activity-level" class="activity-level">Loading…</div><p class="insight-copy" id="anomaly-description">Comparing with previous years of the same calendar month.</p>
      <div class="percentile-track" aria-hidden="true"><span id="percentile-marker"></span></div><div class="percentile-labels" aria-hidden="true"><span>Below normal<br/>≤ 10th</span><span>Normal</span><span>Above normal<br/>≥ 90th</span></div>
      <dl class="insight-stats"><div class="primary-stat"><dt>Percentile rank</dt><dd id="percentile-rank">—</dd></div><div><dt>Historical median</dt><dd id="historical-median">—</dd></div><div><dt>Ratio to median <small>(context only)</small></dt><dd id="median-ratio">—</dd></div><div><dt>Reference years</dt><dd id="reference-years">—</dd></div></dl>
      <label class="baseline-label" for="baseline">Compare against</label><select id="baseline"><option value="all">Available history since 2001</option><option value="snpp">S-NPP observations only</option></select><div class="quality-note" id="quality-note"></div></div>
      <a class="method-teaser" href="/methods.html#sensor-jump"><span class="round-icon">${icon("spark")}</span><span><strong>Why harmonize?</strong><small>A new sensor should not rewrite history.</small></span>${icon("arrow")}</a></aside>
  </section>
  <div class="selection-note" id="selection-note" hidden></div><div class="error-banner" id="error" role="alert" hidden></div>
  <section class="calendar-panel panel"><div class="section-heading"><div><p class="eyebrow">THE LONG VIEW</p><h2>A calendar of fire activity</h2><p class="small muted">Every square is one month. Select a month to explore it on the map.</p></div><div class="calendar-controls"><div class="segmented" role="group" aria-label="Calendar data"><button class="active" data-mode="est" aria-pressed="true">Harmonized</button><button data-mode="est_m0" aria-pressed="false">Direct splice</button></div><button class="icon-button" id="download-image" aria-label="Download calendar as PNG">${icon("download")}</button></div></div>
    <div class="calendar-subheading"><span id="calendar-region">California</span><div class="year-range"><label for="start-year">From</label><select id="start-year" aria-label="First calendar year"></select><label for="end-year">to</label><select id="end-year" aria-label="Last calendar year"></select></div><span class="calendar-scale" id="calendar-scale"><i class="zero-swatch" aria-hidden="true"></i><span>0</span><span id="scale-lo" class="scale-tick">—</span><span class="color-ramp calendar-ramp" style="background:${rampGradient()}"></span><span id="scale-hi" class="scale-tick">—</span><span class="scale-note">log scale · 5th–99th percentile of this area</span></span></div>
    <p class="calendar-note" id="calendar-note" hidden></p>
    <div class="calendar-scroll"><div id="calendar" class="calendar" aria-label="Monthly fire activity calendar"></div></div>
    <div class="calendar-bottom"><span class="calendar-legend"><span><i class="swatch observed"></i>Observation</span><span><i class="swatch estimated"></i>Model estimate (striped)</span><span><i class="swatch estimated low-confidence"></i>Low-confidence estimate</span><span><i class="swatch missing"></i>No data</span></span><span>• = preliminary / incomplete month</span></div>
  </section>
  <section class="trend-panel panel"><div class="section-heading"><div><p class="eyebrow">SAME PLACE, DIFFERENT SENSORS</p><h2>The history behind the calendar</h2><p class="small muted">Annual totals for the selected area. The switch above changes both the calendar and this chart. Click a year to highlight it.</p></div><div class="segmented" role="group" aria-label="Chart emphasis"><button class="active" data-mode="est" aria-pressed="true">Harmonized</button><button data-mode="est_m0" aria-pressed="false">Direct splice</button></div></div>
    <div class="chart-key" id="trend-key"><span><i class="key-line harmonized"></i>Harmonized (VIIRS scale)</span><span><i class="key-line splice"></i>Direct splice: MODIS until 2012-01, S-NPP after</span><span><i class="key-line aqua"></i>Aqua MODIS as recorded</span><span><i class="key-dot snpp"></i>S-NPP VIIRS observed</span></div>
    <div id="trend" class="trend-chart"></div><p class="chart-foot" id="trend-foot"></p></section>
  <section class="trust-strip"><div>${icon("check")}<span><strong>Tested, with limits</strong><small>22% lower test error than the ratio baseline in training regions.</small></span></div><div>${icon("info")}<span><strong>Sources stay visible</strong><small>Observations, estimates and incomplete months are marked.</small></span></div><a class="text-button" href="/methods.html#limits">Read the method & limitations ${icon("arrow")}</a></section>
  <footer><span class="footer-brand">Team Inspiratio <span>NASA Space Apps 2026</span></span><span>NASA FIRMS · MODIS & VIIRS · Dataset CC BY 4.0</span><button class="text-button" data-downloads>Data, attribution & downloads ${icon("arrow")}</button></footer>
  </main><div id="tooltip" role="tooltip" hidden></div>
  <dialog id="downloads-dialog"><button class="dialog-close icon-button" aria-label="Close data downloads">${icon("close")}</button><p class="eyebrow">OPEN METHODS, TRACEABLE DATA</p><h2>Take the data with you.</h2><p class="dialog-lead">Dataset v1 · 0.25° cells · 312 UTC months · Six study regions.</p><div class="download-list"><button id="modal-csv">${icon("download")}<span><strong>Selected monthly series</strong><small>CSV · values, stability bands, sources and coverage</small></span>${icon("arrow")}</button><button id="modal-png">${icon("download")}<span><strong>Calendar image</strong><small>PNG · current region and year range</small></span>${icon("arrow")}</button><a href="/data/v1/data-card.md" download>${icon("info")}<span><strong>Dataset card</strong><small>Methods, interpretation, limitations and citation</small></span>${icon("arrow")}</a><a href="${REPO}/releases/tag/v1" target="_blank" rel="noopener">${icon("download")}<span><strong>Full scientific dataset</strong><small>Parquet & CSV · public GitHub release</small></span>${icon("arrow")}</a></div><p class="small muted">Point-level fire records are not included in this release's web assets. Monthly CSV downloads contain gridded counts and estimates, not raw point records.</p><h3>Attribution</h3><p class="small">Team Inspiratio, <em>Harmonized MODIS × VIIRS monthly fire counts</em>, v1 (2026). Dataset: CC BY 4.0. Source observations: NASA Earthdata FIRMS, MODIS and VIIRS. Map tiles: © OpenStreetMap contributors; fallback land geometry: Natural Earth.</p><a href="/data/v1/data-interface.md" download>Download the data interface specification ${icon("arrow")}</a></dialog>`;

const $ = (s) => document.querySelector(s);
for (const y of Array.from({ length: 27 }, (_, i) => 2000 + i))
  for (const id of ["#start-year", "#end-year"]) $(id).add(new Option(y, y));
$("#start-year").value = state.start;
$("#end-year").value = state.end;
document
  .querySelectorAll("[data-downloads]")
  .forEach((b) => (b.onclick = () => $("#downloads-dialog").showModal()));
document
  .querySelectorAll(".dialog-close")
  .forEach((b) => (b.onclick = () => b.closest("dialog").close()));
document.querySelectorAll("dialog").forEach(
  (d) =>
    (d.onclick = (e) => {
      if (
        e.target === d &&
        (e.clientX < d.getBoundingClientRect().left ||
          e.clientX > d.getBoundingClientRect().right ||
          e.clientY < d.getBoundingClientRect().top ||
          e.clientY > d.getBoundingClientRect().bottom)
      )
        d.close();
    }),
);
document
  .querySelectorAll("[data-region]")
  .forEach((b) => (b.onclick = () => loadRegion(b.dataset.region)));
// One switch state drives the calendar and the annual chart (both toggles stay in sync).
function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll("[data-mode]").forEach((x) => {
    const on = x.dataset.mode === mode;
    x.classList.toggle("active", on);
    x.setAttribute("aria-pressed", String(on));
  });
  renderCalendar();
  renderTrend();
}
document
  .querySelectorAll("[data-mode]")
  .forEach((b) => (b.onclick = () => setMode(b.dataset.mode)));
$("#baseline").onchange = (e) => {
  state.baseline = e.target.value;
  renderInsight();
  renderCalendar();
};
for (const id of ["#start-year", "#end-year"])
  $(id).onchange = () => {
    state.start = +$("#start-year").value;
    state.end = +$("#end-year").value;
    if (state.start > state.end) {
      state.end = state.start;
      $("#end-year").value = state.end;
    }
    renderCalendar();
    renderTrend();
  };

map = L.map("map", {
  zoomControl: false,
  preferCanvas: true,
  minZoom: 2,
  maxZoom: 11,
  attributionControl: true,
}).setView([37, -119], 5);
map.attributionControl.setPrefix(false);
L.control.zoom({ position: "bottomright" }).addTo(map);
L.geoJSON(topoFeature(land, land.objects.land), {
  interactive: false,
  style: {
    color: "#c8cfc4",
    weight: 0.5,
    fillColor: "#e7e9df",
    fillOpacity: 1,
  },
}).addTo(map);
const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution:
    '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · Natural Earth',
  maxZoom: 19,
});
tiles.addTo(map);
gridLayer = createCellLayer(L).addTo(map);
// One hover handler for the whole grid (replaces ~1,600 per-cell tooltips).
function cellTip(e) {
  const d = state.data;
  if (!d?._geo || state.busy) return hideTooltip();
  const k = cellAt(e.latlng.lat, e.latlng.lng, d._geo.index, d.cell_deg),
    t = d.months.indexOf(state.selected),
    v = k < 0 ? null : d.est[k][t];
  if (!(v > 0)) return hideTooltip();
  $("#tooltip").innerHTML =
    `<strong>${fullMonth(state.selected)}</strong><span>${count(v, approximate(t))} equivalent detections</span><small>0.25° cell</small>`;
  $("#tooltip").hidden = false;
  moveTooltip(e.originalEvent);
}
map.on("mousemove click", cellTip);
map.on("mouseout movestart zoomstart", hideTooltip);
selectionLayer = L.featureGroup().addTo(map);
const fit = () => {
  if (state.data) {
    const [w, s, e, n] = state.data.bbox;
    map.fitBounds(
      [
        [s, w],
        [n, e],
      ],
      { padding: [16, 16], animate: false },
    );
  }
};
new ResizeObserver(() => {
  map.invalidateSize({ pan: false });
  fit();
}).observe($("#map"));
$("#map-fit").onclick = fit;
const draw = (type) => {
  drawHandler?.disable();
  drawHandler =
    type === "box"
      ? new L.Draw.Rectangle(map, {
          showArea: false,
          shapeOptions: { color: "#e3a35a", weight: 2, fillOpacity: 0.12 },
        })
      : new L.Draw.Polygon(map, {
          showArea: false,
          allowIntersection: false,
          shapeOptions: { color: "#e3a35a", weight: 2, fillOpacity: 0.12 },
        });
  drawHandler.enable();
};
$("#draw-box").onclick = () => draw("box");
$("#draw-polygon").onclick = () => draw("polygon");
map.on(L.Draw.Event.CREATED, (e) => applySelection(e.layer.toGeoJSON()));
$("#reset-selection").onclick = () => resetSelection();
$("#coordinate-form").onsubmit = (e) => {
  e.preventDefault();
  const f = new FormData(e.target),
    w = +f.get("west"),
    s = +f.get("south"),
    east = +f.get("east"),
    n = +f.get("north");
  if (!(w < east && s < n))
    return showError("Bounds must have West < East and South < North.");
  applySelection(
    polygon([
      [
        [w, s],
        [east, s],
        [east, n],
        [w, n],
        [w, s],
      ],
    ]),
  );
};

function showError(message) {
  $("#error").hidden = !message;
  $("#error").textContent = message;
}
function status(message) {
  $("#map-status").textContent = message;
}
async function loadRegion(id) {
  const epoch = ++state.epoch,
    started = performance.now();
  state.busy = true;
  state.timings = {};
  showError("");
  status("Loading verified v1 data…");
  try {
    if (!cache.has(id)) {
      const t0 = performance.now(),
        bytes = await gzipBytes(`/data/v1/${id}.json.gz`),
        t1 = performance.now();
      cache.set(id, JSON.parse(new TextDecoder().decode(bytes)));
      state.timings.download = Math.round(t1 - t0);
      state.timings.parse = Math.round(performance.now() - t1);
    }
    if (epoch !== state.epoch) return;
    const d = cache.get(id);
    if (
      d.version !== "v1" ||
      d.months.length !== 312 ||
      d.cells.lat_idx.length !== d.est.length
    )
      throw Error("Unexpected region data format.");
    state.region = id;
    state.data = d;
    state.totals = d.totals;
    state.weights = null;
    state.selection = null;
    state.series = d.months.map((month, t) => ({
      month,
      value: d.totals.est[t],
      source: d.month_source[t],
      nrt: d.month_nrt[t],
      input_complete: d.month_input_complete[t],
    }));
    if (!d.months.includes(state.selected)) state.selected = d.months.at(-1);
    const [name, country, eco] = names[id];
    $("#region-title").textContent = name;
    $("#map-country").textContent = country.toUpperCase();
    $("#ecosystem").textContent = eco;
    $("#region-role").textContent =
      d.role === "holdout" ? "Holdout · lower confidence" : "Training region";
    $("#region-role").classList.toggle("holdout", d.role === "holdout");
    $("#cell-count").textContent = fmt(d.cells.lat_idx.length) + " cells";
    $("#calendar-region").textContent = name;
    document.querySelectorAll("[data-region]").forEach((b) => {
      const on = b.dataset.region === id;
      b.classList.toggle("selected", on);
      b.setAttribute("aria-pressed", String(on));
    });
    const [w, s, e, n] = d.bbox;
    for (const [k, v] of Object.entries({
      west: w,
      south: s,
      east: e,
      north: n,
    }))
      $(`[name=${k}]`).value = v;
    selectionLayer.clearLayers();
    $("#selection-note").hidden = true;
    $("#reset-selection").hidden = true;
    if (outline) outline.remove();
    outline = L.rectangle(
      [
        [s, w],
        [n, e],
      ],
      {
        color: "#446d55",
        weight: 1.5,
        fill: false,
        dashArray: "5 4",
        interactive: false,
      },
    ).addTo(map);
    timed("fit", fit);
    state.busy = false;
    render();
    state.timings.total = Math.round(performance.now() - started);
    console.debug("[fire-atlas] region switch (ms)", id, { ...state.timings });
    status("Published v1 · full study region");
  } catch (e) {
    console.error(e);
    if (epoch === state.epoch) {
      showError(e.message);
      status("Data unavailable · retry by choosing a region");
      state.busy = false;
    }
  }
}

async function binary(kind) {
  const key = state.region + "." + kind;
  if (!binaryCache.has(key)) {
    const bytes = await gzipBytes(`/data/v1/${key}.f32.gz`);
    binaryCache.set(
      key,
      new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 4),
    );
    if (binaryCache.size > 4)
      binaryCache.delete(binaryCache.keys().next().value);
  }
  return binaryCache.get(key);
}

async function applySelection(shape) {
  if (state.busy || !state.data) return;
  showError("");
  const d = state.data,
    [w, s, e, n] = d.bbox,
    points = shape.geometry.coordinates.flat();
  if (
    points.some(
      (p) =>
        p[0] < w - 1e-8 ||
        p[0] > e + 1e-8 ||
        p[1] < s - 1e-8 ||
        p[1] > n + 1e-8,
    )
  )
    return showError(
      "Draw entirely inside the selected study region. Switch regions to explore another area.",
    );
  const epoch = ++state.epoch;
  state.busy = true;
  status("Summing intersecting cells and loading resampling draws…");
  try {
    const weights = selectionWeights(d, shape);
    if (!weights.length)
      throw Error("The selection does not intersect any data cells.");
    const [raw, draws] = await Promise.all([binary("raw"), binary("draws")]);
    if (epoch !== state.epoch) return;
    const series = aggregateSelection(d, weights),
      totals = {
        est: series.map((s) => s.value),
        ...aggregateIntervals(d, weights, draws),
      };
    ["est_m0", "aqua_count", "terra_count", "snpp_count"].forEach(
      (field, j) => {
        totals[field] = d.months.map((_, t) => {
          let sum = 0;
          for (const [i, f] of weights) {
            const v = raw[(i * d.months.length + t) * 4 + j];
            if (!Number.isFinite(v)) return null;
            sum += v * f;
          }
          return sum;
        });
      },
    );
    state.weights = weights;
    state.selection = shape;
    state.series = series;
    state.totals = totals;
    state.busy = false;
    selectionLayer.clearLayers();
    L.geoJSON(shape, {
      style: { color: "#d28a3e", weight: 2, fillOpacity: 0.06 },
    }).addTo(selectionLayer);
    $("#reset-selection").hidden = false;
    $("#selection-note").hidden = false;
    const small =
      area(shape) <
      area(
        cellPolygon(
          d.cells.lat_idx[weights[0][0]],
          d.cells.lon_idx[weights[0][0]],
          d.cell_deg,
        ),
      );
    $("#selection-note").textContent =
      `Custom area · ${fmt(area(shape) / 1e6)} km² · ${weights.length} intersecting cells. Counts are allocated by cell overlap area${small ? "; this area is smaller than one grid cell" : ""}. Stability bands use 20 resamples and are approximate, uncalibrated bands.`;
    $("#calendar-region").textContent =
      names[state.region][0] + " / custom area";
    render();
    status("Custom area · area-weighted approximation");
    $("#cell-count").textContent = fmt(weights.length) + " intersecting cells";
  } catch (e) {
    if (epoch === state.epoch) {
      state.busy = false;
      showError(e.message);
      status("Selection not applied");
    }
  }
}
function resetSelection() {
  state.epoch++;
  loadRegion(state.region);
}
// Each render step is timed so slow steps show up in the console and in
// window.fireAtlas.timings (used to find the region-switch bottleneck).
function timed(name, fn) {
  const t0 = performance.now();
  fn();
  state.timings[name] = Math.round(performance.now() - t0);
}
function render() {
  timed("card", renderInsight);
  timed("calendar", renderCalendar);
  timed("map", renderMap);
  timed("chart", renderTrend);
}
// Is month t a model estimate or otherwise not an exact count?
function approximate(t) {
  const src = state.data.month_source[t];
  return src.startsWith("model_") || src === "noaa20_scaled" || !!state.weights;
}
function renderInsight() {
  if (!state.data) return;
  const t = state.data.months.indexOf(state.selected),
    r = anomaly(state.series, state.selected, state.asOf, state.baseline),
    monthName = new Date(state.selected + "-15T00:00:00Z").toLocaleDateString(
      "en-US",
      { month: "long", timeZone: "UTC" },
    ),
    src = state.data.month_source[t];
  $("#focus-month").textContent = fullMonth(state.selected);
  $("#map-month").textContent = fullMonth(state.selected);
  $("#focus-value").textContent = count(r.value, approximate(t));
  $("#focus-caption").textContent =
    "VIIRS-equivalent detections · " +
    (state.weights
      ? "custom area, area-weighted"
      : src === "snpp"
        ? "observed (S-NPP VIIRS)"
        : src === "noaa20_scaled"
          ? "scaled NOAA-20 observation"
          : "model estimate");
  const level = $("#activity-level");
  level.className = "activity-level " + (r.level || "neutral");
  const labels = {
    high: "Above normal",
    normal: "Normal",
    low: "Below normal",
  };
  const statuses = {
    no_data: "No data",
    month_in_progress: "Month still in progress",
    incomplete_coverage: "Incomplete coverage · not graded",
    no_history: "No comparable history",
    insufficient_history: "Not graded · fewer than 10 reference years",
  };
  // The grade is the percentile; the ratio to the median is context only.
  level.textContent = r.level
    ? `${labels[r.level]} · ${ordinal(r.percentile)} percentile`
    : statuses[r.status] || "Not graded";
  const refs = r.ref_years
      .map(
        (y) =>
          state.series.find(
            (s) => s.month === y + state.selected.slice(4),
          )?.value,
      )
      .filter((v) => v != null),
    higher = refs.filter((v) => v > r.value + 0.005).length,
    allLower = refs.length > 0 && refs.every((v) => v < r.value - 0.005),
    span = r.ref_years.length
      ? `${r.ref_years[0]}–${r.ref_years.at(-1)}`
      : "";
  let copy;
  if (r.percentile == null)
    copy =
      r.status === "month_in_progress"
        ? "This month is not over yet, so it is not compared with history."
        : "This month cannot be graded against complete historical months.";
  else {
    copy = allLower
      ? `Higher than all ${r.n_ref} previous ${monthName}s (${span}). `
      : `${higher === 0 ? "None" : higher} of ${r.n_ref} previous ${monthName}s (${span}) ${higher === 1 ? "was" : "were"} higher. `;
    if (!r.level)
      copy += "At least 10 reference years are needed for a grade.";
    else {
      copy += "Graded by percentile: above normal from the 90th, below normal up to the 10th.";
      if (r.level === "normal" && r.ratio != null && r.ratio >= 1.5)
        copy += ` It is ${r.ratio.toFixed(1)}× the median, but that alone does not make it unusual: fire years vary a lot.`;
      else if (r.level === "normal" && r.ratio != null && r.ratio <= 0.67)
        copy += ` It is ${r.ratio.toFixed(1)}× the median, still within the usual range.`;
    }
  }
  $("#anomaly-description").textContent = copy;
  $("#percentile-rank").textContent =
    r.percentile == null
      ? "—"
      : `${ordinal(r.percentile)}${r.level ? "" : " (not graded)"}`;
  $("#historical-median").textContent =
    r.median == null ? "—" : count(r.median, !Number.isInteger(r.median));
  $("#median-ratio").textContent =
    r.ratio == null
      ? r.notes.includes("small_median")
        ? "Not shown"
        : "—"
      : r.ratio.toFixed(1) + "×";
  $("#reference-years").textContent = String(r.n_ref);
  $("#percentile-marker").style.left = (r.percentile ?? 50) + "%";
  $("#percentile-marker").style.opacity = r.percentile == null ? 0 : 1;
  const warnings = [];
  if (r.preliminary) warnings.push("Preliminary · near-real-time data");
  if (!state.data.month_input_complete[t])
    warnings.push("Input coverage is incomplete");
  if (r.notes.includes("small_median"))
    warnings.push("Historically fewer than 5 detections: no ratio shown");
  if (state.data.role === "holdout")
    warnings.push("Unseen region · lower confidence");
  if (src === "model_terra_bridge")
    warnings.push("Terra bridge · low-confidence estimate");
  if (src === "noaa20_scaled")
    warnings.push("Scaled NOAA-20 · continuity not yet human-reviewed");
  $("#quality-note").innerHTML =
    `<span class="tiny-source">${sources[src]?.[0] || esc(src)}</span>${warnings.map((w) => `<span>${icon("info")}${esc(w)}</span>`).join("")}<small>Baseline: ${state.baseline === "all" ? "available history since 2001" : "S-NPP observations only"} · as of ${state.asOf} UTC · v1</small>`;
}

function color(value, max) {
  if (value == null) return "transparent";
  if (value <= 0) return palette[0];
  return palette[
    Math.max(
      1,
      Math.min(
        palette.length - 1,
        Math.ceil(
          (Math.log1p(value) / Math.log1p(max || 1)) * (palette.length - 1),
        ),
      ),
    )
  ];
}
function calendarValues() {
  return state.totals?.[state.mode] || [];
}
// One colour scale per area, fitted to the harmonized series and shared by both
// calendar views, so switching to the direct splice keeps "same colour = same count".
function calendarScale() {
  return logPercentileScale(state.totals?.est || []);
}
function renderCalendar() {
  hideTooltip();
  if (!state.data) return;
  const values = calendarValues(),
    scale = calendarScale(),
    lookup = new Map(state.data.months.map((m, t) => [m, t]));
  $("#scale-lo").textContent = scale.lo == null ? "—" : "≤ " + compact(Math.round(scale.lo));
  $("#scale-hi").textContent = scale.hi == null ? "—" : compact(Math.round(scale.hi)) + "+";
  renderCalendarNote();
  const annual = annualTotals(state.data.months, values);
  let html =
    '<div class="cal-head year-head">Year</div>' +
    monthsShort.map((m) => `<div class="cal-head">${m}</div>`).join("") +
    '<div class="cal-head annual-head">Annual total</div>';
  for (let y = state.end; y >= state.start; y--) {
    const yearTotal = annual.get(y)?.total ?? null;
    html += `<button class="cal-year ${state.selected.startsWith(y + "-") ? "focus-year" : ""}" data-year="${y}" aria-label="Focus on ${y}">${y}${y === 2000 || y === 2026 ? "<sup>·</sup>" : ""}</button>`;
    for (let m = 1; m <= 12; m++) {
      const month = `${y}-${String(m).padStart(2, "0")}`,
        t = lookup.get(month),
        v = t == null ? null : values[t],
        src = t == null ? "" : state.data.month_source[t];
      // Stripes mark model estimates; the direct splice shows only recorded values.
      const est = state.mode === "est",
        estimated = est && src.startsWith("model_"),
        low =
          estimated &&
          (src === "model_terra_bridge" || state.data.role === "holdout");
      const flags =
        t != null &&
        (state.data.month_nrt[t] || !state.data.month_input_complete[t]);
      // A blank splice month reads its reason aloud, the same one the tooltip gives.
      const gap =
        !est && t != null && v == null
          ? spliceGapReason(state.data, state.totals.est_m0, t)
          : null;
      const label = gap
        ? `no direct-splice value. ${esc(gap)}`
        : `${v == null ? "no data" : count(v, est && approximate(t)) + (est ? " VIIRS-equivalent detections" : " detections, direct splice")}, ${(est ? sources[src]?.[0] : spliceSource(month)) || "no source"}${flags ? ", preliminary or incomplete" : ""}`;
      html += `<button class="cal-cell ${v == null ? "missing" : v === 0 ? "zero" : ""} ${low ? "estimated low-confidence" : estimated ? "estimated" : "observed"} ${state.selected === month ? "chosen" : ""}" style="--cell:${scale.color(v) || "transparent"}" data-month="${month}" ${t == null ? "disabled" : ""} aria-label="${fullMonth(month)}: ${label}" ${state.selected === month ? 'aria-pressed="true"' : 'aria-pressed="false"'}>${flags ? "<span>•</span>" : ""}</button>`;
    }
    html +=
      yearTotal == null && annual.has(y)
        ? `<span class="annual-total muted" title="Not summed: this view is missing some of ${y}'s months">—</span>`
        : `<span class="annual-total">${compact(yearTotal)}</span>`;
    if (y > state.start) html += calendarDivider(y);
  }
  html += '<div class="median-label">Median</div>';
  for (let m = 1; m <= 12; m++) {
    const s = state.series
      .filter(
        (r) =>
          +r.month.slice(5) === m &&
          +r.month.slice(0, 4) >= 2001 &&
          +r.month.slice(0, 4) < +state.selected.slice(0, 4) &&
          r.input_complete &&
          r.value != null &&
          (state.baseline === "all" || r.source === "snpp"),
      )
      .map((r) => r.value)
      .sort((a, b) => a - b);
    html += `<span class="median-value" title="Historical median for ${monthsShort[m - 1]}, using the anomaly baseline">${s.length ? compact(roundEstimate(quantile(s, 0.5))) : "—"}</span>`;
  }
  html += '<span class="median-value">—</span>';
  $("#calendar").innerHTML = html;
  $("#calendar")
    .querySelectorAll("[data-month]")
    .forEach((b) => {
      b.onclick = () => {
        state.selected = b.dataset.month;
        renderInsight();
        renderCalendar();
        renderMap();
        renderTrend();
      };
      b.onpointerenter = (e) => showTooltip(e, b.dataset.month);
      b.onpointermove = moveTooltip;
      b.onpointerleave = hideTooltip;
      b.onfocus = () => {
        const r = b.getBoundingClientRect();
        showTooltip(
          { clientX: r.left + r.width / 2, clientY: r.bottom },
          b.dataset.month,
        );
      };
      b.onblur = hideTooltip;
      b.onkeydown = (e) => {
        const next = {
          ArrowLeft: -1,
          ArrowRight: 1,
          ArrowUp: 12,
          ArrowDown: -12,
        }[e.key];
        if (next) {
          e.preventDefault();
          const i = state.data.months.indexOf(b.dataset.month) + next;
          $("#calendar")
            .querySelector(`[data-month="${state.data.months[i]}"]`)
            ?.focus();
        }
      };
    });
  $("#calendar")
    .querySelectorAll("[data-year]")
    .forEach(
      (b) =>
        (b.onclick = () => {
          state.selected = b.dataset.year + "-" + state.selected.slice(5);
          if (!state.data.months.includes(state.selected))
            state.selected = state.data.months.find((m) =>
              m.startsWith(b.dataset.year + "-"),
            );
          render();
        }),
    );
}
// A labelled rule between year rows where the kind of value changes
// (model estimate ↔ observation, or MODIS ↔ VIIRS in the direct splice).
function calendarDivider(y) {
  const d = state.data,
    firstObs = d.months.find((m, t) => d.month_source[t] === "snpp"),
    row = (up, down) =>
      `<div class="cal-divider" role="separator"><span>▲ ${up}</span><i></i><span>▼ ${down}</span></div>`;
  if (state.mode === "est") {
    if (firstObs && y === +firstObs.slice(0, 4))
      return row(
        `Observations: S-NPP VIIRS from ${firstObs}`,
        "Model estimates from MODIS, including the 2012–13 blind-test years",
      );
    return "";
  }
  if (d.role !== "holdout" && y === 2014)
    return row("S-NPP VIIRS as recorded", "2012-02 to 2013-12 withheld for the blind test");
  if (y === 2012)
    return row(
      d.role === "holdout" ? "No VIIRS: held out to test the model" : "S-NPP withheld",
      "MODIS as recorded (Terra, then Aqua from 2002-07)",
    );
  return "";
}
// Explains the current calendar view in one line: what each view is and why
// some months are blank (never leaves a blank unexplained).
function renderCalendarNote() {
  const d = state.data,
    note = $("#calendar-note");
  let text = "";
  if (state.mode === "est" && d.role === "holdout")
    text =
      "Holdout region: every month is a model estimate from MODIS (striped). Its VIIRS data were held out to test the model, so no month here is a VIIRS observation, and errors are larger than in the training regions.";
  if (state.mode === "est_m0") {
    if (d.role === "holdout")
      text =
        "Direct splice: MODIS as recorded until 2012-01. This is a holdout region — its VIIRS data were held out to test the model — so there is nothing to splice on after 2012-01, and those months are blank, not zero.";
    else {
      const outages = [
        ...new Set(
          d.months
            .filter(
              (m, t) =>
                d.month_source[t] === "noaa20_scaled" &&
                state.totals.est_m0[t] == null,
            )
            .map((m) => m.slice(0, 4)),
        ),
      ];
      text = `Direct splice: MODIS as recorded until 2012-01, S-NPP VIIRS from 2014-01, on the same colour scale as the harmonized view — the darker shades from 2014 are the sensor change, not more fire. 2012-02 to 2013-12 is blank, not zero: S-NPP VIIRS for those years is withheld for the one-time blind test, and only the external grader has it.${outages.length ? ` Blank months in ${outages.join(", ")} are S-NPP outages.` : ""}`;
    }
  }
  note.textContent = text;
  note.hidden = !text;
}
function showTooltip(e, month) {
  const t = state.data.months.indexOf(month);
  if (t < 0) return;
  const v = calendarValues()[t],
    lo = state.totals.lo_90[t],
    hi = state.totals.hi_90[t],
    splice = state.mode === "est_m0",
    gap = splice ? spliceGapReason(state.data, state.totals.est_m0, t) : null;
  $("#tooltip").innerHTML =
    `<strong>${fullMonth(month)}</strong>` +
    (gap
      ? `<span>No direct-splice value</span><small>${esc(gap)}</small>`
      : `<span>${count(v, !splice && approximate(t))} ${splice ? "detections, direct splice" : "VIIRS-equivalent detections"}</span><small>${splice ? spliceSource(month) : sources[state.data.month_source[t]]?.[0]}${state.data.month_nrt[t] ? " · preliminary" : ""}${state.data.month_input_complete[t] ? "" : " · incomplete coverage"}</small>${!splice && state.data.month_source[t].startsWith("model_") ? `<small>Stability band: ${approx(lo)} to ${approx(hi)}${state.weights ? " (20 draws, approximate)" : ""}</small>` : ""}`);
  $("#tooltip").hidden = false;
  moveTooltip(e);
}
function moveTooltip(e) {
  const el = $("#tooltip");
  el.style.left =
    Math.min(
      window.innerWidth - el.offsetWidth - 12,
      Math.max(12, e.clientX + 14),
    ) + "px";
  el.style.top =
    Math.min(window.innerHeight - el.offsetHeight - 12, e.clientY + 16) + "px";
}
function hideTooltip() {
  $("#tooltip").hidden = true;
}
function renderMap() {
  if (!state.data) return;
  const d = state.data,
    t = d.months.indexOf(state.selected),
    geo =
      d._geo ||
      (d._geo = {
        lat: Float32Array.from(d.cells.lat_idx, (i) => -90 + i * d.cell_deg),
        lng: Float32Array.from(d.cells.lon_idx, (j) => -180 + j * d.cell_deg),
        index: cellIndex(d.cells, d.cell_deg),
      });
  let max = 1;
  for (const row of d.est) if (row[t] > max) max = row[t];
  gridLayer.setCells({
    lat: geo.lat,
    lng: geo.lng,
    deg: d.cell_deg,
    color: d.est.map((row) => (row[t] > 0 ? color(row[t], max) : null)),
  });
}
// Annual totals: harmonized vs the direct splice (MODIS until 2012-01, S-NPP after),
// with Aqua MODIS and S-NPP VIIRS as recorded for reference.
const TREND = [
  { key: "est", label: "Harmonized", color: "#2b7a5f", approx: true },
  { key: "est_m0", label: "Direct splice", color: "#c18145" },
  { key: "aqua_count", label: "Aqua MODIS", color: "#d3ad84", dash: "6 4" },
  { key: "snpp_count", label: "S-NPP VIIRS", color: "#2c3e50", dots: true },
];
// Axis: about four gridlines at 1/2/5 × 10^k steps.
const niceStep = (v) => {
  const p = 10 ** Math.floor(Math.log10(v)),
    m = v / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p;
};
function trendAnnual() {
  const d = state.data,
    usable = {
      est: (t) => state.totals.est[t] != null,
      est_m0: (t) => state.totals.est_m0?.[t] != null,
      aqua_count: (t) => state.totals.aqua_count?.[t] != null,
      // NOAA-20 months are partial S-NPP months: leave those years off the S-NPP line.
      snpp_count: (t) =>
        d.month_source[t] === "snpp" && state.totals.snpp_count?.[t] != null,
    };
  return Object.fromEntries(
    TREND.map((s) => [
      s.key,
      annualTotals(d.months, state.totals[s.key] || [], usable[s.key]),
    ]),
  );
}
function renderTrend() {
  if (!state.data) return;
  const d = state.data,
    box = $("#trend"),
    cs = getComputedStyle(box),
    inner =
      box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  // Draw at the real pixel width so labels stay legible on phones.
  const W = Math.max(300, Math.round(inner) || 1060),
    narrow = W < 640,
    H = narrow ? 250 : 262,
    pad = { l: 46, r: 12, t: narrow ? 62 : 46, b: 30 },
    ys = Array.from(
      { length: state.end - state.start + 1 },
      (_, i) => state.start + i,
    ),
    step = ys.length > 1 ? (W - pad.l - pad.r) / (ys.length - 1) : 0,
    x = (i) => (ys.length === 1 ? (pad.l + W - pad.r) / 2 : pad.l + i * step),
    annual = trendAnnual(),
    at = (key, yr) => annual[key].get(yr) || null;
  const all = TREND.flatMap((s) =>
    ys.map((yr) => at(s.key, yr)?.total).filter((v) => v != null),
  );
  const tick = niceStep(Math.max(1, ...all) / 4),
    max = tick * Math.max(1, Math.ceil(Math.max(1, ...all) / tick)),
    y = (v) => H - pad.b - (v / max) * (H - pad.t - pad.b),
    half = Math.max(10, step / 2),
    i2011 = ys.indexOf(2011),
    i2012 = ys.indexOf(2012),
    i2013 = ys.indexOf(2013),
    holdout = d.role === "holdout",
    splice = state.mode === "est_m0";
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Annual totals: harmonized, direct splice, Aqua MODIS and S-NPP VIIRS">`;
  // 2012–13 (training) or 2012 onwards (holdout): no S-NPP VIIRS available here.
  if (i2012 >= 0 && (holdout || i2013 >= 0)) {
    const x0 = x(i2012) - half,
      x1 = holdout ? W - pad.r : x(i2013) + half;
    const label = holdout
      ? "No VIIRS here: held out to test the model"
      : "S-NPP withheld";
    svg += `<rect class="trend-band" x="${x0}" y="${pad.t}" width="${x1 - x0}" height="${H - pad.t - pad.b}"/>${x1 - x0 > label.length * 5.6 ? `<text class="band-label" x="${(x0 + x1) / 2}" y="${pad.t + 14}" text-anchor="middle">${label}</text>` : ""}`;
  }
  for (let v = 0; v <= max + tick / 2; v += tick) {
    svg += `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y(v)}" y2="${y(v)}" stroke="#e8eae3"/><text x="${pad.l - 10}" y="${y(v) + 4}" text-anchor="end">${compact(v)}</text>`;
  }
  const selected = ys.indexOf(+state.selected.slice(0, 4));
  if (selected >= 0)
    svg += `<rect x="${x(selected) - Math.min(12, half)}" y="${pad.t - 6}" width="${2 * Math.min(12, half)}" height="${H - pad.b - pad.t + 6}" fill="#eef1e8"/>`;
  // Sensor switch: MODIS as recorded until 2012-01, S-NPP VIIRS after.
  if (i2011 >= 0 && i2012 >= 0) {
    const xb = (x(i2011) + x(i2012)) / 2;
    const top = narrow && !holdout ? 12 : pad.t - 30;
    svg += `<line class="switch-line" x1="${xb}" x2="${xb}" y1="${top + 4}" y2="${H - pad.b}"/>`;
    svg += `<text class="switch-label" x="${xb - 6}" y="${top}" text-anchor="end">← MODIS</text><text class="switch-label" x="${xb + 6}" y="${top}">${holdout ? "VIIRS withheld →" : "S-NPP VIIRS →"}</text>`;
    if (!holdout) {
      // Keep the callout inside the chart; two lines on narrow screens.
      const lines =
          W - pad.r - xb > 400
            ? ["2012 jump in the direct splice: sensor change, not more fire"]
            : ["Splice jump at 2012 =", "sensor change, not more fire"],
        widest = Math.max(...lines.map((l) => l.length)) * 6.7,
        fits = xb + 6 + widest < W - pad.r;
      lines.forEach((l, k) => {
        svg += `<text class="switch-callout" x="${fits ? xb + 6 : W - pad.r}" y="${pad.t - 14 - 15 * (lines.length - 1 - k)}" text-anchor="${fits ? "start" : "end"}">${l}</text>`;
      });
    }
  }
  const lineOrder = splice
    ? ["aqua_count", "est", "est_m0"]
    : ["aqua_count", "est_m0", "est"];
  for (const key of lineOrder) {
    const s = TREND.find((t) => t.key === key),
      strong = key === (splice ? "est_m0" : "est"),
      width = key === "aqua_count" ? 1.5 : strong ? 3 : 1.75,
      opacity = key === "aqua_count" || strong ? 1 : splice ? 0.55 : 0.9;
    let path = "",
      open = false,
      hollow = "";
    ys.forEach((yr, i) => {
      const a = at(key, yr);
      if (!a || a.total == null) return void (open = false);
      if (a.partial) {
        // 2000 and 2026 are part-years in the dataset: show, but do not join.
        hollow += `<circle cx="${x(i)}" cy="${y(a.total)}" r="3.5" fill="#fffefa" stroke="${s.color}" stroke-width="1.5" opacity="${opacity}"/>`;
        return void (open = false);
      }
      path += `${open ? "L" : "M"}${x(i).toFixed(1)},${y(a.total).toFixed(1)}`;
      open = true;
    });
    svg += `<path d="${path}" fill="none" stroke="${s.color}" stroke-width="${width}" stroke-linejoin="round" stroke-linecap="round" opacity="${opacity}" ${s.dash ? `stroke-dasharray="${s.dash}"` : ""}/>${hollow}`;
    // Bridge the withheld 2012–13 gap so the size of the splice's jump is visible.
    const before = at(key, 2011)?.total,
      after = at(key, 2014)?.total;
    if (key === "est_m0" && before != null && after != null && i2011 >= 0)
      svg += `<path d="M${x(i2011)},${y(before)}L${x(ys.indexOf(2014))},${y(after)}" fill="none" stroke="${s.color}" stroke-width="${Math.max(1.5, width - 0.75)}" stroke-dasharray="2 4" stroke-linecap="round" opacity="${opacity}"/>`;
  }
  // S-NPP as dots on top, with a surface ring, so it stays visible where it equals the harmonized line.
  ys.forEach((yr, i) => {
    const a = at("snpp_count", yr);
    if (a?.total != null)
      svg += `<circle cx="${x(i)}" cy="${y(a.total)}" r="${a.partial ? 3 : 3.6}" fill="${a.partial ? "#fffefa" : "#2c3e50"}" stroke="${a.partial ? "#2c3e50" : "#fffefa"}" stroke-width="1.5"/>`;
  });
  const labelEvery = step < 22 ? 5 : step < 48 ? 2 : 1;
  ys.forEach((yr, i) => {
    svg += `<g class="chart-year" data-chart-year="${yr}" tabindex="0" role="button" aria-label="${esc(trendYearText(yr, annual))}. Highlight ${yr}"><rect x="${x(i) - half}" y="0" width="${2 * half}" height="${H}" fill="transparent"/>${yr % labelEvery === 0 || (i === 0 && (labelEvery - (yr % labelEvery)) * step > 30) || (i === ys.length - 1 && (yr % labelEvery) * step > 30) ? `<text x="${x(i)}" y="${H - 9}" text-anchor="middle">${yr}</text>` : ""}</g>`;
  });
  svg += "</svg>";
  box.innerHTML = svg;
  $("#trend-foot").textContent = holdout
    ? "Annual totals. This holdout region has no VIIRS data in the project, so the direct splice ends in 2011 and every harmonized value is a model estimate. 2026 ends in October (hollow marker)."
    : "Annual totals. A line skips a year when that series is missing any of its months: S-NPP 2012–13 is withheld for the blind test, and S-NPP outage years (filled with scaled NOAA-20 only in the harmonized line) drop off the S-NPP and splice lines. 2026 ends in October (hollow markers).";
  box.querySelectorAll("[data-chart-year]").forEach((el) => {
    const yr = +el.dataset.chartYear,
      action = () => {
        state.selected = yr + "-" + state.selected.slice(5);
        if (!state.data.months.includes(state.selected))
          state.selected = state.data.months.find((m) =>
            m.startsWith(yr + "-"),
          );
        render();
      };
    el.onclick = action;
    el.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        action();
      }
    };
    el.onpointerenter = (e) => {
      $("#tooltip").innerHTML =
        `<strong>${yr}</strong>` +
        TREND.map((s) => {
          const a = annual[s.key].get(yr);
          return `<small><i class="tip-key" style="background:${s.color}"></i>${s.label}: ${a?.total == null ? "—" : count(a.total, s.approx || !!state.weights)}${a?.partial ? " (part year)" : ""}</small>`;
        }).join("");
      $("#tooltip").hidden = false;
      moveTooltip(e);
    };
    el.onpointermove = moveTooltip;
    el.onpointerleave = hideTooltip;
  });
}
function trendYearText(yr, annual) {
  return (
    yr +
    ": " +
    TREND.map((s) => {
      const v = annual[s.key].get(yr)?.total;
      return `${s.label} ${v == null ? "not available" : count(v, s.approx || !!state.weights)}`;
    }).join(", ")
  );
}
let trendWidth = 0;
new ResizeObserver(() => {
  const w = $("#trend").clientWidth;
  if (w && Math.abs(w - trendWidth) > 8 && state.data) {
    trendWidth = w;
    renderTrend();
  }
}).observe($("#trend"));

function download(blob, name) {
  const u = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = u;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(u), 10000);
}
function csv() {
  if (!state.data) return;
  const headers = [
    "region",
    "selection",
    "month",
    "est",
    "lo_90",
    "hi_90",
    "source",
    "nrt",
    "input_complete",
    "est_m0",
    "aqua_count",
    "terra_count",
    "snpp_count",
    "dataset_version",
    "as_of_utc",
    "interval_method",
    "license",
  ];
  const rows = state.series
    .filter(
      (s) =>
        +s.month.slice(0, 4) >= state.start &&
        +s.month.slice(0, 4) <= state.end,
    )
    .map((s) => {
      const t = state.data.months.indexOf(s.month);
      return [
        state.region,
        state.weights ? "custom area" : "full region",
        s.month,
        s.value,
        state.totals.lo_90[t],
        state.totals.hi_90[t],
        s.source,
        s.nrt,
        s.input_complete,
        ...["est_m0", "aqua_count", "terra_count", "snpp_count"].map(
          (k) => state.totals[k]?.[t],
        ),
        "v1",
        state.asOf,
        state.weights
          ? "20 draws, approximate, uncalibrated"
          : "100 draws, regional calibration 5.37",
        "CC BY 4.0",
      ];
    });
  const quote = (v) => (v == null ? "" : `"${String(v).replace(/"/g, '""')}"`);
  download(
    new Blob(
      [
        headers.join(",") + "\n",
        rows.map((r) => r.map(quote).join(",")).join("\n") + "\n",
      ],
      { type: "text/csv;charset=utf-8" },
    ),
    `${state.region}${state.weights ? "-custom" : ""}-monthly-v1.csv`,
  );
  if (state.selection)
    download(
      new Blob([JSON.stringify(state.selection)], {
        type: "application/geo+json",
      }),
      state.region + "-selection.geojson",
    );
}
function exportPNG() {
  if (!state.data) return;
  const rows = state.end - state.start + 1,
    c = document.createElement("canvas");
  c.width = 1440;
  c.height = 220 + rows * 30;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#f7f7f2";
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.fillStyle = "#23382e";
  ctx.font = "bold 32px sans-serif";
  ctx.fillText(
    "Fire Atlas / " +
      names[state.region][0] +
      (state.weights ? " — custom area" : ""),
    45,
    58,
  );
  ctx.font = "16px sans-serif";
  ctx.fillStyle = "#68736a";
  ctx.fillText(
    `${state.mode === "est" ? "Harmonized VIIRS-equivalent" : "Direct-splice"} detections · Dataset v1 · 0.25° grid × UTC month`,
    45,
    90,
  );
  monthsShort.forEach((m, i) => ctx.fillText(m, 125 + i * 98, 134));
  const values = calendarValues(),
    scale = calendarScale();
  for (let y = state.end; y >= state.start; y--) {
    const yy = 156 + (state.end - y) * 30;
    ctx.fillStyle = "#435047";
    ctx.fillText(y, 45, yy + 17);
    for (let m = 1; m <= 12; m++) {
      const t = state.data.months.indexOf(`${y}-${String(m).padStart(2, "0")}`),
        v = t < 0 ? null : values[t];
      ctx.fillStyle = v == null ? "#dddeda" : scale.color(v);
      ctx.fillRect(120 + (m - 1) * 98, yy, 91, 23);
      const estimated =
        t >= 0 &&
        v != null &&
        state.mode === "est" &&
        state.data.month_source[t].startsWith("model_");
      if (estimated) {
        // Same fine stripes as on screen: model estimates.
        ctx.save();
        ctx.beginPath();
        ctx.rect(120 + (m - 1) * 98, yy, 91, 23);
        ctx.clip();
        ctx.strokeStyle = "rgba(255,255,255,0.5)";
        ctx.lineWidth = 1;
        for (let k = -23; k < 91; k += 6) {
          ctx.beginPath();
          ctx.moveTo(120 + (m - 1) * 98 + k, yy + 23);
          ctx.lineTo(120 + (m - 1) * 98 + k + 23, yy);
          ctx.stroke();
        }
        ctx.restore();
      }
      if (
        estimated &&
        (state.data.month_source[t] === "model_terra_bridge" ||
          state.data.role === "holdout")
      ) {
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = "#6b7165";
        ctx.strokeRect(120 + (m - 1) * 98, yy, 91, 23);
        ctx.setLineDash([]);
      }
    }
  }
  ctx.font = "14px sans-serif";
  ctx.fillStyle = "#68736a";
  // Whole numbers, matching the on-page legend.
  const end = (v) => compact(v == null ? null : Math.round(v));
  ctx.fillText(
    `Team Inspiratio · NASA FIRMS MODIS & VIIRS · CC BY 4.0 · ${state.mode === "est" ? "Striped = model estimate · " : ""}Log colour scale from ${end(scale.lo)} (5th percentile) to ${end(scale.hi)} (99th percentile) of this area`,
    45,
    c.height - 24,
  );
  c.toBlob((b) => download(b, `${state.region}-fire-calendar-v1.png`));
}
$("#download-csv").onclick = () => $("#downloads-dialog").showModal();
if (location.hash === "#data") $("#downloads-dialog").showModal();
$("#modal-csv").onclick = csv;
$("#modal-png").onclick = exportPNG;
$("#download-image").onclick = exportPNG;
// Small read-only debug surface for browser acceptance tests; no credentials or network mutation.
window.fireAtlas = {
  get state() {
    return state;
  },
  get timings() {
    return state.timings;
  },
  applySelection,
  resetSelection,
  anomaly,
};
await loadRegion(state.region);
