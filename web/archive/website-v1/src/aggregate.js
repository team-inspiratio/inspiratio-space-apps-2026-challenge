import { area } from "@turf/area";
import { intersect } from "@turf/intersect";
import { polygon, featureCollection } from "@turf/helpers";
import { quantile } from "./anomaly.js";

export function cellPolygon(i, j, step = 0.25) {
  const s = -90 + i * step,
    w = -180 + j * step;
  return polygon([
    [
      [w, s],
      [w + step, s],
      [w + step, s + step],
      [w, s + step],
      [w, s],
    ],
  ]);
}

export function selectionWeights(data, selection) {
  // Fast bounding box rejection before polygon intersection.
  const all =
    selection.geometry.type === "Polygon"
      ? selection.geometry.coordinates.flat()
      : selection.geometry.coordinates.flat(2);
  const west = Math.min(...all.map((p) => p[0])),
    east = Math.max(...all.map((p) => p[0]));
  const south = Math.min(...all.map((p) => p[1])),
    north = Math.max(...all.map((p) => p[1]));
  const weights = [];
  data.cells.lat_idx.forEach((i, k) => {
    const j = data.cells.lon_idx[k],
      s = -90 + i * data.cell_deg,
      w = -180 + j * data.cell_deg;
    if (
      w >= east ||
      w + data.cell_deg <= west ||
      s >= north ||
      s + data.cell_deg <= south
    )
      return;
    const cell = cellPolygon(i, j, data.cell_deg),
      overlap = intersect(featureCollection([cell, selection]));
    if (overlap) {
      const weight = Math.min(1, area(overlap) / area(cell));
      if (weight > 1e-10) weights.push([k, weight]);
    }
  });
  return weights;
}

export function aggregateSelection(data, weights) {
  return data.months.map((month, t) => ({
    month,
    value: weights.length
      ? weights.reduce((s, [i, w]) => s + data.est[i][t] * w, 0)
      : null,
    input_complete: data.month_input_complete[t],
    source: data.month_source[t],
    nrt: data.month_nrt[t],
  }));
}

export function aggregateIntervals(data, weights, draws, n = 20, scale = 1) {
  const T = data.months.length;
  const low = [],
    high = [];
  for (let t = 0; t < T; t++) {
    const values = Array.from({ length: n }, (_, b) =>
      weights.reduce((s, [i, w]) => s + draws[(i * T + t) * n + b] * w, 0),
    ).sort((a, b) => a - b);
    const est = weights.reduce((s, [i, w]) => s + data.est[i][t] * w, 0);
    // Observed / NOAA-20 months have no model-resampling interval.
    const model = data.month_source[t].startsWith("model_");
    low.push(
      model ? Math.max(0, est - scale * (est - quantile(values, 0.05))) : est,
    );
    high.push(model ? est + scale * (quantile(values, 0.95) - est) : est);
  }
  return { lo_90: low, hi_90: high };
}
