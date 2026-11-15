// App state shared by the map, the place panel and the story.
// All science goes through the tested V2 modules in ./v2 (anomaly, subset, csv, area loading).
import { catalog, names } from './v2/data.js'
import { ask } from './loader'
import world from '../data/world.json'

export type Point = {
  month: string
  value: number | null
  lo: number | null
  hi: number | null
  raw: number | null
  source: string
  nrt: boolean
  input_complete: boolean
}
/** Cell arrays from the worker: est is flat [cell * T + month], NaN = no value. */
export type Cells = { lat: Float32Array; lon: Float32Array; est: Float32Array; T: number; vmax: number }
export type Place = {
  id: string
  kind: 'world' | 'region' | 'box'
  label: string
  sub: string
  bbox: [number, number, number, number] | null
  series: Point[]
  hasRaw: boolean
  lowConfidence: boolean
  cells: Cells | null
  /** Surrounding cells drawn faintly around a drawn area. */
  context?: Cells | null
}
export type Unit = { name: string; label: string; role: string; bbox: [number, number, number, number]; kind: string; file: string; cells: number; version: string }

/** Objects with a non-plain prototype are not proxied by Svelte's $state, so hot loops read them directly. */
class Plain {}
export const plain = <T extends object>(o: T): T => Object.setPrototypeOf(o, Plain.prototype) as T

export const MONTHS: string[] = world.months
export const LAST = MONTHS.length - 1
export const AS_OF = new Date().toISOString().slice(0, 10)
export const LOW_CONFIDENCE = new Set(['BOAS', 'BONA', 'MIDE', 'north_australia', 'central_siberia', 'indo_gangetic'])
export const HOLDOUT = new Set(['north_australia', 'central_siberia', 'indo_gangetic'])
export const CHONGQING: [number, number, number, number] = [106, 29, 108, 30.5]
/** A few reference places drawn on the map when zoomed in. */
export const LABELS = [
  { name: 'Chongqing', lon: 106.55, lat: 29.56 },
  { name: 'San Francisco', lon: -122.42, lat: 37.77 },
  { name: 'Los Angeles', lon: -118.24, lat: 34.05 },
  { name: 'Sacramento', lon: -121.49, lat: 38.58 },
  { name: 'Sydney', lon: 151.21, lat: -33.87 },
  { name: 'Melbourne', lon: 144.96, lat: -37.81 },
  { name: 'Canberra', lon: 149.13, lat: -35.28 },
]

export type Example = { label: string; note: string; month: string; region?: string; bbox?: [number, number, number, number]; name?: string }
export const EXAMPLES: Example[] = [
  { label: 'California', note: 'September 2020', month: '2020-09', region: 'california' },
  { label: 'South-east Australia', note: 'Black Summer, December 2019', month: '2019-12', bbox: [146, -38, 154, -28], name: 'South-east Australia' },
  { label: 'Chongqing', note: 'August 2022', month: '2022-08', bbox: [106, 29, 108, 30.5], name: 'Chongqing area' },
]
export function openExample(e: Example) {
  return e.region ? selectRegion(e.region, e.month) : selectBox(e.bbox!, e.month, e.name)
}

const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
export const monthName = (m: string, long = false) =>
  `${long ? ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][+m.slice(5) - 1] : MON[+m.slice(5) - 1]} ${m.slice(0, 4)}`
export const fmt = (v: number | null | undefined, digits = 0) =>
  v == null ? '—' : v.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits })
export const compact = (v: number) =>
  v >= 1e6 ? `${(v / 1e6).toFixed(1)} M` : v >= 1e4 ? `${Math.round(v / 1e3)} k` : fmt(v)

export const worldPlace: Place = plain({
  id: 'world',
  kind: 'world',
  label: 'World',
  sub: '14 GFED regions, holdout boxes excluded',
  bbox: null,
  hasRaw: true,
  lowConfidence: false,
  cells: null,
  series: world.months.map((month, i) => ({
    month,
    value: world.est[i],
    lo: null,
    hi: null,
    raw: world.est_m0[i],
    source: world.source[i],
    nrt: world.nrt[i],
    input_complete: world.input_complete[i],
  })),
})

export const app = $state({
  place: worldPlace as Place,
  loading: '' as string,
  error: '' as string,
  month: LAST,
  playing: false,
  mode: 'harm' as 'harm' | 'raw',
  proj: 'globe' as 'globe' | 'flat',
  /** Camera request: bumped whenever the map should re-frame. */
  frame: { seq: 0, bbox: null as [number, number, number, number] | null, proj: 'globe' as 'globe' | 'flat' },
  drawing: false,
  highlight: { sealed: false, sources: false, seam: false, cell: '' as string },
  step: 0,
  free: false,
  /** Set when the reader operates the tool; the story then leaves the current step alone. */
  touched: false,
  /** True while jumping to the explorer, so steps passed on the way are not applied. */
  skipping: false,
  units: [] as Unit[],
  /** 0 = opening screen, 1 = tool in place. Drives the opening camera and the chrome. */
  introP: 0,
  /** Screen space the map should keep clear of floating UI, in px. */
  insets: { left: 24, right: 24, top: 76, bottom: 110 },
  /** Optional play range: stop when the month reaches `to`. */
  play: { to: -1, speed: 12 },
  /** Timestamp of the last "flare" of all dots. */
  pulse: 0,
  /** 0..1: map dots flying into the MODIS–VIIRS scatter plot; curve draw-on progress. */
  scatter: 0,
  scatterCurve: 0,
  /** Selected date range (month indices, inclusive). */
  range: [0, 0] as [number, number],
  baseline: 'all' as 'all' | 'snpp',
  layer: 'fire' as 'fire' | 'anomaly',
  palette: 'fire' as 'fire' | 'cividis',
  /** The reader picked a place or drew a box during the story. */
  exploring: false,
  /** The reader chose the series themselves (not the story). */
  modeByUser: false,
})
app.range = [0, MONTHS.length - 1]

export function touch() {
  app.touched = true
}

/** The reader takes over during the story: the story stops steering until they ask for it back. */
export function beginExplore() {
  if (app.free) return
  app.exploring = true
  app.playing = false
  app.highlight = { sealed: false, sources: false, seam: false, cell: '' }
  if (!app.modeByUser) app.mode = 'harm'
}

let request = 0

export async function loadUnits() {
  const c = await catalog()
  app.units = (c.items as Unit[]).filter((u) => u.kind === 'region' || u.kind === 'box')
}

export function frame(bbox: Place['bbox'], proj: 'globe' | 'flat') {
  app.proj = proj
  app.frame = { seq: app.frame.seq + 1, bbox, proj }
}

export function selectWorld(opts: { reframe?: boolean } = {}) {
  request++
  app.place = worldPlace
  app.loading = ''
  app.error = ''
  if (opts.reframe !== false) frame(null, app.proj)
}

function hostOf(u: Unit) {
  const cx = (u.bbox[0] + u.bbox[2]) / 2, cy = (u.bbox[1] + u.bbox[3]) / 2
  return app.units.find((h) => h.kind === 'region' && !HOLDOUT.has(h.name) && h.bbox[0] <= cx && cx <= h.bbox[2] && h.bbox[1] <= cy && cy <= h.bbox[3])
}

/** Load (or warm) region files in the background so later moves need no parsing. */
export function prefetch(names_: string[]) {
  const units = names_.map((n) => app.units.find((u) => u.name === n)).filter(Boolean)
  return ask({ type: 'prefetch', units }).catch(() => {})
}

export async function selectRegion(name: string, month?: string) {
  const unit = app.units.find((u) => u.name === name)
  if (!unit) return
  const id = ++request
  app.loading = `Loading ${names[name as keyof typeof names] ?? name}…`
  app.error = ''
  try {
    const host = unit.kind === 'box' ? hostOf(unit) : undefined
    const r: any = await ask({ type: 'region', unit, host })
    if (id !== request) return
    app.place = plain({
      id: name,
      kind: 'region',
      label: names[name as keyof typeof names] ?? name,
      sub: `${HOLDOUT.has(name) ? 'Holdout region' : unit.kind === 'box' ? 'Demonstration region' : 'GFED region'} · ${fmt(r.cells.lat.length)} cells of 0.25°`,
      bbox: unit.bbox,
      series: r.series,
      hasRaw: r.series.some((s: Point) => s.raw != null),
      lowConfidence: LOW_CONFIDENCE.has(name),
      cells: r.cells,
      context: r.context,
    })
    if (month) app.month = MONTHS.indexOf(month)
    app.loading = ''
    frame(unit.bbox, 'flat')
  } catch (e) {
    if (id === request) {
      app.loading = ''
      app.error = String((e as Error).message ?? e)
    }
  }
}

export async function selectBox(bbox: [number, number, number, number], month?: string, name?: string) {
  const id = ++request
  app.error = ''
  app.loading = 'Loading area…'
  try {
    const units = app.units.filter((u) => u.kind === 'region')
    const r: any = await ask({ type: 'area', units, bbox })
    if (id !== request) return
    const [w, s, e, n] = bbox
    const deg = (v: number, pos: string, neg: string) => `${Math.abs(+v.toFixed(2))}°${v >= 0 ? pos : neg}`
    app.place = plain({
      id: `box:${bbox.join(',')}`,
      kind: 'box',
      label: name ?? (sameBox(bbox, CHONGQING) ? 'Chongqing area' : 'Custom area'),
      sub: `${deg(w, 'E', 'W')}–${deg(e, 'E', 'W')}, ${deg(s, 'N', 'S')}–${deg(n, 'N', 'S')} · ${fmt(r.cellCount)} cells`,
      bbox,
      series: r.series,
      hasRaw: r.hasRaw,
      lowConfidence: r.regions.some((x: any) => LOW_CONFIDENCE.has(x.name)),
      cells: r.cells,
      context: r.context,
    })
    if (month) app.month = MONTHS.indexOf(month)
    app.loading = ''
    frame(bbox, 'flat')
  } catch (e) {
    if (id === request) {
      app.loading = ''
      app.error = String((e as Error).message ?? e)
    }
  }
}

const sameBox = (a: number[], b: number[]) => a.every((v, i) => Math.abs(v - b[i]) < 1e-6)

/** Shareable state in the URL hash. */
export function hashState() {
  const p = app.place
  const parts = [`m=${MONTHS[app.month]}`, `mode=${app.mode}`]
  if (app.range[0] > 0 || app.range[1] < LAST) parts.push(`from=${MONTHS[app.range[0]]}`, `to=${MONTHS[app.range[1]]}`)
  if (p.kind === 'region') parts.unshift(`place=${p.id}`)
  if (p.kind === 'box' && p.bbox) parts.unshift(`box=${p.bbox.join(',')}`)
  return '#' + parts.join('&')
}

export async function restoreHash(): Promise<boolean> {
  const h = new URLSearchParams(location.hash.slice(1))
  if (![...h.keys()].length) return false
  const m = h.get('m')
  if (m && MONTHS.includes(m)) app.month = MONTHS.indexOf(m)
  if (h.get('mode') === 'raw') app.mode = 'raw'
  const from = MONTHS.indexOf(h.get('from') ?? ''), to = MONTHS.indexOf(h.get('to') ?? '')
  if (from >= 0 && to >= from) app.range = [from, to]
  const box = h.get('box')?.split(',').map(Number)
  if (box?.length === 4 && box.every(Number.isFinite)) await selectBox(box as [number, number, number, number], m ?? undefined)
  else if (h.get('place')) await selectRegion(h.get('place')!, m ?? undefined)
  return true
}

export { names }
