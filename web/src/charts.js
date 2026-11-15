// Small SVG chart helpers for the method page, drawn in the site's style at the
// container's real pixel width (so text stays legible on phones). Every mark
// that carries a value gets a data-tip; methods.js shows it in the shared tooltip.
export const COLORS = {
  harmonized: "#2b7a5f", // harmonized / LightGBM E028
  splice: "#c18145", // direct splice / M0
  aqua: "#d3ad84", // Aqua MODIS as recorded (dashed)
  viirs: "#2c3e50", // observed VIIRS / grader truth
  m1s: "#8a6fb8", // ratio baseline
  qm: "#9aa093", // quantile mapping
  band: "#cfe3d4",
  rule: "#a36449",
};
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
export const tipAttr = (html) => `data-tip="${esc(html)}"`;

export function linearScale([d0, d1], [r0, r1]) {
  const k = (r1 - r0) / (d1 - d0 || 1);
  const f = (v) => r0 + (v - d0) * k;
  f.invert = (p) => d0 + (p - r0) / k;
  return f;
}
export function logScale([d0, d1], [r0, r1]) {
  const a = Math.log10(d0),
    k = (r1 - r0) / (Math.log10(d1) - a);
  return (v) => r0 + (Math.log10(Math.max(v, d0)) - a) * k;
}
export function niceStep(v) {
  const p = 10 ** Math.floor(Math.log10(v)),
    m = v / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p;
}
export const compact = (n) =>
  new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);

/** Linear y axis with ~4 gridlines; returns {y, max, svg}. */
export function yAxisLinear({ max, top, bottom, left, right, fmt = compact, min = 0 }) {
  const step = niceStep((max - min) / 4),
    hi = Math.ceil(max / step) * step,
    lo = Math.floor(min / step) * step,
    y = linearScale([lo, hi], [bottom, top]);
  let svg = "";
  for (let v = lo; v <= hi + step / 2; v += step)
    svg += `<line class="grid" x1="${left}" x2="${right}" y1="${y(v)}" y2="${y(v)}"/><text class="tick" x="${left - 8}" y="${y(v) + 4}" text-anchor="end">${fmt(+v.toFixed(6))}</text>`;
  return { y, max: hi, min: lo, svg };
}
/** Log10 y axis with decade gridlines. */
export function yAxisLog({ lo, hi, top, bottom, left, right }) {
  const y = logScale([lo, hi], [bottom, top]);
  let svg = "";
  for (let v = lo; v <= hi * 1.0001; v *= 10)
    svg += `<line class="grid" x1="${left}" x2="${right}" y1="${y(v)}" y2="${y(v)}"/><text class="tick" x="${left - 8}" y="${y(v) + 4}" text-anchor="end">${compact(v)}</text>`;
  return { y, svg };
}
export const open = (w, h, label) =>
  `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${esc(label)}">`;

/** Path through points; null y breaks the line. */
export function path(points) {
  let d = "",
    on = false;
  for (const [x, y] of points) {
    if (y == null || !Number.isFinite(y)) {
      on = false;
      continue;
    }
    d += `${on ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
    on = true;
  }
  return d;
}
/** Filled band between lo and hi; null breaks it into segments. */
export function band(points) {
  const segs = [];
  let cur = [];
  for (const p of points) {
    if (p[1] == null || p[2] == null) {
      if (cur.length) segs.push(cur);
      cur = [];
    } else cur.push(p);
  }
  if (cur.length) segs.push(cur);
  return segs
    .map(
      (s) =>
        "M" +
        s.map(([x, lo]) => `${x.toFixed(1)},${lo.toFixed(1)}`).join("L") +
        "L" +
        [...s]
          .reverse()
          .map(([x, , hi]) => `${x.toFixed(1)},${hi.toFixed(1)}`)
          .join("L") +
        "Z",
    )
    .join("");
}

/**
 * Grouped vertical bars. groups: [{label, values: {key: v}, tips?: {key: html}}];
 * keys: [{key, label, color}]. Bars are 4px-rounded at the data end, 2px apart.
 */
export function groupedBars({
  width,
  height = 240,
  groups,
  keys,
  max,
  fmt = compact,
  label,
  valueLabels = false,
  pad = { l: 46, r: 8, t: 14, b: 34 },
  ref,
  min = 0,
}) {
  const ax = yAxisLinear({
      max: max ?? Math.max(...groups.flatMap((g) => keys.map((k) => g.values[k.key] ?? 0))),
      min,
      top: pad.t,
      bottom: height - pad.b,
      left: pad.l,
      right: width - pad.r,
      fmt,
    }),
    gw = (width - pad.l - pad.r) / groups.length,
    inner = Math.min(gw * 0.78, keys.length * 34),
    bw = (inner - 2 * (keys.length - 1)) / keys.length;
  let svg = open(width, height, label) + ax.svg;
  if (ref)
    svg += `<line class="ref" x1="${pad.l}" x2="${width - pad.r}" y1="${ax.y(ref.value)}" y2="${ax.y(ref.value)}"/>${ref.label ? `<text class="ref-label" x="${width - pad.r}" y="${ax.y(ref.value) - 5}" text-anchor="end">${esc(ref.label)}</text>` : ""}`;
  groups.forEach((g, i) => {
    const x0 = pad.l + i * gw + (gw - inner) / 2;
    keys.forEach((k, j) => {
      const v = g.values[k.key];
      if (v == null) return;
      const x = x0 + j * (bw + 2),
        y0 = ax.y(Math.max(ax.min, 0)),
        y1 = ax.y(v),
        h = Math.max(0.5, y0 - y1),
        r = Math.min(4, bw / 2, h);
      svg += `<path class="bar" fill="${k.color}" d="M${x},${y0}V${y1 + r}Q${x},${y1} ${x + r},${y1}H${x + bw - r}Q${x + bw},${y1} ${x + bw},${y1 + r}V${y0}Z" ${tipAttr(g.tips?.[k.key] ?? `<strong>${esc(g.label)}</strong><span>${esc(k.label)}: ${fmt(v)}</span>`)}/>`;
      if (valueLabels)
        svg += `<text class="value" x="${x + bw / 2}" y="${y1 - 5}" text-anchor="middle">${fmt(v)}</text>`;
    });
    svg += `<text class="tick x" x="${pad.l + i * gw + gw / 2}" y="${height - pad.b + 16}" text-anchor="middle">${esc(g.label)}</text>`;
    if (g.sublabel)
      svg += `<text class="tick x sub" x="${pad.l + i * gw + gw / 2}" y="${height - pad.b + 29}" text-anchor="middle">${esc(g.sublabel)}</text>`;
  });
  svg += `<line class="axis" x1="${pad.l}" x2="${width - pad.r}" y1="${ax.y(Math.max(ax.min, 0))}" y2="${ax.y(Math.max(ax.min, 0))}"/>`;
  return svg + "</svg>";
}

/** Legend row (HTML). items: [{label, color, kind: "line"|"dash"|"bar"|"dot"|"band"}] */
export const legend = (items) =>
  `<div class="fig-legend">${items
    .map(
      (it) =>
        `<span><i class="lg-${it.kind || "bar"}" style="--c:${it.color}"></i>${esc(it.label)}</span>`,
    )
    .join("")}</div>`;
