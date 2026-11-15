// The month's 0.25° grid as ONE canvas layer instead of ~1,600 Leaflet rectangles,
// each with its own tooltip. Building, projecting and wiring that many layer
// objects on every region or month change is what made switching slow; here a
// redraw is a single loop of fillRect calls and hover is an index lookup.

/** Cell index for a point, or -1. `index` maps lat_idx * 1440 + lon_idx → k. */
export function cellAt(lat, lng, index, deg = 0.25) {
  const i = Math.floor((lat + 90) / deg),
    j = Math.floor((lng + 180) / deg);
  return index.get(i * Math.round(360 / deg) + j) ?? -1;
}
export const cellIndex = (cells, deg = 0.25) =>
  new Map(
    cells.lat_idx.map((i, k) => [i * Math.round(360 / deg) + cells.lon_idx[k], k]),
  );

/** Leaflet layer factory (L passed in so this module stays importable in Node tests). */
export function createCellLayer(L, { pad = 0.4, opacity = 0.82 } = {}) {
  const Layer = L.Layer.extend({
    initialize() {
      this._cells = null;
    },
    onAdd(map) {
      this._canvas = L.DomUtil.create("canvas", "cell-layer leaflet-zoom-hide");
      this._canvas.style.pointerEvents = "none";
      this._canvas.style.opacity = opacity;
      map.getPanes().overlayPane.appendChild(this._canvas);
      map.on("moveend zoomend resize viewreset", this._redraw, this);
      this._redraw();
    },
    onRemove(map) {
      map.off("moveend zoomend resize viewreset", this._redraw, this);
      this._canvas.remove();
    },
    /** cells: {lat: Float32Array(south edges), lng: Float32Array(west edges), color: string[], deg} */
    setCells(cells) {
      this._cells = cells;
      this._redraw();
      return this;
    },
    _redraw() {
      const map = this._map;
      if (!map || !this._canvas) return;
      const size = map.getSize(),
        dpr = window.devicePixelRatio || 1,
        off = size.multiplyBy(pad).round(),
        w = size.x + 2 * off.x,
        h = size.y + 2 * off.y,
        c = this._canvas;
      const origin = map.containerPointToLayerPoint([0, 0]).subtract(off);
      L.DomUtil.setPosition(c, origin);
      c.style.width = w + "px";
      c.style.height = h + "px";
      if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) {
        c.width = Math.round(w * dpr);
        c.height = Math.round(h * dpr);
      }
      const ctx = c.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const cells = this._cells;
      if (!cells) return;
      const deg = cells.deg;
      for (let k = 0; k < cells.color.length; k++) {
        const fill = cells.color[k];
        if (!fill) continue;
        // Project the two corners (Web Mercator: cell height varies with latitude).
        const a = map.latLngToLayerPoint([cells.lat[k] + deg, cells.lng[k]]),
          b = map.latLngToLayerPoint([cells.lat[k], cells.lng[k] + deg]);
        const x0 = a.x - origin.x,
          y0 = a.y - origin.y,
          x1 = b.x - origin.x,
          y1 = b.y - origin.y;
        if (x1 < 0 || y1 < 0 || x0 > w || y0 > h) continue;
        ctx.fillStyle = fill;
        // Half-pixel overlap avoids hairline seams between neighbouring cells.
        ctx.fillRect(x0, y0, x1 - x0 + 0.5, y1 - y0 + 0.5);
      }
    },
  });
  return new Layer();
}
