import "./style.css";
import "./research.css";
import "./hallmark.css";
import { createActivityMap } from "./activity-map.js";
import { catalog, loadRegion, loadArea, evidence } from "./data.js";
import { anomaly, sourceLabel, count, csv, validateBounds, annual } from "./science.js";
const $ = (s) => document.querySelector(s),
  $$ = (s) => [...document.querySelectorAll(s)];
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const date = new Date().toISOString().slice(0, 10),
  months = [
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
const state = {
  region: null,
  target: "",
  baseline: "all",
  mode: "value",
  subset: null,
  busy: false,
  start: "2000-11",
  end: "2026-10",
  palette: "red",
};
let items = [],
  sample = true,
  loadId = 0;
const icon = `<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="12" fill="none" stroke="currentColor"/><ellipse cx="16" cy="16" rx="6" ry="12" fill="none" stroke="currentColor"/><path d="M4 16h24M7 9h18M7 23h18" stroke="currentColor"/></svg>`;
$("#app").innerHTML = `
<a class="skip" href="#workspace">Skip to data explorer</a>
<header><a class="brand" href="#">${icon}<span>Inspiratio<small>Fire history, harmonized</small></span></a><nav aria-label="Main navigation"><a href="#workspace">Explore</a><a href="#method">Methods &amp; evidence</a><button class="text-button" id="share">Share this view</button></nav><details class="accessibility"><summary>Display & accessibility</summary><div><label><input type="checkbox" id="color-assist"> Color-vision assistance</label><label>Assistance palette<select id="palette"><option value="teal">Sequential teal</option><option value="mono">Monochrome</option></select></label><label><input type="checkbox" id="contrast"> High contrast</label><label><input type="checkbox" id="large-text"> Larger text</label><label><input type="checkbox" id="reduce-motion"> Reduce motion</label></div></details></header>
<main>
<section class="intro"><div><h1>Satellite fire activity<br>on a common scale</h1><p>From MODIS to VIIRS, put satellite fire detections on the same scale. <br>Choose a place. Explore its seasons and changes.</p></div><div class="intro-note"><span class="orbit">2000 <i></i> 2026</span><p>Monthly records / 0.25° grid<br>VIIRS-equivalent detections</p><a href="#method">Why harmonize? <span aria-hidden="true"><svg class="external-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 12 12 4M5 4h7v7" fill="none" stroke="currentColor" stroke-width="1.3"/></svg></span></a></div></section>
<div id="notice" class="notice" role="status">Loading the data catalog…</div>
<section id="workspace" aria-label="Fire history explorer"><div class="workspace-head"><div><span class="dot"></span><h2>Find a place</h2></div><label>Region <select id="region" aria-label="Choose a region"></select></label></div>
<div class="workspace-grid"><section class="geography" aria-label="Geographic location"><div class="map-top"><span id="map-title">World overview</span><span>Interactive map</span></div><section id="custom" aria-label="Custom area selection"><h3>Select your own area</h3><div class="area-tools"><button id="draw-area" aria-pressed="false">Draw rectangle</button><button id="pan-map" aria-pressed="true">Pan map</button><button id="chongqing-example">Example: Chongqing · Aug 2022</button></div><p>Enter coordinates, or choose Draw rectangle and drag with the left mouse button. Matching data regions load automatically. West &gt; east crosses 180°. Boundary cells use approximate area weights.</p><form id="bbox-form"><label>West longitude<input name="w" type="number" step="any" min="-180" max="180" required></label><label>South latitude<input name="s" type="number" step="any" min="-90" max="90" required></label><label>East longitude<input name="e" type="number" step="any" min="-180" max="180" required></label><label>North latitude<input name="n" type="number" step="any" min="-90" max="90" required></label><button class="primary" type="submit">Apply area</button><button type="button" id="clear-box">Clear area</button></form><p id="bbox-message" role="status"></p></section><p id="draw-status" class="map-help" role="status">Pan mode · Drag to move, scroll to zoom. Choose Draw rectangle to select an area.</p><div id="map" role="region" aria-label="Interactive fire activity map"></div><p class="map-help">Scroll to zoom · Drag to pan · City labels appear as you zoom in</p><div class="map-bottom"><p id="coordinates">Choose a region to explore</p><div class="zoom"><button id="zoom-out" aria-label="Zoom out">−</button><button id="zoom-in" aria-label="Zoom in">＋</button><button id="zoom-reset">Fit main activity</button><button id="zoom-all">Full coverage</button></div></div><div class="spatial-legend"><span id="map-grid-status" role="status"></span><span>0</span><i id="map-ramp"></i><span id="map-max"></span><span>detections / cell · log scale</span></div><p id="map-cell-info" role="status">Hover over a grid cell to read its value.</p><div id="region-pills" class="region-pills"></div></section>
<aside class="inspector" aria-label="Analysis of the selected month"><div class="place"><span id="region-kind">Regional record</span><h2 id="place-name">Loading</h2></div><label class="month-label">Month<select id="target" aria-label="Choose a month"></select></label><div id="reading" aria-live="polite"></div><label class="baseline-label">Same-month reference period<select id="baseline"><option value="all">All available years from 2001</option><option value="snpp">S-NPP observation years only</option></select></label><p class="asof">As of <span id="asof"></span> (UTC)</p></aside></div></section>
<section class="history" id="history"><div class="section-heading"><div><h2>Monthly burning activity</h2><p id="calendar-description">Read across for seasons. Read down to compare the same month.</p></div><div class="segmented" role="group" aria-label="Displayed series"><button id="harmonized" aria-pressed="true">Harmonized</button><button id="raw" aria-pressed="false">Direct splice</button></div></div><p id="series-note" class="muted"></p><div class="range-controls"><label>From <input id="range-start" type="text" inputmode="numeric" pattern="20[0-9]{2}-(0[1-9]|1[0-2])" placeholder="YYYY-MM" aria-label="Date in YYYY-MM format" value="2000-11"></label><label>To <input id="range-end" type="text" inputmode="numeric" pattern="20[0-9]{2}-(0[1-9]|1[0-2])" placeholder="YYYY-MM" value="2026-10"></label><button id="range-reset">All available months</button><label><input type="checkbox" id="values-toggle"> Show cell values</label><span id="range-status" role="status"></span></div><div class="history-grid"><div class="calendar-wrap"><div id="calendar" role="group" aria-label="Monthly fire calendar"></div><div class="legend"><span>0</span><i id="calendar-ramp"></i><span id="legend-max">More</span><span class="missing-key"></span><span>Unavailable</span></div><p class="muted">Logarithmic color scale for this region; colors are not comparable across regions. Select a month to see its value, source and interval.</p></div><div class="season-panel"><h3 id="chart-heading">The same month, across years</h3><p id="chart-caption"></p><div id="chart"></div><p class="muted" id="chart-note"></p><div class="export-actions"><button id="download-csv" class="primary">Download monthly CSV <span aria-hidden="true">↓</span></button><button id="download-image">Save calendar image</button></div><p class="muted">Exports retain the data version, source and quality flags. Fire detections are not individual fires.</p></div></div></section>
<details class="data-table-panel"><summary>Read monthly values as a table</summary><div class="table-scroll"><table><caption>Selected date range · harmonized monthly detections</caption><thead><tr><th scope="col">Month</th><th scope="col">Detections</th><th scope="col">Source</th><th scope="col">Coverage</th><th scope="col">Product</th></tr></thead><tbody id="monthly-table"></tbody></table></div></details><section class="method" id="method"><div class="method-intro"><h2>A new satellite<br>The same history</h2><p>VIIRS detects more small fires than MODIS. Joining their records directly can make a sensor change look like a change in fire activity. We use MODIS information to estimate detections at the same location on the VIIRS scale.</p></div><div class="method-body"><h3>The evidence behind the record</h3><div class="evidence-grid"><div><strong>22%</strong><p>Lower MALE than the simple-ratio baseline in the demonstration-region blind test. This result belongs to the v1 three-region model.</p></div><div><strong>${evidence.global.combined.e028_global.all.male.toFixed(3)}</strong><p>Global-model validation MALE, compared with ${evidence.global.combined.m1s.all.male.toFixed(3)} for the simple-ratio baseline. The globally retrained model was not blind-tested again.</p></div><div><strong>16.75×</strong><p>Calibration multiplier for global regional intervals. These describe model stability, not a probability guarantee for the true value.</p></div></div><details><summary>How do observations, estimates and gaps differ?</summary><p>Complete S-NPP months from 2014 use observed counts. Earlier months and holdout regions use model estimates; Terra-only months use a low-confidence bridge. Missing S-NPP months may use scaled NOAA-20 counts, whose continuity should not be assumed. The 2012–2013 S-NPP test data remain isolated.</p></details><details><summary>Where should results be treated cautiously?</summary><p>Model results for boreal forests, the Middle East and holdout regions need cautious interpretation. In v1, holdout error was about 2.5 times the training-region error. Clouds, smoke and satellite overpass times cause missed detections. Near-real-time data may be revised. Incomplete months receive no anomaly classification; fewer than 10 reference years means no activity category.</p></details><details><summary>Intervals and custom areas</summary><p>Preset regions use the published regional intervals: sum each resample over the region, then take quantiles. Custom areas show overlap-weighted point estimates only. Cell quantiles are never added to invent an interval. Custom selections load intersecting global release partitions and exclude overlapping demonstration boxes to avoid duplicate counts. Unsupplied cells are not invented.</p></details><div class="source-links"><a href="https://github.com/team-inspiratio/inspiratio-space-apps-2026/blob/main/docs/data-card.md" target="_blank" rel="noreferrer">Data card <svg class="external-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 12 12 4M5 4h7v7" fill="none" stroke="currentColor" stroke-width="1.3"/></svg></a><a href="https://github.com/team-inspiratio/inspiratio-space-apps-2026/releases/tag/global-v1" target="_blank" rel="noreferrer">Global data &amp; checksums <svg class="external-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 12 12 4M5 4h7v7" fill="none" stroke="currentColor" stroke-width="1.3"/></svg></a><a href="https://github.com/team-inspiratio/inspiratio-space-apps-2026/blob/main/reports/validation.md" target="_blank" rel="noreferrer">Validation report <svg class="external-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 12 12 4M5 4h7v7" fill="none" stroke="currentColor" stroke-width="1.3"/></svg></a></div></div></section>
<footer><span>Inspiratio / A common Earth record</span><p>Satellite data: NASA FIRMS · Independent reference: GFED · Geography: Natural Earth<br>Harmonized data: CC BY 4.0 · For historical comparisons, not future fire prediction.</p><a href="#">Back to top ↑</a></footer>
</main><div class="toast" id="toast" role="status"></div>`;
const activityMap = createActivityMap($("#map"), text => { $("#map-cell-info").textContent = text; }, bbox=>applyArea(bbox), enabled=>{
  $("#draw-area").setAttribute("aria-pressed",enabled);
  $("#pan-map").setAttribute("aria-pressed",!enabled);
  $("#draw-status").textContent=enabled ? "Draw mode · Hold the left mouse button and drag a rectangle. Release to apply. Escape cancels." : "Pan mode · Drag to move, scroll to zoom. Choose Draw rectangle to select an area.";
});
$("#asof").textContent = date;
const toast = (t) => {
  $("#toast").textContent = t;
  $("#toast").classList.add("visible");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => $("#toast").classList.remove("visible"), 3500);
};
function series() {
  return state.subset?.series ?? state.region.series;
}
function displayedSeries() {
  return series().filter(s => s.month >= state.start && s.month <= state.end);
}
function currentLabel() {
  return state.subset ? "Custom area" : state.region.label;
}
function setUrl() {
  const p = new URLSearchParams({
    region: state.region.name,
    month: state.target,
    baseline: state.baseline,
    start: state.start,
    end: state.end,
  });
  if (state.subset) p.set("bbox", state.subset.bbox.join(","));
  history.replaceState(null, "", "#" + p.toString());
}
async function choose(name, month) {
  activityMap.setDrawing(false);
  const id = ++loadId;
  state.busy = true;
  $("#workspace").setAttribute("aria-busy", "true");
  $("#notice").textContent = "Loading regional records…";
  try {
    const r = await loadRegion(items.find((x) => x.name === name) ?? items[0]);
    if (id !== loadId) return;
    state.region = r;
    state.subset = null;
    state.target = r.series.some((s) => s.month === month) ? month : r.target;
    render();
  } catch (e) {
    $("#notice").textContent = e.message + " Select the region again to retry.";
    toast(e.message);
  } finally {
    if (id === loadId) {
      state.busy = false;
      $("#workspace").removeAttribute("aria-busy");
    }
  }
}
function render() {
  const r = state.region,
    rows = series();
  $("#notice").innerHTML = sample
    ? "Showing <b>real v1 same-month samples</b> for four regions. Blank months are not included in these samples. The full global monthly release is not loaded."
    : "Using the <b>global-v1 release</b>, verified with SHA256 checksums. Regions load on demand, with source labels for observations and estimates.";
  $("#region").value = state.subset ? "__custom" : r.name;
  $("#place-name").textContent = currentLabel();
  $("#region-kind").textContent =
    (state.subset ? "Custom area · Overlap-weighted" : r.role === "holdout"
      ? "Holdout region · Model estimates"
      : "Regional record") +
    " / " +
    r.version;
  $("#target").innerHTML = rows
    .map(
      (s) =>
        `<option value="${s.month}">${months[+s.month.slice(5) - 1]} ${s.month.slice(0, 4)}</option>`,
    )
    .join("");
  $("#target").value = state.target;
  $("#map-title").textContent = currentLabel();
  $("#coordinates").textContent = (state.subset?.bbox ?? r.bbox)
    .map((v, i) => `${["W", "S", "E", "N"][i]} ${v}°`)
    .join(" / ");
  $("#region-pills").innerHTML = items
    .slice(0, 6)
    .map(
      (x) =>
        `<button data-region="${esc(x.name)}" aria-pressed="${x.name === r.name && !state.subset}">${esc(x.label)}</button>`,
    )
    .join("");
  $$("#region-pills button").forEach(
    (b) => (b.onclick = () => choose(b.dataset.region)),
  );
  $("#custom")
    .querySelectorAll("input,button")
    .forEach((e) => (e.disabled = !r.rawData));
  $("#bbox-message").textContent = r.rawData
    ? state.subset ? `${state.subset.cellCount.toLocaleString("en-US")} intersecting cells · Sources: ${state.subset.regions.map(x=>x.label).join(", ")} · No custom stability interval.` : "Ready: select any area. You do not need to choose its data region first."
    : "These samples contain no grid cells. Custom areas become available when the full release is loaded.";
  ["w", "s", "e", "n"].forEach(
    (k, i) =>
      ($(`#bbox-form [name=${k}]`).value = (state.subset?.bbox ?? r.bbox)[i]),
  );
  $("#raw").disabled = !rows.some((s) => s.raw != null);
  if ($("#raw").disabled) state.mode = "value";
  $("#harmonized").setAttribute("aria-pressed", state.mode === "value");
  $("#raw").setAttribute("aria-pressed", state.mode === "raw");
  $("#series-note").textContent = state.subset
    ? "Custom-area values are approximate, weighted by overlap area. Resampling intervals and individual detection records are unavailable."
    : sample
      ? "These samples contain one calendar month across years. Other months remain blank; annual totals cannot be inferred."
      : state.mode === "raw"
        ? "The direct splice preserves sensor differences and gaps for comparison. Month analysis still uses harmonized values. Raw S-NPP observations for 2012–2013 are unavailable here."
        : "Harmonized values share the VIIRS scale. Hover over or select a month with the keyboard to read its source.";
  renderMap();
  renderReading();
  renderCalendar();
  renderChart();
  setUrl();
}
function renderMap() {
  const data=state.subset?.data ?? state.region.rawData;
  const result=activityMap.update(data,state.target,color,state.subset?.bbox ?? null,state.region.name);
  $("#map-ramp").style.background=`linear-gradient(90deg,${color(0,result.max)},${color(result.max,result.max)})`;
  $("#map-max").textContent=count(result.max);
  $("#map-grid-status").textContent=result.cells ? `${state.target} · ${state.subset ? "Local" : "Regional"} color scale · ${sourceLabel[series().find(s=>s.month===state.target)?.source]??"Harmonized activity"}` : "Spatial data unavailable for this month";
  $("#map-cell-info").textContent="Hover over a cell to read its value and source. Colors rescale to the selected area and month; equal reds in different views need not mean equal counts. Detections are not fire severity. Light gray means zero; unshaded areas have no supplied cell.";
}
function renderReading() {
  const s = series().find((x) => x.month === state.target),
    a = anomaly(series(), state.target, date, state.baseline);
  const status = {
    no_data: "No data available",
    month_in_progress: "Month in progress",
    incomplete_coverage: "Incomplete coverage",
    no_history: "No historical reference",
    insufficient_history: "Not enough history",
    ok: {
      high: "Activity above normal",
      normal: "Activity within normal range",
      low: "Activity below normal",
    }[a.level],
  }[a.status];
  const uncertain =
    (state.subset ? state.subset.regions.some(r=>r.role==="holdout"||["BONA","BOAS","MIDE"].includes(r.name)) : state.region.role === "holdout" || ["BONA", "BOAS", "MIDE"].includes(state.region.name)) ||
    s.source === "model_terra_bridge";
  $("#reading").innerHTML =
    `<div class="value">${s.source === "snpp" && !state.subset ? "" : "<span>≈</span>"}${count(s.value)}</div><p class="unit">${s.source === "snpp" ? "Observed S-NPP detections" : "VIIRS-equivalent estimated detections"}</p><span class="source">${sourceLabel[s.source] ?? esc(s.source)}</span>${s.source === "noaa20_scaled" ? '<p class="source-note">This month uses NOAA-20 detections scaled to the S-NPP reference. Sensor continuity is uncertain; counts are not burned area or fire severity.</p>' : ""}${s.nrt ? '<span class="source provisional">Near-real-time · Subject to revision</span>' : ""}<div class="finding ${a.level ?? ""}"><h3>${status}</h3><p>${a.ratio != null ? `<strong>${a.ratio.toFixed(2)}×</strong> the historical same-month median` : a.notes.includes("small_median") ? "This month usually has very few detections." : a.status === "incomplete_coverage" ? "Missing coverage may affect the count. No anomaly is assigned." : a.status === "month_in_progress" ? "Showing detections so far. No anomaly is assigned." : "There is not enough reference data to assign an activity category."}</p>${a.percentile != null ? `<div class="percentile"><i style="left:${a.percentile}%"></i></div><div class="percentile-label"><span>Percentile: ${a.percentile.toFixed(1)}</span><span>${a.n_ref} reference years</span></div>` : ""}</div><div class="interval"><span>Model stability interval</span><strong>${s.lo != null && s.hi != null ? (s.source.startsWith("model") ? count(s.lo) + " – " + count(s.hi) : "No model interval for this month") : "Unavailable"}</strong><small>${s.source === "snpp" ? "Observed months do not use a model stability interval." : s.lo != null ? "Variation across resampled training years; not a guarantee of coverage." : "Intervals are not inferred from cell quantiles or samples."}</small></div>${uncertain ? '<p class="caution">Treat this region or source as low confidence. Do not use these values for precise risk assessment.</p>' : ""}`;
}
function color(v, max) {
  if (v == null) return "";
  const t = Math.log1p(Math.max(0, v)) / Math.log1p(max || 1);
  if(state.palette === "red") return `hsl(${6 - 5*t} ${74 + 8*t}% ${97 - 69*t}%)`;
  return state.palette === "mono" ? `hsl(210 5% ${96 - 78*t}%)` : `hsl(${178 + 24*t} ${30 + 25*t}% ${96 - 73*t}%)`;
}
function renderCalendar() {
  const rows = displayedSeries(),
    totals = new Map(annual(rows, state.mode).map(x => [x.year, x.value])),
    values = new Map(rows.map((s) => [s.month, s])),
    max = Math.max(1, ...rows.map((s) => s[state.mode] ?? 0));
  let html =
    '<span class="calendar-year"></span>' +
    months.map((m) => `<span class="calendar-month">${m}</span>`).join("") + '<span class="calendar-month">Annual total</span>';
  for (let y = +state.end.slice(0,4); y >= +state.start.slice(0,4); y--) {
    html += `<span class="calendar-year">${y}</span>`;
    for (let m = 1; m <= 12; m++) {
      const key = `${y}-${String(m).padStart(2, "0")}`,
        s = values.get(key),
        v = s?.[state.mode];
      html += `<button class="cell ${v == null ? "empty" : ""} ${key === state.target ? "selected" : ""}" ${v == null ? "disabled" : ""} data-month="${key}" style="${v == null ? "" : `background:${color(v, max)}`}" title="${key} · ${v == null ? "Unavailable" : count(v) + " · " + (sourceLabel[s.source] ?? s.source)}" aria-label="${key} ${v == null ? "Unavailable" : count(v) + " detections " + sourceLabel[s.source]}" aria-pressed="${key === state.target}" aria-current="${key === state.target ? "date" : "false"}"><span style="color:${v != null && Math.log1p(v)/Math.log1p(max) > .5 ? "white" : "#172f3b"}">${v == null ? "—" : count(v)}</span></button>`;
    }
    html += `<span class="annual-total" title="Requires 12 months with complete coverage">${count(totals.get(String(y)))}</span>`;
  }
  $("#calendar").innerHTML = html;
  $("#legend-max").textContent = count(max);
  $("#calendar-ramp").style.background = `linear-gradient(90deg, ${color(0,max)}, ${color(max,max)})`;
  $("#monthly-table").innerHTML = rows.map(s => `<tr><th scope="row">${s.month}</th><td>${count(s.value)}</td><td>${esc(sourceLabel[s.source] ?? s.source)}</td><td>${s.input_complete === false ? "Incomplete" : "Complete"}</td><td>${s.nrt ? "Near-real-time" : "Standard"}</td></tr>`).join("");
  $("#range-status").textContent = `${rows.length} supplied months · Annual totals require 12 complete months`;
  $$(".cell:not(:disabled)").forEach(
    (b) =>
      (b.onclick = () => {
        state.target = b.dataset.month;
        render();
        $(`#calendar [data-month="${state.target}"]`).focus();
      }),
  );
  $("#calendar").onkeydown = (event) => {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
    const cells = $$("#calendar .cell");
    const index = cells.indexOf(document.activeElement);
    if (index < 0) return;
    event.preventDefault();
    const offset = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -12, ArrowDown: 12 }[event.key];
    for (let next = index + offset; next >= 0 && next < cells.length; next += offset) {
      if (!cells[next].disabled) { cells[next].focus(); break; }
    }
  };
}
function renderChart() {
  const cal = state.target.slice(5),
    rows = displayedSeries().filter((s) => s.month.slice(5) === cal),
    max = Math.max(1, ...rows.map((s) => s[state.mode] ?? 0)),
    W = 460,
    H = 230;
  $("#chart-heading").textContent = `${months[+cal - 1]} across the years`;
  $("#chart-caption").textContent =
    state.mode === "raw"
      ? "Direct splice on original sensor scales"
      : "VIIRS-equivalent detections";
  const width = 380 / Math.max(rows.length, 1),
    bar = width * 0.65;
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Same-month detections across years"><line x1="48" x2="440" y1="190" y2="190" stroke="#b4c6cd"/><text x="42" y="24" text-anchor="end">${count(max)}</text><text x="42" y="194" text-anchor="end">0</text>`;
  rows.forEach((s, i) => {
    const v = s[state.mode],
      x = 55 + i * width,
      h = v == null ? 0 : (160 * v) / max;
    svg += `<g tabindex="${v == null ? -1 : 0}" role="button" aria-label="${s.month} ${count(v)} detections" data-month="${s.month}"><title>${s.month}: ${count(v)}</title><rect x="${x}" y="${190 - h}" width="${bar}" height="${Math.max(v == null ? 0 : 1, h)}" fill="${s.month === state.target ? "#d65836" : s.source === "snpp" ? "#478a89" : "#9ebbbb"}"/>${i % 5 === 0 || i === rows.length - 1 ? `<text x="${x + bar / 2}" y="214" text-anchor="middle">${s.month.slice(0, 4)}</text>` : ""}</g>`;
  });
  $("#chart").innerHTML = svg + "</svg>";
  $$("#chart g").forEach((g) => {
    g.onclick = () => {
      state.target = g.dataset.month;
      render();
    };
    g.onkeydown = (e) => {
      if (e.key === "Enter") g.onclick();
    };
  });
  $("#chart-note").textContent =
    "Dark teal: observed. Light teal: estimated or scaled. Orange: selected month. Missing values remain gaps.";
}
function save(blob, name) {
  const u = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = u;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(u), 5000);
}
$("#region").onchange = (e) => choose(e.target.value);
$("#target").onchange = (e) => {
  state.target = e.target.value;
  render();
};
$("#baseline").onchange = (e) => {
  state.baseline = e.target.value;
  renderReading();
  setUrl();
};
$("#harmonized").onclick = () => {
  state.mode = "value";
  render();
};
$("#raw").onclick = () => {
  state.mode = "raw";
  render();
};
$("#zoom-in").onclick = () => activityMap.zoomIn();
$("#zoom-out").onclick = () => activityMap.zoomOut();
$("#zoom-reset").onclick = () => activityMap.fit();
$("#zoom-all").onclick = () => activityMap.fit(false);
async function applyArea(bbox,month) {
  if(sample||!state.region)return;
  try { validateBounds(bbox); } catch(error) { $("#bbox-message").textContent=error.message; return; }
  const id=++loadId;
  activityMap.setDrawing(false);
  ["w","s","e","n"].forEach((k,i)=>{$(`#bbox-form [name=${k}]`).value=bbox[i];});
  state.busy=true; $("#workspace").setAttribute("aria-busy","true");
  try {
    const area=await loadArea(items,bbox,text=>{$("#bbox-message").textContent=text;},()=>id===loadId);
    if(!area||id!==loadId)return;
    state.subset=area;
    if(month&&area.series.some(s=>s.month===month))state.target=month;
    render();
    toast("Area applied. Map, calendar and monthly statistics now use your selection.");
  } catch(error) {
    if(id===loadId)$("#bbox-message").textContent=error.message+" Previous results are unchanged.";
  } finally {
    if(id===loadId){state.busy=false;$("#workspace").removeAttribute("aria-busy");}
  }
}
$("#bbox-form").onsubmit = event => {
  event.preventDefault();
  applyArea(["w","s","e","n"].map(k=>Number(new FormData(event.target).get(k))));
};
$("#draw-area").onclick=()=>activityMap.setDrawing(true);
$("#pan-map").onclick=()=>activityMap.setDrawing(false);
$("#chongqing-example").onclick=()=>applyArea([106,29,108,30.5],"2022-08");
$("#clear-box").onclick=()=>{
  ++loadId;state.busy=false;$("#workspace").removeAttribute("aria-busy");
  state.subset=null;activityMap.setDrawing(false);render();
};
$("#download-csv").onclick = () => {
  if (!state.region) return;
  save(
    new Blob([csv(displayedSeries(), state.subset ? `Custom area [${state.subset.bbox.join(",")}]` : currentLabel(), state.region.version)], {
      type: "text/csv;charset=utf-8",
    }),
    `inspiratio-${state.region.name}-${state.region.version}.csv`,
  );
  toast("Monthly CSV exported with source and quality flags.");
};
$("#download-image").onclick = () => {
  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  const lastYear = +state.end.slice(0,4), firstYear = +state.start.slice(0,4);
  canvas.height = 290 + (lastYear-firstYear+1)*34;
  const c = canvas.getContext("2d");
  c.fillStyle = "#f8fbfc";
  c.fillRect(0, 0, canvas.width, canvas.height);
  c.fillStyle = "#173948";
  c.font = "bold 34px sans-serif";
  c.fillText(currentLabel() + " / Monthly fire calendar", 45, 60, 990);
  c.font = "18px sans-serif";
  c.fillText(
    `${state.region.version} · ${state.mode === "raw" ? "Direct splice" : "VIIRS-equivalent"} · ${sample ? "Real same-month samples; blanks unavailable" : "Released data"} · ${date} UTC`,
    45,
    96,
    990,
  );
  const rows = displayedSeries(),
    max = Math.max(1, ...rows.map((s) => s[state.mode] ?? 0));
  months.forEach((m, i) => c.fillText(m, 133 + i * 73, 140));
  for (let y = lastYear; y >= firstYear; y--) {
    const py = 160 + (lastYear - y) * 34;
    c.fillStyle = "#173948";
    c.fillText(String(y), 45, py + 21);
    for (let m = 1; m <= 12; m++) {
      const s = rows.find(
          (s) => s.month === `${y}-${String(m).padStart(2, "0")}`,
        ),
        v = s?.[state.mode];
      c.fillStyle = v == null ? "#e6edef" : color(v, max);
      c.fillRect(125 + (m - 1) * 73, py, 65, 27);
    }
  }
  c.fillStyle = "#173948";
  c.fillText(
    "Regional log scale; light gray = unavailable. Detections are not individual fires.",
    45,
    canvas.height - 65,
    990,
  );
  c.fillText("Team Inspiratio · NASA FIRMS · Data: CC BY 4.0", 45, canvas.height - 25);
  canvas.toBlob((b) => save(b, `inspiratio-${state.region.name}-calendar.png`));
};
$("#share").onclick = async () => {
  try {
    await navigator.clipboard.writeText(location.href);
    toast("Link copied with the current region, month and reference period.");
  } catch {
    toast(
      "Copy the address bar to share this view. Your selection is saved in the URL.",
    );
  }
};
async function boot() {
  const result = await catalog();
  items = result.items;
  sample = result.sample;
  $("#region").innerHTML = '<option value="__custom" disabled hidden>Custom area</option>' + items
    .map((r) => `<option value="${esc(r.name)}">${esc(r.label)}</option>`)
    .join("");
  const params = new URLSearchParams(location.hash.slice(1));
  for (const key of ["start", "end"]) {
    const value = params.get(key);
    if (/^20\d{2}-(0[1-9]|1[0-2])$/.test(value) && value >= "2000-11" && value <= "2026-10") state[key] = value;
  }
  if (state.start > state.end) { state.start="2000-11"; state.end="2026-10"; }
  $("#range-start").value=state.start; $("#range-end").value=state.end;
  state.baseline = params.get("baseline") === "snpp" ? "snpp" : "all";
  $("#baseline").value = state.baseline;
  await choose(params.get("region") ?? "california", params.get("month"));
  if (params.has("bbox") && state.region?.rawData) {
    await applyArea(params.get("bbox").split(",").map(Number));
  }
}
function updateRange() {
  const start = $("#range-start").value, end = $("#range-end").value;
  if (!/^20\d{2}-(0[1-9]|1[0-2])$/.test(start) || !/^20\d{2}-(0[1-9]|1[0-2])$/.test(end) || start > end || start < "2000-11" || end > "2026-10") {
    $("#range-status").textContent = "Choose a valid range between November 2000 and October 2026.";
    $("#range-start").value=state.start; $("#range-end").value=state.end;
    return;
  }
  state.start=start; state.end=end;
  render();
}
$("#range-start").onchange=updateRange;
$("#range-end").onchange=updateRange;
$("#range-reset").onclick=()=>{ $("#range-start").value="2000-11"; $("#range-end").value="2026-10"; updateRange(); };
$("#values-toggle").onchange=e=>$("#calendar").classList.toggle("show-values",e.target.checked);
function applyPreferences() {
  state.palette=$("#color-assist").checked ? $("#palette").value : "red";
  $("#palette").disabled=!$("#color-assist").checked;
  for (const id of ["contrast","large-text","reduce-motion"]) document.documentElement.classList.toggle(id,$("#"+id).checked);
  try { localStorage.setItem("inspiratio-display",JSON.stringify({palette:state.palette,contrast:$("#contrast").checked,large:$("#large-text").checked,motion:$("#reduce-motion").checked})); } catch {}
  if(state.region) { renderCalendar(); renderMap(); renderChart(); }
}
try {
  const p=JSON.parse(localStorage.getItem("inspiratio-display") || "{}");
  $("#color-assist").checked=p.palette === "teal" || p.palette === "mono";
  $("#palette").value=p.palette === "mono" ? "mono" : "teal";
  $("#contrast").checked=!!p.contrast; $("#large-text").checked=!!p.large; $("#reduce-motion").checked=!!p.motion;
} catch {}
for(const id of ["color-assist","palette","contrast","large-text","reduce-motion"]) $("#"+id).onchange=applyPreferences;
applyPreferences();
boot().catch(() => {
  $("#notice").textContent =
    "The region catalog could not be loaded. Refresh the page to retry.";
});

for (const link of document.querySelectorAll(
  'a[href="#workspace"], a[href="#method"]',
)) {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    document.querySelector(link.getAttribute("href")).scrollIntoView({
      behavior: (document.documentElement.classList.contains("reduce-motion") || matchMedia("(prefers-reduced-motion: reduce)").matches)
        ? "instant"
        : "smooth",
    });
  });
}
