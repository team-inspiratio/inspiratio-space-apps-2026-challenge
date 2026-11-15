// Reference map layers: country, state/province and city names; state lines, rivers and lakes.
// Natural Earth (public domain), preprocessed into public/geo/*.json. Loaded lazily.
import { feature } from 'topojson-client'
import { geoArea, geoCentroid } from 'd3'
import countries from 'world-atlas/countries-110m.json'

const BASE = import.meta.env.BASE_URL

/** [name, lon, lat, rank] — lower rank is more important. */
export type LabelPt = { name: string; lon: number; lat: number; rank: number; country?: string; cap?: boolean }
export type Line = { rank: number; pts: Float32Array }

export const countryLabels: LabelPt[] = (() => {
  const fc = feature(countries as any, (countries as any).objects.countries) as any
  const out: LabelPt[] = []
  for (const f of fc.features) {
    const name = f.properties?.name
    if (!name || name === 'Antarctica') continue
    // Use the centroid of the largest polygon so France is labelled in France, not the Atlantic.
    const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates
    let best: any = null, area = 0
    for (const p of polys) {
      const g = { type: 'Polygon', coordinates: p }
      const a = geoArea(g as any)
      if (a > area && a < 6) ((area = a), (best = g))
    }
    if (!best) continue
    const [lon, lat] = geoCentroid(best)
    out.push({ name, lon, lat, rank: -area })
  }
  return out.sort((a, b) => a.rank - b.rank)
})()

export const geo = {
  places: [] as LabelPt[],
  admin1: [] as LabelPt[],
  admin1Lines: [] as Line[],
  rivers: [] as Line[],
  lakes: [] as Line[],
  ready: { points: false, lines: false },
}

let pointsP: Promise<void> | null = null
export function loadPoints() {
  return (pointsP ??= Promise.all([
    fetch(BASE + 'geo/places.json').then((r) => r.json()),
    fetch(BASE + 'geo/admin1.json').then((r) => r.json()),
  ]).then(([p, a]) => {
    geo.places = p.map((r: any[]) => ({ name: r[0], lon: r[1], lat: r[2], rank: r[3], country: r[4], cap: !!r[5] }))
    // One label per state or province (the source has extra points for islands and exclaves).
    const seen = new Set<string>()
    geo.admin1 = a
      .filter((r: any[]) => r[0])
      .map((r: any[]) => ({ name: r[0], lon: r[1], lat: r[2], rank: r[3], country: r[4] }))
      .sort((x: LabelPt, y: LabelPt) => x.rank - y.rank)
      .filter((p: LabelPt) => (seen.has(p.name + '|' + p.country) ? false : (seen.add(p.name + '|' + p.country), true)))
    geo.ready.points = true
  }))
}
let linesP: Promise<void> | null = null
export function loadLines() {
  const lines = (rows: any[]) => rows.map((r) => ({ rank: r[0], pts: Float32Array.from(r[1]) }))
  return (linesP ??= Promise.all(['admin1-lines', 'rivers', 'lakes'].map((n) => fetch(BASE + `geo/${n}.json`).then((r) => r.json()))).then(
    ([a, r, l]) => {
      geo.admin1Lines = lines(a)
      geo.rivers = lines(r)
      geo.lakes = lines(l)
      geo.ready.lines = true
    },
  ))
}

/** A short "where is this" for a box, e.g. "Georgia & South Carolina, United States". */
export function describe(b: [number, number, number, number]): string {
  if (!geo.ready.points) return ''
  const [w, s, e, n] = b
  const inside = geo.admin1.filter((p) => p.lon >= w && p.lon <= e && p.lat >= s && p.lat <= n)
  const cx = (w + e) / 2, cy = (s + n) / 2
  const pick = inside.length
    ? inside.sort((a, b) => a.rank - b.rank || Math.hypot(a.lon - cx, a.lat - cy) - Math.hypot(b.lon - cx, b.lat - cy)).slice(0, 2)
    : [...geo.admin1].sort((a, b) => Math.hypot(a.lon - cx, a.lat - cy) - Math.hypot(b.lon - cx, b.lat - cy)).slice(0, 1)
  if (!pick.length) return ''
  const countries = [...new Set(pick.map((p) => p.country).filter(Boolean))]
  const names = pick.length === 2 && pick[0].country === pick[1].country ? `${pick[0].name} & ${pick[1].name}` : pick[0].name
  return `${inside.length ? '' : 'near '}${names}${countries.length ? ', ' + countries.join(' / ') : ''}`
}
