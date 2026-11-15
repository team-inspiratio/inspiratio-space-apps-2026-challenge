// Background loading: download, decompress and parse region files and 0.25° tiles off the main thread,
// so camera moves never stall. All science still goes through the tested V2 functions.
import { releaseSeries, subset, boxWeight } from './v2/science.js'
import { createAreaCollector, areaCandidates } from './v2/area.js'

const BASE = (self as any).__base ?? '/'
type Unit = { name: string; file: string; bbox: number[]; kind: string }

async function gunzipBytes(r: Response) {
  const bytes = new Uint8Array(await r.arrayBuffer())
  // Some hosts decompress .gz transparently: inspect the bytes, not the name.
  if (bytes[0] === 31 && bytes[1] === 139)
    return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer())
  return bytes
}

const regions = new Map<string, any>()
async function region(u: Unit) {
  if (regions.has(u.name)) {
    const v = regions.get(u.name)
    regions.delete(u.name)
    regions.set(u.name, v)
    return v
  }
  const r = await fetch(BASE + 'data/global-v1/' + u.file.split('/').pop())
  if (!r.ok) throw Error('Data for this region are unavailable. Please retry.')
  const d = JSON.parse(new TextDecoder().decode(await gunzipBytes(r)))
  const v = { ...u, rawData: d, series: releaseSeries(d) }
  regions.set(u.name, v)
  while (regions.size > 4) regions.delete(regions.keys().next().value!)
  return v
}

type Tile = { idx: Uint16Array; harm: Uint8Array; raw: Uint16Array; n: number; T: number }
const tiles = new Map<string, Tile>()
async function tile(ty: number, tx: number): Promise<Tile | null> {
  const key = `${ty}_${tx}`
  if (tiles.has(key)) return tiles.get(key)!
  const r = await fetch(BASE + `tiles/${key}.bin.gz`)
  if (!r.ok) return null
  const b = await gunzipBytes(r)
  const dv = new DataView(b.buffer, b.byteOffset, b.byteLength)
  const n = dv.getUint32(4, true), T = dv.getUint32(8, true)
  let o = 12
  const idx = new Uint16Array(b.buffer.slice(b.byteOffset + o, b.byteOffset + o + n * 2))
  o += n * 2
  const harm = new Uint8Array(b.buffer.slice(b.byteOffset + o, b.byteOffset + o + n * T))
  o += n * T
  if (o % 2) o++
  const raw = new Uint16Array(b.buffer.slice(b.byteOffset + o, b.byteOffset + o + n * T * 2))
  const t = { idx, harm, raw, n, T }
  tiles.set(key, t)
  while (tiles.size > 80) tiles.delete(tiles.keys().next().value!)
  return t
}

/** Flatten a region's cells into typed arrays: est is n*T with NaN for "no value". */
function flatCells(lat_idx: number[], lon_idx: number[], est: (number | null)[][]) {
  const n = lat_idx.length, T = est[0]?.length ?? 0
  const lat = new Float32Array(n), lon = new Float32Array(n), e = new Float32Array(n * T)
  const sample: number[] = []
  for (let i = 0; i < n; i++) {
    lat[i] = lat_idx[i] * 0.25 - 90
    lon[i] = lon_idx[i] * 0.25 - 180
    const row = est[i]
    for (let t = 0; t < T; t++) {
      const v = row[t]
      e[i * T + t] = v == null ? NaN : v
      if (v && i % 7 === 0) sample.push(v)
    }
  }
  sample.sort((a, b) => a - b)
  const vmax = Math.max(1, sample.length ? sample[Math.floor(sample.length * 0.995)] : 1)
  return { lat, lon, est: e, T, vmax }
}
const transfer = (c: ReturnType<typeof flatCells>) => [c.lat.buffer, c.lon.buffer, c.est.buffer]

/** Direct-splice series for any box, from the exact 0.25° tile counts, with subset()'s area weights and null rule. */
async function boxRaw(bbox: number[], T: number) {
  const out: (number | null)[] = new Array(T).fill(0)
  const nullAt = new Uint8Array(T)
  const parts = bbox[0] > bbox[2] ? [[bbox[0], bbox[1], 180, bbox[3]], [-180, bbox[1], bbox[2], bbox[3]]] : [bbox]
  let any = false
  for (const [w, s, e, n] of parts) {
    for (let ty = Math.floor((s + 90) / 10); ty <= Math.min(17, Math.floor((n + 90 - 1e-9) / 10)); ty++)
      for (let tx = Math.floor((w + 180) / 10); tx <= Math.min(35, Math.floor((e + 180 - 1e-9) / 10)); tx++) {
        const t = await tile(ty, tx)
        if (!t) continue
        for (let i = 0; i < t.n; i++) {
          const lat = (ty * 40 + Math.floor(t.idx[i] / 40)) * 0.25 - 90
          const lon = (tx * 40 + (t.idx[i] % 40)) * 0.25 - 180
          const wgt = boxWeight(lat, lon, bbox)
          if (wgt <= 0) continue
          any = true
          for (let m = 0; m < T; m++) {
            const v = t.raw[i * T + m]
            if (v === 65535) nullAt[m] = 1
            else (out[m] as number) += wgt * v
          }
        }
      }
  }
  return any ? out.map((v, m) => (nullAt[m] ? null : v)) : out.map(() => null)
}

self.onmessage = async (ev: MessageEvent) => {
  const { id, type } = ev.data
  try {
    if (type === 'base') {
      ;(self as any).__base = ev.data.base
      return
    }
    if (type === 'region') {
      const u: Unit = ev.data.unit
      const r = await region(u)
      const d = r.rawData
      const cells = flatCells(d.cells.lat_idx, d.cells.lon_idx, d.est)
      let context = null
      if (ev.data.host) {
        const h = await region(ev.data.host)
        context = flatCells(h.rawData.cells.lat_idx, h.rawData.cells.lon_idx, h.rawData.est)
      }
      ;(self as any).postMessage(
        { id, ok: true, series: r.series, cells, context },
        [...transfer(cells), ...(context ? transfer(context) : [])],
      )
    } else if (type === 'area') {
      const { units, bbox } = ev.data
      const cands = areaCandidates(units, bbox)
      const col = createAreaCollector(bbox)
      for (const u of cands) col.add(await region(u))
      const res = col.finish()
      const T = res.data.months.length
      const raw = await boxRaw(bbox, T)
      const series = res.series.map((s: any, i: number) => ({ ...s, raw: raw[i] }))
      const cells = flatCells(res.data.cells.lat_idx, res.data.cells.lon_idx, res.data.est)
      const host = cands[0] ? await region(cands[0]) : null
      const context = host ? flatCells(host.rawData.cells.lat_idx, host.rawData.cells.lon_idx, host.rawData.est) : null
      ;(self as any).postMessage(
        { id, ok: true, series, cells, context, regions: res.regions, cellCount: res.cellCount, hasRaw: raw.some((v) => v != null) },
        [...transfer(cells), ...(context ? transfer(context) : [])],
      )
    } else if (type === 'tile') {
      const t = await tile(ev.data.ty, ev.data.tx)
      if (!t) return (self as any).postMessage({ id, ok: true, tile: null })
      // Copy so the cache keeps its own buffers.
      const c = { idx: t.idx.slice(), harm: t.harm.slice(), raw: t.raw.slice(), n: t.n, T: t.T }
      ;(self as any).postMessage({ id, ok: true, tile: c }, [c.idx.buffer, c.harm.buffer, c.raw.buffer])
    } else if (type === 'prefetch') {
      for (const u of ev.data.units as Unit[]) await region(u).catch(() => {})
      ;(self as any).postMessage({ id, ok: true })
    }
  } catch (e) {
    ;(self as any).postMessage({ id, ok: false, error: String((e as Error)?.message ?? e) })
  }
}

// Keep imports referenced for bundlers that tree-shake aggressively.
void subset
