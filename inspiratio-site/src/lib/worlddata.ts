// 1° world grid for the overview map, built by prep/build_assets.py from the released parquet.
// Values are log-quantized to 0–254 against a global maximum; 255 marks "no direct-splice value".
const BASE = import.meta.env.BASE_URL

export type WorldGrid = {
  n: number
  T: number
  lat: Float32Array
  lon: Float32Array
  harm: Uint8Array
  raw: Uint8Array
  vmax: number
  index: Int32Array // [lat0 * 360 + lon0] -> cell, for hover lookups
}

export async function loadWorld(): Promise<WorldGrid> {
  const [meta, harm, raw] = await Promise.all([
    fetch(BASE + 'stage/cells.json').then((r) => r.json()),
    fetch(BASE + 'stage/harm.bin').then((r) => r.arrayBuffer()),
    fetch(BASE + 'stage/raw.bin').then((r) => r.arrayBuffer()),
  ])
  const n = meta.n
  const index = new Int32Array(180 * 360).fill(-1)
  const lat = Float32Array.from(meta.lat)
  const lon = Float32Array.from(meta.lon)
  for (let i = 0; i < n; i++) index[Math.floor(lat[i] + 90) * 360 + Math.floor(lon[i] + 180)] = i
  return { n, T: meta.months.length, lat, lon, harm: new Uint8Array(harm), raw: new Uint8Array(raw), vmax: meta.vmax, index }
}

/** Approximate detections for a quantized level (inverse of the prep encoding). */
export const levelToValue = (q: number, vmax: number) => Math.expm1((q / 254) * Math.log1p(vmax))
