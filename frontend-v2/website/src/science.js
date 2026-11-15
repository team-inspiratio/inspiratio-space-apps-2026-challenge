export const sourceLabel = {
  snpp: "VIIRS observation",
  noaa20_scaled: "Scaled NOAA-20",
  model_aqua: "MODIS model estimate",
  model_terra_bridge: "Terra bridge · Low confidence",
  mixed: "Mixed observation and estimate sources",
};
export function anomaly(series, target, as_of, baseline = "all") {
  if (!["all", "snpp"].includes(baseline)) throw Error("Unknown baseline");
  const out = {
    status: null,
    value: null,
    n_ref: 0,
    ref_years: [],
    median: null,
    ratio: null,
    percentile: null,
    level: null,
    preliminary: false,
    notes: [],
  };
  const t = series.find((s) => s.month === target);
  if (t?.value == null) {
    out.status = "no_data";
    return out;
  }
  out.value = t.value;
  out.preliminary = !!t.nrt;
  if (out.preliminary) out.notes.push("preliminary");
  const [y, m] = target.split("-").map(Number),
    next = `${y + (m === 12 ? 1 : 0)}-${String((m % 12) + 1).padStart(2, "0")}-01`;
  if (as_of < next) {
    out.status = "month_in_progress";
    return out;
  }
  if (t.input_complete === false) {
    out.status = "incomplete_coverage";
    out.notes.push("incomplete_coverage");
    return out;
  }
  const refs = series
    .filter(
      (s) =>
        +s.month.slice(0, 4) >= 2001 &&
        +s.month.slice(0, 4) < y &&
        s.month.slice(5) === target.slice(5) &&
        s.value != null &&
        s.input_complete !== false &&
        (baseline === "all" || s.source === "snpp"),
    )
    .sort((a, b) => a.month.localeCompare(b.month));
  out.n_ref = refs.length;
  out.ref_years = refs.map((s) => +s.month.slice(0, 4));
  if (!refs.length) {
    out.status = "no_history";
    return out;
  }
  const vals = refs.map((s) => s.value).sort((a, b) => a - b),
    n = vals.length;
  out.median = (vals[Math.floor((n - 1) / 2)] + vals[Math.floor(n / 2)]) / 2;
  out.percentile =
    (100 *
      (vals.filter((v) => v < t.value - 0.005).length +
        0.5 * vals.filter((v) => Math.abs(v - t.value) <= 0.005).length)) /
    n;
  if (out.median >= 5) out.ratio = t.value / out.median;
  else out.notes.push("small_median");
  if (n < 10) {
    out.status = "insufficient_history";
    out.notes.push("insufficient_history");
    return out;
  }
  out.status = "ok";
  out.level =
    out.percentile >= 90 ? "high" : out.percentile <= 10 ? "low" : "normal";
  return out;
}
export function releaseSeries(d) {
  if (
    !Array.isArray(d.months) ||
    !Array.isArray(d.totals?.est) ||
    d.months.length !== d.totals.est.length
  )
    throw Error("Data do not match the monthly series format.");
  return d.months.map((month, i) => ({
    month,
    value: d.totals.est[i],
    lo: d.totals.lo_90?.[i] ?? null,
    hi: d.totals.hi_90?.[i] ?? null,
    raw: d.totals.est_m0?.[i] ?? null,
    source: d.month_source[i],
    nrt: d.month_nrt[i],
    input_complete: d.month_input_complete[i],
  }));
}
import { longitudeParts } from "./geo.js";
const rad = (x) => (x * Math.PI) / 180;
export function boxWeight(lat, lon, bbox) {
  if (bbox[0] > bbox[2]) return longitudeParts(bbox).reduce((sum, part) => sum + boxWeight(lat, lon, part), 0);
  const [w, s, e, n] = bbox,
    a = Math.max(lon, w),
    b = Math.min(lon + 0.25, e),
    c = Math.max(lat, s),
    d = Math.min(lat + 0.25, n);
  return a >= b || c >= d
    ? 0
    : (((b - a) / 0.25) * (Math.sin(rad(d)) - Math.sin(rad(c)))) /
        (Math.sin(rad(lat + 0.25)) - Math.sin(rad(lat)));
}
export function validateBounds(bbox) {
  if (
    bbox.length !== 4 ||
    !bbox.every(Number.isFinite) ||
    bbox[0] === bbox[2] ||
    bbox[1] >= bbox[3] ||
    bbox[0] < -180 ||
    bbox[0] > 180 ||
    bbox[2] < -180 ||
    bbox[2] > 180 ||
    bbox[1] < -90 ||
    bbox[3] > 90
  )
    throw Error("Use longitudes from −180 to 180 and latitudes from −90 to 90. West and east must differ; south must be less than north.");
}
export function subset(d, bbox) {
  validateBounds(bbox);
  const weights = d.cells.lat_idx.map((v, i) =>
    boxWeight(v * 0.25 - 90, d.cells.lon_idx[i] * 0.25 - 180, bbox),
  );
  if (!weights.some((w) => w > 0))
    throw Error("This area does not overlap cells in the loaded region.");
  return releaseSeries(d).map((s, t) => ({
    ...s,
    value: weights.some((w,i) => w > 0 && d.est[i][t] == null) ? null : weights.reduce((v, w, i) => v + w * d.est[i][t], 0),
    lo: null,
    hi: null,
    raw: null,
    custom: true,
  }));
}
export function csv(series, region, version) {
  const fields = [
    "region",
    "version",
    "month",
    "value",
    "lo",
    "hi",
    "raw",
    "source",
    "input_complete",
    "nrt",
  ];
  const quote = (x) => '"' + String(x ?? "").replaceAll('"', '""') + '"';
  return (
    "\ufeff" +
    [
      fields.join(","),
      ...series.map((s) =>
        fields
          .map((k) =>
            quote(k === "region" ? region : k === "version" ? version : s[k]),
          )
          .join(","),
      ),
    ].join("\n")
  );
}
export function count(v) {
  return v == null ? "—" : Math.round(v).toLocaleString("en-US");
}
export function annual(series, key = "value") {
  const years = [...new Set(series.map((s) => s.month.slice(0, 4)))];
  return years.map((year) => {
    const rows = series.filter((s) => s.month.startsWith(year));
    return {
      year,
      value:
        rows.length === 12 &&
        rows.every((s) => s[key] != null && s.input_complete !== false)
          ? rows.reduce((a, s) => a + s[key], 0)
          : null,
    };
  });
}
