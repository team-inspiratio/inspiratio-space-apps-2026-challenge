// Promise wrapper around the data worker.
import Worker from './data.worker?worker'

const w = new Worker()
w.postMessage({ type: 'base', base: new URL(import.meta.env.BASE_URL, location.href).href })
let seq = 0
const pending = new Map<number, { res: (v: any) => void; rej: (e: Error) => void }>()
w.onmessage = (ev) => {
  const p = pending.get(ev.data.id)
  if (!p) return
  pending.delete(ev.data.id)
  ev.data.ok ? p.res(ev.data) : p.rej(Error(ev.data.error))
}
export function ask<T = any>(msg: Record<string, unknown>): Promise<T> {
  const id = ++seq
  return new Promise((res, rej) => {
    pending.set(id, { res, rej })
    w.postMessage({ ...JSON.parse(JSON.stringify(msg)), id })
  })
}

export type Tile = { idx: Uint16Array; harm: Uint8Array; raw: Uint16Array; n: number; T: number }
const tileCache = new Map<string, Tile | null>()
const tileWaiting = new Set<string>()
/** Returns a tile if cached; otherwise starts loading it and returns undefined. */
export function getTile(ty: number, tx: number, onReady: () => void): Tile | null | undefined {
  const k = `${ty}_${tx}`
  if (tileCache.has(k)) return tileCache.get(k)
  if (!tileWaiting.has(k)) {
    tileWaiting.add(k)
    ask<{ tile: Tile | null }>({ type: 'tile', ty, tx })
      .then((r) => {
        tileCache.set(k, r.tile)
        while (tileCache.size > 120) tileCache.delete(tileCache.keys().next().value!)
        onReady()
      })
      .catch(() => tileCache.set(k, null))
      .finally(() => tileWaiting.delete(k))
  }
  return undefined
}
export let tileIndex: { vmax: number; tiles: { ty: number; tx: number }[] } | null = null
fetch(import.meta.env.BASE_URL + 'tiles/index.json')
  .then((r) => r.json())
  .then((j) => (tileIndex = j))
