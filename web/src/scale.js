// Calendar colour scale. Pure functions so they can be unit-tested in Node.
// The ramp spans the 5th–99th percentile of the current area's positive monthly
// values on a log axis, so the full light-to-dark range is always used: seasons
// and big fire years stand out instead of everything sitting in one shade.
import { quantile } from "./anomaly.js";

// Light → dark, one hue family (yellow-green → teal → navy). Zero has its own neutral fill.
export const RAMP = [
  "#dce4a9",
  "#b8d677",
  "#7fbe67",
  "#4c9e72",
  "#2b7f78",
  "#286272",
  "#29495e",
  "#28394d",
];
export const ZERO_COLOR = "#f1f0e8";

const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const STOPS = RAMP.map(hex);

/** Colour at position t in [0, 1] along RAMP (linear between stops). */
export function rampColor(t) {
  const x = Math.min(1, Math.max(0, t)) * (STOPS.length - 1),
    i = Math.min(STOPS.length - 2, Math.floor(x)),
    f = x - i;
  const c = STOPS[i].map((a, k) => Math.round(a + f * (STOPS[i + 1][k] - a)));
  return "#" + c.map((v) => v.toString(16).padStart(2, "0")).join("");
}

/**
 * Log scale fitted to the lo/hi percentiles of the positive, finite values.
 * Values at or below the lo percentile get the lightest ramp colour, values at
 * or above the hi percentile the darkest. 0 → ZERO_COLOR, null → null.
 */
export function logPercentileScale(values, lo = 0.05, hi = 0.99) {
  const positive = values
    .filter((v) => v != null && Number.isFinite(v) && v > 0)
    .sort((a, b) => a - b);
  if (!positive.length)
    return {
      lo: null,
      hi: null,
      position: (v) => (v == null ? null : 0),
      color: (v) => (v == null ? null : ZERO_COLOR),
    };
  let a = quantile(positive, lo),
    b = quantile(positive, hi);
  if (!(b > a)) b = a * 10; // flat series: keep a non-zero span
  const la = Math.log(a),
    span = Math.log(b) - la;
  const position = (v) => {
    if (v == null || !Number.isFinite(v)) return null;
    if (v <= 0) return 0;
    return Math.min(1, Math.max(0, (Math.log(v) - la) / span));
  };
  return {
    lo: a,
    hi: b,
    position,
    color: (v) =>
      v == null || !Number.isFinite(v)
        ? null
        : v <= 0
          ? ZERO_COLOR
          : rampColor(position(v)),
  };
}

/** CSS gradient that matches RAMP exactly, for legends. */
export const rampGradient = (dir = "90deg") =>
  `linear-gradient(${dir}, ${RAMP.map((c, i) => `${c} ${((100 * i) / (RAMP.length - 1)).toFixed(1)}%`).join(", ")})`;
