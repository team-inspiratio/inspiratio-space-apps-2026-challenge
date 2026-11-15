<script lang="ts">
  import { onMount } from 'svelte'
  import { gsap } from 'gsap'
  import {
    geoProjection,
    geoOrthographicRaw,
    geoEqualEarthRaw,
    geoOrthographic,
    geoEqualEarth,
    geoPath,
    geoGraticule10,
    interpolate,
    easeCubicInOut,
    easeCubicOut,
  } from 'd3'
  import { feature, mesh } from 'topojson-client'
  import countries from 'world-atlas/countries-110m.json'
  import scatterData from '../data/scatter.json'
  import { app, MONTHS, fmt, monthName, selectBox, touch, beginExplore } from '../lib/store.svelte'
  import { type WorldGrid, levelToValue } from '../lib/worlddata'
  import { LUT, setPalette, anomalyColor } from '../lib/ramp'
  import { getTile, tileIndex, type Tile } from '../lib/loader'
  import { geo, countryLabels, loadPoints, loadLines } from '../lib/geo'
  import Icon from './Icon.svelte'

  let { world }: { world: WorldGrid } = $props()

  type Cam = { t: number; rot: [number, number]; scale: number; tx: number; ty: number }
  type BBox = [number, number, number, number]
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
  const DPR = Math.min(2, devicePixelRatio || 1)
  // Adaptive sharpness: if this machine struggles (no GPU, slow CPU), the sharp layer uses fewer pixels.
  let hiQ = DPR
  let slowFrames = 0, sampled = 0
  let slowMachine = false
  let drewLast = false

  let wrap: HTMLDivElement
  let canvas: HTMLCanvasElement
  let mainCtx: CanvasRenderingContext2D
  // Two fixed render layers, never resized during motion: sharp (device pixels) and light (1x).
  type Layer = {
    cv: HTMLCanvasElement; ctx: CanvasRenderingContext2D; base: HTMLCanvasElement; bctx: CanvasRenderingContext2D; q: number; key: string; cam: Cam | null
    lab: HTMLCanvasElement; lctx: CanvasRenderingContext2D; lkey: string; lcam: Cam | null
  }
  let hi: Layer, lo: Layer
  let ctx: CanvasRenderingContext2D
  let base: HTMLCanvasElement
  let bctx: CanvasRenderingContext2D
  let drawCv: HTMLCanvasElement
  let L: Layer
  let W = 800, H = 600
  let q = DPR // current backing-store scale: 1 while moving, DPR at rest
  let cam: Cam = { t: 0, rot: [-20, -18], scale: 250, tx: 400, ty: 300 }
  let anim: { from: Cam; to: Cam; start: number; dur: number; arc: number } | null = null
  let dirty = true
  let spinning = true
  let userCam = false
  let lastMove = -1e9
  let tip = $state<{ x: number; y: number; html: string } | null>(null)
  let band: BBox | null = null
  let fontFamily = 'system-ui'

  // ---------- geography ----------
  type Part = { b: [number, number, number, number]; c: any }
  type Geo = { land: any; borders: any; landParts: Part[]; borderParts: Part[] }
  function bboxOf(coords: any, depth: number): [number, number, number, number] {
    let w = 180, s_ = 90, e = -180, n = -90
    const walk = (c: any, d: number) => {
      if (d === 0) {
        if (c[0] < w) w = c[0]
        if (c[0] > e) e = c[0]
        if (c[1] < s_) s_ = c[1]
        if (c[1] > n) n = c[1]
      } else for (const x of c) walk(x, d - 1)
    }
    walk(coords, depth)
    return [w, s_, e, n]
  }
  function makeGeo(topo: any): Geo {
    const land = feature(topo, topo.objects.land) as any
    const borders = mesh(topo, topo.objects.countries, (a: any, b: any) => a !== b) as any
    const lg = land.features ? land.features[0].geometry : land.geometry
    const polys = lg.type === 'Polygon' ? [lg.coordinates] : lg.coordinates
    const lines = borders.type === 'LineString' ? [borders.coordinates] : borders.coordinates
    return {
      land,
      borders,
      landParts: polys.map((c: any) => ({ b: bboxOf(c, 2), c })),
      borderParts: lines.map((c: any) => ({ b: bboxOf(c, 1), c })),
    }
  }
  /** Only the parts that overlap the view (with a margin); whole geometry when the view is wide. */
  function visibleGeo(g: Geo): { land: any; borders: any } {
    const vb = viewBounds()
    if (!vb) return g
    const m = 2
    const hit = (b: number[]) => b[2] >= vb.w - m && b[0] <= vb.e + m && b[3] >= vb.s - m && b[1] <= vb.n + m
    return {
      land: { type: 'MultiPolygon', coordinates: g.landParts.filter((p) => hit(p.b)).map((p) => p.c) },
      borders: { type: 'MultiLineString', coordinates: g.borderParts.filter((p) => hit(p.b)).map((p) => p.c) },
    }
  }
  const coarse = makeGeo(countries)
  let fine: Geo | null = null
  let finest: Geo | null = null
  let loadingGeo = { fine: false, finest: false }
  const graticule = geoGraticule10()
  const sphere = { type: 'Sphere' } as const

  function makeProj(c: Cam) {
    if (c.t <= 0) return geoOrthographic().rotate(c.rot).scale(c.scale).translate([c.tx, c.ty]).precision(0.4)
    if (c.t >= 1) return geoEqualEarth().rotate(c.rot).scale(c.scale).translate([c.tx, c.ty]).precision(0.4)
    const t = c.t
    const raw = (l: number, p: number) => {
      const a = geoOrthographicRaw(l, p)
      const b = geoEqualEarthRaw(l, p)
      return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t] as [number, number]
    }
    return geoProjection(raw).rotate(c.rot).scale(c.scale).translate([c.tx, c.ty]).clipAngle(90 + 90 * t * t).precision(0.6)
  }
  // On the globe and the flat map, screen = translate + scale * unit position for a fixed rotation,
  // so unit positions are projected once per rotation and reused while panning and zooming.
  const affine = (c: Cam) => c.t === 0 || c.t === 1
  const affKey = (c: Cam) => `${c.t}|${c.rot[0].toFixed(4)}|${c.rot[1].toFixed(4)}`
  const RAD = Math.PI / 180
  /** Orthographic unit position and front-facing factor, without d3 overhead. */
  function orthoUnit(c: Cam) {
    const l0 = c.rot[0] * RAD, c0 = Math.cos(c.rot[1] * RAD), s0 = Math.sin(c.rot[1] * RAD)
    const cl0 = Math.cos(l0), sl0 = Math.sin(l0)
    return (cosP: number, sinP: number, cosL: number, sinL: number, out: Float32Array, k: number) => {
      const cL = cosL * cl0 - sinL * sl0, sL = sinL * cl0 + cosL * sl0
      const x = cosP * cL, y = cosP * sL, z = sinP
      const x2 = x * c0 - z * s0
      out[2 * k] = y
      out[2 * k + 1] = -(z * c0 + x * s0)
      return x2 > 1e-3 ? Math.max(0.3, Math.min(1, x2 * 1.4)) : 0
    }
  }
  function unitProj(c: Cam) {
    return (c.t === 0 ? geoOrthographic() : geoEqualEarth()).rotate(c.rot).scale(1).translate([0, 0])
  }
  const boxFeature = (b: BBox) => {
    const [w, s, e, n] = b
    const east = e < w ? e + 360 : e
    const ring: [number, number][] = []
    const k = 24
    for (let i = 0; i <= k; i++) ring.push([w, s + ((n - s) * i) / k])
    for (let i = 1; i <= k; i++) ring.push([w + ((east - w) * i) / k, n])
    for (let i = 1; i <= k; i++) ring.push([east, n - ((n - s) * i) / k])
    for (let i = 1; i <= k; i++) ring.push([east - ((east - w) * i) / k, s])
    return { type: 'Polygon', coordinates: [ring] } as any
  }

  // ---------- framing ----------
  const MAX_DEG = 128 // px per degree at most: a 0.25° cell ≈ 32 px
  const maxScale = () => (MAX_DEG * 180) / Math.PI
  const minScale = () => Math.min(W, H) * 0.25
  function safe() {
    const i = app.insets
    return { x0: i.left, y0: i.top, x1: W - i.right, y1: H - i.bottom }
  }
  function target(bbox: BBox | null, proj: 'globe' | 'flat'): Cam {
    const f = safe()
    const sw = f.x1 - f.x0, sh = f.y1 - f.y0
    const pad = Math.min(sw, sh) * 0.05
    const ext: [[number, number], [number, number]] = [[f.x0 + pad, f.y0 + pad], [f.x1 - pad, f.y1 - pad]]
    const centre = (b: BBox) => [b[0] + ((b[2] < b[0] ? b[2] + 360 : b[2]) - b[0]) / 2, (b[1] + b[3]) / 2]
    let c: Cam
    if (proj === 'globe') {
      const cc = bbox ? centre(bbox) : null
      const rot: [number, number] = cc ? [-cc[0], -cc[1]] : [cam.rot[0], -18]
      const p = geoOrthographic().rotate(rot)
      if (bbox && bbox[2] - bbox[0] < 120) p.fitExtent([[f.x0 + sw * 0.3, f.y0 + sh * 0.3], [f.x1 - sw * 0.3, f.y1 - sh * 0.3]], boxFeature(bbox))
      else p.fitExtent(ext, sphere)
      const [tx, ty] = p.translate()
      c = { t: 0, rot, scale: p.scale(), tx, ty }
    } else {
      const small = !!bbox && bbox[2] - bbox[0] < 300
      const rot: [number, number] = [-(small ? centre(bbox!)[0] : 10), 0]
      const p = geoEqualEarth().rotate(rot)
      if (small) {
        const span = Math.max(bbox![2] - bbox![0], bbox![3] - bbox![1])
        const k = span < 5 ? 0.3 : span < 15 ? 0.2 : 0.1
        p.fitExtent([[f.x0 + sw * k, f.y0 + sh * k], [f.x1 - sw * k, f.y1 - sh * k]], boxFeature(bbox!))
      } else p.fitExtent(ext, sphere)
      const [tx, ty] = p.translate()
      c = { t: 1, rot, scale: p.scale(), tx, ty }
    }
    if (c.scale > maxScale()) {
      // Keep the centre while capping the zoom.
      const k = maxScale() / c.scale
      const cx = (f.x0 + f.x1) / 2, cy = (f.y0 + f.y1) / 2
      c = { ...c, scale: maxScale(), tx: cx - (cx - c.tx) * k, ty: cy - (cy - c.ty) * k }
    }
    return c
  }
  function introCam(): Cam {
    const wide = W > 900
    const r = wide ? Math.min(H * 0.43, W * 0.28) : Math.min(W * 0.4, H * 0.24)
    return { t: 0, rot: cam.rot, scale: r, tx: wide ? W - r - Math.max(40, W * 0.06) : W * 0.5, ty: H * (wide ? 0.53 : 0.3) }
  }
  function fly(to: Cam, dur = 1500) {
    const from = { ...cam, rot: [...cam.rot] as [number, number] }
    let d = to.rot[0] - from.rot[0]
    d = ((((d + 180) % 360) + 360) % 360) - 180
    to = { ...to, rot: [from.rot[0] + d, to.rot[1]] }
    const travel = Math.abs(d) + Math.abs(to.rot[1] - from.rot[1])
    inertia = { x: 0, y: 0 }
    zoomTarget = null
    anim = { from, to, start: performance.now(), dur: reduced ? 0 : dur, arc: from.t === to.t ? Math.min(0.5, travel / 160) : 0 }
  }
  function stepCam(now: number) {
    if (!anim) return
    const k = anim.dur ? Math.min(1, (now - anim.start) / anim.dur) : 1
    const e = easeCubicInOut(k)
    const a = anim.from, b = anim.to
    const ls = Math.log(a.scale) + (Math.log(b.scale) - Math.log(a.scale)) * e - anim.arc * Math.sin(Math.PI * k)
    const te = a.t < b.t ? easeCubicInOut(Math.max(0, (k - 0.25) / 0.75)) : a.t > b.t ? easeCubicInOut(Math.min(1, k / 0.75)) : e
    cam = {
      t: a.t + (b.t - a.t) * te,
      rot: interpolate(a.rot, b.rot)(e) as [number, number],
      scale: Math.exp(ls),
      tx: a.tx + (b.tx - a.tx) * e,
      ty: a.ty + (b.ty - a.ty) * e,
    }
    if (k >= 1) {
      cam = { ...b }
      anim = null
    }
  }

  // ---------- month blending ----------
  let blend = { a: app.month, b: app.month, start: 0, dur: 1 }
  let lastMonth = app.month
  const blendF = (t: number) => Math.min(1, (t - blend.start) / blend.dur)

  // ---------- frame state ----------
  let now = 0
  let pulseK = 0
  let outlineStart = 0
  let lastPlaceId = ''
  let camKey = ''
  const ck = (c: Cam) => `${c.t.toFixed(4)}|${c.rot[0].toFixed(3)}|${c.rot[1].toFixed(3)}|${c.scale.toFixed(2)}|${c.tx.toFixed(1)}|${c.ty.toFixed(1)}`
  let moving = false // the camera changed recently: draw the light base layer
  let fast = false // user-driven or animated motion: also drop to 1x resolution
  let lastFast = -1e9
  let pr: any = null
  /** Pixels per degree near the centre of the view. */
  let deg = 3

  function makeLayer(cv: HTMLCanvasElement, q_: number): Layer {
    const base_ = document.createElement('canvas')
    const lab = document.createElement('canvas')
    return { cv, ctx: cv.getContext('2d')!, base: base_, bctx: base_.getContext('2d')!, q: q_, key: '', cam: null, lab, lctx: lab.getContext('2d')!, lkey: '', lcam: null }
  }
  function sizeLayer(l: Layer) {
    l.cv.width = Math.round(W * l.q)
    l.cv.height = Math.round(H * l.q)
    l.base.width = l.cv.width
    l.base.height = l.cv.height
    l.lab.width = l.cv.width
    l.lab.height = l.cv.height
    l.key = ''
    l.lkey = ''
  }
  function useLayer(l: Layer) {
    L = l
    ctx = l.ctx
    base = l.base
    bctx = l.bctx
    q = l.q
    drawCv = l.cv
  }

  // ---------- base layer (cached until the camera or detail changes) ----------
  let baseKey = '' // forces a base redraw on both layers when cleared
  /** During fast motion on the flat map, reuse the cached background, shifted and scaled. */
  function reuseBase(): boolean {
    const baseCam = L.cam
    if (!(fast || (moving && slowMachine)) || !baseCam || !affine(cam) || cam.t !== baseCam.t) return false
    if (Math.abs(cam.rot[0] - baseCam.rot[0]) > 1e-6 || Math.abs(cam.rot[1] - baseCam.rot[1]) > 1e-6) return false
    const k = cam.scale / baseCam.scale
    if (k < 0.97 || k > 2.5) return false
    const c = ctx
    c.setTransform(1, 0, 0, 1, 0, 0)
    c.fillStyle = '#f6f5f1'
    c.fillRect(0, 0, drawCv.width, drawCv.height)
    c.setTransform(q * k, 0, 0, q * k, q * (cam.tx - k * baseCam.tx), q * (cam.ty - k * baseCam.ty))
    c.drawImage(base, 0, 0, W, H)
    return true
  }
  function drawBase() {
    const level = moving ? 'c' : deg > 40 && finest ? 'x' : deg > 5 && fine ? 'f' : 'c'
    const lines = !moving && deg > 6 && geo.ready.lines
    const key = `${camKey}|${W}x${H}@${q}|${level}|${lines}|${moving}`
    if (key + baseKey === L.key) return
    L.key = key + baseKey
    L.cam = { ...cam, rot: [...cam.rot] as [number, number] }
    const g = visibleGeo(level === 'x' ? finest! : level === 'f' ? fine! : coarse)
    const c = bctx
    c.setTransform(q, 0, 0, q, 0, 0)
    c.clearRect(0, 0, W, H)
    const path = geoPath(moving ? (makeProj(cam) as any).precision(2) : pr, c)
    c.beginPath()
    path(sphere)
    c.fillStyle = '#fbfaf7'
    c.fill()
    if (cam.t < 1) {
      // Volume: a cool rim and a soft light from the upper left.
      const r = cam.scale
      const grad = c.createRadialGradient(cam.tx - r * 0.35, cam.ty - r * 0.4, r * 0.1, cam.tx, cam.ty, r)
      grad.addColorStop(0, 'rgba(255,255,255,0)')
      grad.addColorStop(0.7, 'rgba(120,140,160,0.05)')
      grad.addColorStop(1, `rgba(100,120,145,${0.24 * (1 - cam.t)})`)
      c.fillStyle = grad
      c.fill()
    }
    if (!moving) {
      c.beginPath()
      path(graticule)
      c.strokeStyle = 'rgba(22,25,29,0.055)'
      c.lineWidth = 0.6
      c.stroke()
    }
    c.beginPath()
    path(g.land)
    c.fillStyle = '#e8e5dd'
    c.fill()
    if (!moving) {
      // A soft inner edge gives the land a little relief: layered strokes, no blur filter.
      c.save()
      c.clip()
      c.lineJoin = 'round'
      for (const [w, a] of [[10, 0.035], [6, 0.045], [3, 0.06]] as const) {
        c.lineWidth = w
        c.strokeStyle = `rgba(90,78,60,${a})`
        c.stroke()
      }
      c.restore()
    }
    if (lines) {
      c.lineJoin = 'round'
      drawLines(c, geo.lakes, 99, '#dde6ec', 0, true)
      drawLines(c, geo.rivers, deg > 30 ? 99 : deg > 14 ? 6 : 4, '#b8c9d6', 0.8)
      c.setLineDash([3, 3])
      drawLines(c, geo.admin1Lines, 99, 'rgba(22,25,29,0.22)', 0.6)
      c.setLineDash([])
    }
    if (!moving) c.beginPath()
    if (!moving) path(g.borders)
    if (moving) return
    c.strokeStyle = deg > 6 ? 'rgba(22,25,29,0.38)' : 'rgba(251,250,247,0.95)'
    c.lineWidth = deg > 6 ? 0.9 : 0.8
    c.stroke()
    c.beginPath()
    path(sphere)
    c.strokeStyle = 'rgba(22,25,29,0.12)'
    c.lineWidth = 0.8
    c.stroke()
  }
  function drawLines(c: CanvasRenderingContext2D, lines: typeof geo.rivers, maxRank: number, color: string, width: number, fill = false) {
    const vis = visibleTest()
    c.beginPath()
    for (const l of lines) {
      if (l.rank > maxRank) continue
      const p = l.pts
      let pen = false
      for (let i = 0; i < p.length; i += 2) {
        if (!vis(p[i + 1], p[i])) {
          pen = false
          continue
        }
        const s = pr([p[i], p[i + 1]])
        if (!s) {
          pen = false
          continue
        }
        if (pen) c.lineTo(s[0], s[1])
        else c.moveTo(s[0], s[1])
        pen = true
      }
      if (fill) c.closePath()
    }
    if (fill) {
      c.fillStyle = color
      c.fill()
    } else {
      c.strokeStyle = color
      c.lineWidth = width
      c.stroke()
    }
  }

  function visibleTest() {
    if (cam.t >= 1) return (_la: number, _lo: number) => 1
    const clip = ((90 + 90 * cam.t * cam.t) * Math.PI) / 180
    const cosClip = Math.cos(clip) + 1e-3
    const l0 = (-cam.rot[0] * Math.PI) / 180, p0 = (-cam.rot[1] * Math.PI) / 180
    const sp0 = Math.sin(p0), cp0 = Math.cos(p0)
    return (lat: number, lon: number) => {
      const p = (lat * Math.PI) / 180, l = (lon * Math.PI) / 180
      const d = sp0 * Math.sin(p) + cp0 * Math.cos(p) * Math.cos(l - l0)
      return d > cosClip ? Math.max(0.3, Math.min(1, cam.t + d * 1.4)) : 0
    }
  }

  // ---------- dots and cells ----------
  const NB = 64
  const batches: number[][] = Array.from({ length: NB }, () => [])
  const bucketColor = (b: number) => LUT[Math.round(((b + 0.5) / NB) * 255)]
  function flush(alpha: number, shape: 'dot' | 'square', size = 0, radius = 0) {
    const c = ctx
    c.globalAlpha = alpha
    c.globalCompositeOperation = 'multiply'
    for (let b = 0; b < NB; b++) {
      const arr = batches[b]
      if (!arr.length) continue
      c.beginPath()
      if (shape === 'dot') {
        for (let i = 0; i < arr.length; i += 3) {
          c.moveTo(arr[i] + arr[i + 2], arr[i + 1])
          c.arc(arr[i], arr[i + 1], arr[i + 2], 0, 6.2832)
        }
      } else {
        const h = size / 2
        if (size < 12) for (let i = 0; i < arr.length; i += 3) c.rect(arr[i] - h, arr[i + 1] - h, size, size)
        else for (let i = 0; i < arr.length; i += 3) c.roundRect(arr[i] - h, arr[i + 1] - h, size, size, radius)
      }
      c.fillStyle = bucketColor(b)
      c.fill()
      arr.length = 0
    }
    c.globalCompositeOperation = 'source-over'
    c.globalAlpha = 1
  }
  // Anomaly batches by colour string.
  const anomBatches = new Map<string, number[]>()
  function flushAnom(alpha: number, shape: 'dot' | 'square', size = 0, radius = 0) {
    const c = ctx
    c.globalAlpha = alpha
    for (const [col, arr] of anomBatches) {
      c.beginPath()
      if (shape === 'dot') for (let i = 0; i < arr.length; i += 3) (c.moveTo(arr[i] + arr[i + 2], arr[i + 1]), c.arc(arr[i], arr[i + 1], arr[i + 2], 0, 6.2832))
      else for (let i = 0; i < arr.length; i += 3) c.roundRect(arr[i] - size / 2, arr[i + 1] - size / 2, size, size, radius)
      c.fillStyle = col
      c.fill()
    }
    anomBatches.clear()
    c.globalAlpha = 1
  }

  // Positions of the 1° grid: unit positions cached per rotation, scaled per frame.
  let wxy = new Float32Array(0)
  let wvis = new Float32Array(0)
  let wux = new Float32Array(0)
  let wTrig: Float32Array | null = null
  /** cos/sin of latitude and longitude per cell (offset in degrees added to both). */
  function trigOf(lat: Float32Array | number[], lon: Float32Array | number[], off: number) {
    const n = lat.length, t = new Float32Array(n * 4)
    for (let i = 0; i < n; i++) {
      const P = (lat[i] + off) * RAD, L = (lon[i] + off) * RAD
      t[4 * i] = Math.cos(P)
      t[4 * i + 1] = Math.sin(P)
      t[4 * i + 2] = Math.cos(L)
      t[4 * i + 3] = Math.sin(L)
    }
    return t
  }
  let wKey = ''
  let wAff = ''
  function worldPositions() {
    if (wKey === camKey && wxy.length) return
    wKey = camKey
    if (wxy.length !== world.n * 2) {
      wxy = new Float32Array(world.n * 2)
      wvis = new Float32Array(world.n)
      wux = new Float32Array(world.n * 2)
    }
    if (affine(cam)) {
      const ak = affKey(cam)
      if (ak !== wAff) {
        wAff = ak
        if (cam.t === 0) {
          if (!wTrig) wTrig = trigOf(world.lat, world.lon, 0)
          const f = orthoUnit(cam)
          for (let i = 0; i < world.n; i++) wvis[i] = f(wTrig[4 * i], wTrig[4 * i + 1], wTrig[4 * i + 2], wTrig[4 * i + 3], wux, i)
        } else {
        const up = unitProj(cam)
        const vis = visibleTest()
        for (let i = 0; i < world.n; i++) {
          const v = vis(world.lat[i], world.lon[i])
          const p = v ? up([world.lon[i], world.lat[i]]) : null
          wvis[i] = p ? v : 0
          if (p) {
            wux[2 * i] = p[0]
            wux[2 * i + 1] = p[1]
          }
        }
        }
      }
      const S = cam.scale, TX = cam.tx, TY = cam.ty
      for (let i = 0; i < world.n; i++) {
        wxy[2 * i] = TX + S * wux[2 * i]
        wxy[2 * i + 1] = TY + S * wux[2 * i + 1]
      }
      return
    }
    wAff = ''
    const vis = visibleTest()
    for (let i = 0; i < world.n; i++) {
      const v = vis(world.lat[i], world.lon[i])
      wvis[i] = v
      if (!v) continue
      const p = pr([world.lon[i], world.lat[i]])
      if (!p) {
        wvis[i] = 0
        continue
      }
      wxy[2 * i] = p[0]
      wxy[2 * i + 1] = p[1]
    }
  }

  // Same-month median per 1° cell for the anomaly layer (approximate: from the quantized grid).
  const medCache = new Map<number, Float32Array>()
  function worldMedians(m: number) {
    if (medCache.has(m)) return medCache.get(m)!
    const T = world.T, y = +MONTHS[m].slice(0, 4), mo = MONTHS[m].slice(5)
    const refs: number[] = []
    for (let k = 0; k < T; k++) if (MONTHS[k].slice(5) === mo && +MONTHS[k].slice(0, 4) < y && +MONTHS[k].slice(0, 4) >= 2001) refs.push(k)
    const out = new Float32Array(world.n)
    const buf: number[] = []
    for (let i = 0; i < world.n; i++) {
      buf.length = 0
      for (const k of refs) buf.push(world.harm[i * T + k])
      buf.sort((a, b) => a - b)
      out[i] = buf.length ? levelToValue(buf[(buf.length - 1) >> 1] * 0.5 + buf[buf.length >> 1] * 0.5, world.vmax) : NaN
    }
    medCache.set(m, out)
    if (medCache.size > 24) medCache.delete(medCache.keys().next().value!)
    return out
  }

  /** 0 = only 1° dots … 1 = only 0.25° tiles. */
  const tileMix = () => Math.max(0, Math.min(1, (deg - 7) / 5))

  function drawWorld(alpha: number) {
    if (alpha <= 0.01) return
    worldPositions()
    const f = blendF(now)
    const ma = blend.a, mb = blend.b, T = world.T
    const src = app.mode === 'raw' ? world.raw : world.harm
    const boost = 1 + 0.5 * pulseK
    const rmax = Math.min(5.5, Math.max(1.2, deg * 0.64))
    const anom = app.layer === 'anomaly' && app.mode === 'harm'
    const med = anom ? worldMedians(mb) : null
    for (let i = 0; i < world.n; i++) {
      const v = wvis[i]
      if (!v) continue
      let qa = src[i * T + ma], qb = src[i * T + mb]
      if (qa === 255) qa = 0
      if (qb === 255) qb = 0
      const qq = qa + (qb - qa) * f
      if (qq < 1) continue
      const t = qq / 254
      const r = rmax * (0.22 + 0.78 * Math.sqrt(t)) * v * boost
      if (med) {
        const md = med[i]
        const col = !(md >= 1) ? '#cfcac0' : anomalyColor(levelToValue(qb, world.vmax) / md)
        let arr = anomBatches.get(col)
        if (!arr) anomBatches.set(col, (arr = []))
        arr.push(wxy[2 * i], wxy[2 * i + 1], r)
      } else batches[Math.min(NB - 1, (t * NB) | 0)].push(wxy[2 * i], wxy[2 * i + 1], r)
    }
    if (med) flushAnom(alpha, 'dot')
    else flush(alpha, 'dot')
  }

  /** 0.25° detail from tiles; returns false while visible tiles are still loading. */
  function drawTiles(alpha: number): boolean {
    if (alpha <= 0.01 || !tileIndex || (cam.t > 0 && cam.t < 1)) return true
    const b = viewBounds()
    if (!b) return true
    const f = blendF(now)
    const ma = blend.a, mb = blend.b
    const cellPx = deg * 0.25
    const square = cellPx >= 7
    const vis = visibleTest()
    const sb = app.place.bbox
    const sel: BBox | null = sb ? [sb[0], sb[1], sb[2], sb[3]] : null
    const raw = app.mode === 'raw'
    const anom = app.layer === 'anomaly' && !raw
    const lvmax = Math.log1p(tileIndex.vmax)
    const boost = 1 + 0.35 * pulseK
    let complete = true
    const dims: [number[][], number][] = []
    for (let ty = Math.max(0, Math.floor((b.s + 90) / 10)); ty <= Math.min(17, Math.floor((b.n + 90) / 10)); ty++)
      for (let tx = Math.max(0, Math.floor((b.w + 180) / 10)); tx <= Math.min(35, Math.floor((b.e + 180) / 10)); tx++) {
        const t = getTile(ty, tx, () => (dirty = true))
        if (t === undefined) {
          complete = false
          continue
        }
        if (!t) continue
        drawTile(t, ty, tx, ma, mb, f, cellPx, square, vis, sel, raw, anom, lvmax, boost)
      }
    void dims
    const size = Math.max(1, cellPx - Math.max(1, cellPx * 0.08))
    if (anom) flushAnom(alpha, square ? 'square' : 'dot', size, Math.min(3, size * 0.2))
    else flush(alpha, square ? 'square' : 'dot', size, Math.min(3, size * 0.2))
    // Outside the selection: a lighter second pass.
    if (outsideBatches.some((a) => a.length)) {
      for (let k = 0; k < NB; k++) {
        batches[k] = outsideBatches[k]
        outsideBatches[k] = []
      }
      flush(alpha * 0.32, square ? 'square' : 'dot', size, Math.min(3, size * 0.2))
    }
    return complete
  }
  const outsideBatches: number[][] = Array.from({ length: NB }, () => [])
  const tileMed = new Map<string, Float32Array>()
  // Unit positions per tile for the current rotation.
  let tuAff = ''
  const tileUnit = new Map<string, { u: Float32Array; v: Float32Array }>()
  function unitsFor(t: Tile, ty: number, tx: number) {
    const ak = affKey(cam)
    if (ak !== tuAff) {
      tuAff = ak
      tileUnit.clear()
    }
    const key = `${ty}_${tx}`
    let e = tileUnit.get(key)
    if (e) return e
    const u = new Float32Array(t.n * 2), v = new Float32Array(t.n)
    if (cam.t === 0) {
      const f = orthoUnit(cam)
      for (let i = 0; i < t.n; i++) {
        const P = ((ty * 40 + ((t.idx[i] / 40) | 0)) * 0.25 - 90 + 0.125) * RAD
        const L = ((tx * 40 + (t.idx[i] % 40)) * 0.25 - 180 + 0.125) * RAD
        v[i] = f(Math.cos(P), Math.sin(P), Math.cos(L), Math.sin(L), u, i)
      }
      e = { u, v }
      tileUnit.set(key, e)
      return e
    }
    const up = unitProj(cam)
    const vis = visibleTest()
    for (let i = 0; i < t.n; i++) {
      const lat = (ty * 40 + ((t.idx[i] / 40) | 0)) * 0.25 - 90 + 0.125
      const lon = (tx * 40 + (t.idx[i] % 40)) * 0.25 - 180 + 0.125
      const vv = vis(lat, lon)
      const p = vv ? up([lon, lat]) : null
      v[i] = p ? vv : 0
      if (p) {
        u[2 * i] = p[0]
        u[2 * i + 1] = p[1]
      }
    }
    e = { u, v }
    tileUnit.set(key, e)
    return e
  }
  function drawTile(t: Tile, ty: number, tx: number, ma: number, mb: number, f: number, cellPx: number, square: boolean, vis: any, sel: BBox | null, raw: boolean, anom: boolean, lvmax: number, boost: number) {
    const T = t.T
    let med: Float32Array | null = null
    if (anom) {
      const key = `${ty}_${tx}_${mb}`
      med = tileMed.get(key) ?? null
      if (!med) {
        const y = +MONTHS[mb].slice(0, 4), mo = MONTHS[mb].slice(5)
        const refs: number[] = []
        for (let k = 0; k < T; k++) if (MONTHS[k].slice(5) === mo && +MONTHS[k].slice(0, 4) < y && +MONTHS[k].slice(0, 4) >= 2001) refs.push(k)
        med = new Float32Array(t.n)
        const buf: number[] = []
        for (let i = 0; i < t.n; i++) {
          buf.length = 0
          for (const k of refs) buf.push(t.harm[i * T + k])
          buf.sort((a, b) => a - b)
          med[i] = buf.length ? Math.expm1(((buf[(buf.length - 1) >> 1] + buf[buf.length >> 1]) / 2 / 254) * lvmax) : NaN
        }
        tileMed.set(key, med)
        if (tileMed.size > 200) tileMed.delete(tileMed.keys().next().value!)
      }
    }
    const U = unitsFor(t, ty, tx)
    const S = cam.scale, TX = cam.tx, TY = cam.ty
    void vis
    for (let i = 0; i < t.n; i++) {
      const v = U.v[i]
      if (!v) continue
      let qa: number, qb: number
      if (raw) {
        const ra = t.raw[i * T + ma], rb = t.raw[i * T + mb]
        qa = ra === 65535 ? 0 : (254 * Math.log1p(ra)) / lvmax
        qb = rb === 65535 ? 0 : (254 * Math.log1p(rb)) / lvmax
      } else {
        qa = t.harm[i * T + ma]
        qb = t.harm[i * T + mb]
      }
      const qq = qa + (qb - qa) * f
      if (qq < 1) continue
      const px = TX + S * U.u[2 * i], py = TY + S * U.u[2 * i + 1]
      if (px < -cellPx || py < -cellPx || px > W + cellPx || py > H + cellPx) continue
      const p = [px, py]
      const tt = Math.min(1, qq / 254)
      let inside = true
      if (sel) {
        const lat = (ty * 40 + ((t.idx[i] / 40) | 0)) * 0.25 - 90 + 0.125
        const lon = (tx * 40 + (t.idx[i] % 40)) * 0.25 - 180 + 0.125
        inside = lon >= sel[0] && lon <= sel[2] && lat >= sel[1] && lat <= sel[3]
      }
      const r = square ? 0 : Math.min(cellPx * 0.56, 4.5) * (0.3 + 0.7 * Math.sqrt(tt)) * v * (inside ? boost : 1)
      if (med) {
        const md = med[i]
        const col = !(md >= 0.5) ? '#d6d1c7' : anomalyColor(Math.expm1((qb / 254) * lvmax) / md)
        let arr = anomBatches.get(col)
        if (!arr) anomBatches.set(col, (arr = []))
        arr.push(p[0], p[1], r)
      } else (inside ? batches : outsideBatches)[Math.min(NB - 1, (tt * NB) | 0)].push(p[0], p[1], r)
    }
  }
  function viewBounds() {
    if (!(cam.t === 0 || cam.t === 1)) return null
    const inv = (pr as any).invert
    if (!inv) return null
    let w = 180, e = -180, s = 90, n = -90, hit = 0
    for (let i = 0; i <= 8; i++)
      for (let j = 0; j <= 8; j++) {
        const ll = inv([(W * i) / 8, (H * j) / 8])
        if (!ll || !Number.isFinite(ll[0])) continue
        hit++
        w = Math.min(w, ll[0])
        e = Math.max(e, ll[0])
        s = Math.min(s, ll[1])
        n = Math.max(n, ll[1])
      }
    if (!hit || e - w > 120) return null // too wide for tiles; the 1° grid covers it
    return { w: w - 1, e: e + 1, s: s - 1, n: n + 1 }
  }

  // ---------- labels ----------
  const measure = new Map<string, number>()
  function textW(s: string, c: CanvasRenderingContext2D = ctx) {
    let w = measure.get(s)
    if (w == null) measure.set(s, (w = c.measureText(s).width))
    return w
  }
  function drawLabels(c: CanvasRenderingContext2D) {
    const f = safe()
    const boxes: number[] = []
    const vis = visibleTest()
    const free = (x: number, y: number, w: number, h: number) => {
      if (x < f.x0 || y < f.y0 || x + w > f.x1 || y + h > f.y1) return false
      for (let i = 0; i < boxes.length; i += 4) if (x < boxes[i] + boxes[i + 2] && x + w > boxes[i] && y < boxes[i + 1] + boxes[i + 3] && y + h > boxes[i + 1]) return false
      boxes.push(x - 3, y - 2, w + 6, h + 4)
      return true
    }
    c.lineJoin = 'round'
    c.textBaseline = 'middle'
    let count = 0
    // Cities: more appear as you zoom in.
    if (geo.ready.points && deg > 3.5) {
      const maxRank = deg < 6 ? 1 : deg < 10 ? 2 : deg < 18 ? 4 : deg < 40 ? 6 : 8
      for (const p of geo.places) {
        if (p.rank > maxRank || count > 90) break
        if (!vis(p.lat, p.lon)) continue
        const s = pr([p.lon, p.lat])
        if (!s) continue
        const big = p.rank <= 1 || p.cap
        c.font = `${big ? 600 : 500} ${big ? 12.5 : 11.5}px ${fontFamily}`
        const w = textW(c.font + p.name, c)
        if (!free(s[0] + 6, s[1] - 8, w, 16)) continue
        c.beginPath()
        c.arc(s[0], s[1], big ? 2.8 : 2.2, 0, 6.2832)
        c.fillStyle = '#16191d'
        c.fill()
        c.lineWidth = 3.5
        c.strokeStyle = 'rgba(251,250,247,0.92)'
        c.strokeText(p.name, s[0] + 7, s[1])
        c.fillStyle = '#16191d'
        c.fillText(p.name, s[0] + 7, s[1])
        count++
      }
    }
    // States and provinces.
    if (geo.ready.points && deg > 9) {
      const maxRank = deg < 20 ? 2 : deg < 50 ? 5 : 9
      c.font = `500 10.5px ${fontFamily}`
      let k = 0
      for (const p of geo.admin1) {
        if (p.rank > maxRank || k > 40) continue
        if (!vis(p.lat, p.lon)) continue
        const s = pr([p.lon, p.lat])
        if (!s) continue
        const label = p.name.toUpperCase()
        const w = textW('a1' + label, c) * 1.1
        if (!free(s[0] - w / 2, s[1] - 7, w, 14)) continue
        c.lineWidth = 3
        c.strokeStyle = 'rgba(251,250,247,0.85)'
        c.letterSpacing = '0.08em'
        c.strokeText(label, s[0] - w / 2, s[1])
        c.fillStyle = 'rgba(22,25,29,0.5)'
        c.fillText(label, s[0] - w / 2, s[1])
        c.letterSpacing = '0px'
        k++
      }
    }
    // Countries.
    if (deg > 1.2 && deg < 60) {
      c.font = `600 ${deg > 6 ? 12 : 10.5}px ${fontFamily}`
      let k = 0
      for (const p of countryLabels) {
        if (k > 60) break
        if (!vis(p.lat, p.lon)) continue
        const s = pr([p.lon, p.lat])
        if (!s) continue
        const label = p.name.toUpperCase()
        const w = textW('c' + c.font + label, c) * 1.14
        if (!free(s[0] - w / 2, s[1] - 7, w, 14)) continue
        c.letterSpacing = '0.12em'
        c.lineWidth = 3
        c.strokeStyle = 'rgba(251,250,247,0.8)'
        c.strokeText(label, s[0] - w / 2, s[1])
        c.fillStyle = 'rgba(22,25,29,0.42)'
        c.fillText(label, s[0] - w / 2, s[1])
        c.letterSpacing = '0px'
        k++
      }
    }
  }

  let labelFade = { start: 0 }
  function labelsLayer() {
    const key = `${camKey}|${W}x${H}|${geo.ready.points}|${app.insets.left},${app.insets.right}`
    if (!moving && key !== L.lkey) {
      L.lkey = key
      L.lcam = { ...cam, rot: [...cam.rot] as [number, number] }
      const c = L.lctx
      c.setTransform(1, 0, 0, 1, 0, 0)
      c.clearRect(0, 0, L.lab.width, L.lab.height)
      c.setTransform(q, 0, 0, q, 0, 0)
      drawLabels(c)
      labelFade = { start: now }
    }
    const lc = L.lcam
    if (!lc) return
    const same = !moving && L.lkey === key
    const follow = moving && !slowMachine && affine(cam) && cam.t === lc.t && Math.abs(cam.rot[0] - lc.rot[0]) < 1e-6 && Math.abs(cam.rot[1] - lc.rot[1]) < 1e-6
    if (!same && !follow) return
    const a = reduced ? 1 : Math.min(1, (now - labelFade.start) / 220)
    if (a < 1) dirty = true
    const k = cam.scale / lc.scale
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.globalAlpha = a
    if (same) ctx.drawImage(L.lab, 0, 0)
    else {
      ctx.setTransform(q * k, 0, 0, q * k, q * (cam.tx - k * lc.tx), q * (cam.ty - k * lc.ty))
      ctx.drawImage(L.lab, 0, 0, W, H)
    }
    ctx.globalAlpha = 1
    ctx.setTransform(q, 0, 0, q, 0, 0)
  }

  // ---------- selection outline ----------
  function outline(path: any, b: BBox) {
    const c = ctx
    const k = reduced ? 1 : Math.min(1, (now - outlineStart) / 1200)
    const e = easeCubicOut(k)
    const ring = (boxFeature(b).coordinates[0] as [number, number][]).map((p) => pr(p)).filter(Boolean) as [number, number][]
    if (ring.length < 2) return
    const seg: number[] = []
    let total = 0
    for (let i = 1; i < ring.length; i++) {
      const d = Math.hypot(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1])
      seg.push(d)
      total += d
    }
    c.beginPath()
    c.moveTo(ring[0][0], ring[0][1])
    let left = total * e
    for (let i = 1; i < ring.length && left > 0; i++) {
      const d = seg[i - 1]
      const f = Math.min(1, left / d)
      c.lineTo(ring[i - 1][0] + (ring[i][0] - ring[i - 1][0]) * f, ring[i - 1][1] + (ring[i][1] - ring[i - 1][1]) * f)
      left -= d
    }
    c.strokeStyle = '#0b3d91'
    c.lineWidth = k < 1 ? 1.8 : 1.2
    c.setLineDash(k < 1 ? [7, 5] : [])
    c.lineDashOffset = -now / 30
    c.stroke()
    c.setLineDash([])
    if (k >= 1) {
      // Viewfinder corners once settled.
      const xs = ring.map((p) => p[0]), ys = ring.map((p) => p[1])
      const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys)
      const L = Math.min(18, (x1 - x0) / 4, (y1 - y0) / 4)
      c.beginPath()
      for (const [x, y, dx, dy] of [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]]) {
        c.moveTo(x - dx * 3, y + dy * L)
        c.lineTo(x - dx * 3, y - dy * 3)
        c.lineTo(x + dx * L, y - dy * 3)
      }
      c.lineWidth = 2.2
      c.stroke()
    } else dirty = true
    void path
  }
  function bandBox(path: any, b: BBox) {
    const c = ctx
    c.beginPath()
    path(boxFeature(b))
    c.fillStyle = 'rgba(11,61,145,0.08)'
    c.fill()
    c.setLineDash([5, 4])
    c.strokeStyle = '#0b3d91'
    c.lineWidth = 1.6
    c.stroke()
    c.setLineDash([])
  }

  // ---------- scatter flight ----------
  const K = 5000
  const pairs = (() => {
    const n = scatterData.x_aqua.length
    const out: { x: number; y: number; d: number; jx: number; jy: number }[] = []
    for (let k = 0; k < K; k++) {
      const i = Math.floor(((k * 2654435761) >>> 0) % n)
      out.push({ x: scatterData.x_aqua[i], y: scatterData.y_snpp[i], d: ((k * 40503) % 1000) / 1000, jx: ((k * 7919) % 100) / 50 - 1, jy: ((k * 104729) % 100) / 50 - 1 })
    }
    return out
  })()
  const medianCurve = (() => {
    const groups = new Map<number, number[]>()
    scatterData.x_aqua.forEach((x: number, i: number) => {
      const k = Math.round(Math.log10(x + 1) * 8) / 8
      if (!groups.has(k)) groups.set(k, [])
      groups.get(k)!.push(scatterData.y_snpp[i])
    })
    return [...groups]
      .sort((a, b) => a[0] - b[0])
      .filter(([, ys]) => ys.length >= 40)
      .map(([k, ys]) => {
        ys.sort((a, b) => a - b)
        return { x: 10 ** k - 1, y: ys[Math.floor(ys.length / 2)] }
      })
  })()
  let sources: Float32Array = new Float32Array(0)
  let sourcesKey = ''
  function scatterBox() {
    const f = safe()
    const w = Math.min(560, (f.x1 - f.x0) * 0.66)
    const h = Math.min(w * 0.72, (f.y1 - f.y0) * 0.7)
    return { x: f.x0 + (f.x1 - f.x0 - w) / 2 + 30, y: f.y0 + (f.y1 - f.y0 - h) / 2 - 16, w, h }
  }
  function drawScatter(s: number) {
    const c = ctx
    const box = scatterBox()
    const key = `${blend.b}|${camKey}`
    if (key !== sourcesKey) {
      worldPositions()
      const T = world.T
      const list: number[] = []
      for (let i = 0; i < world.n && list.length < K * 2; i++) if (wvis[i] && world.harm[i * T + blend.b] >= 30) list.push(wxy[2 * i], wxy[2 * i + 1])
      sources = list.length ? Float32Array.from(list) : Float32Array.from([W / 2, H / 2])
      sourcesKey = key
    }
    const X = (v: number) => box.x + (Math.log10(v + 1) / 3) * box.w
    const Y = (v: number) => box.y + box.h - (Math.log10(v + 1) / 3) * box.h
    const axes = Math.max(0, (s - 0.7) / 0.3)
    if (axes > 0) {
      c.globalAlpha = axes
      c.strokeStyle = 'rgba(22,25,29,0.1)'
      c.lineWidth = 1
      c.font = `11px ${fontFamily}`
      c.fillStyle = '#6a7079'
      c.textBaseline = 'alphabetic'
      for (const t of [0, 10, 100, 1000]) {
        c.beginPath()
        c.moveTo(X(t), box.y)
        c.lineTo(X(t), box.y + box.h)
        c.moveTo(box.x, Y(t))
        c.lineTo(box.x + box.w, Y(t))
        c.stroke()
        c.textAlign = 'center'
        c.fillText(String(t), X(t), box.y + box.h + 16)
        c.textAlign = 'right'
        c.fillText(String(t), box.x - 8, Y(t) + 4)
      }
      c.textAlign = 'left'
      c.fillStyle = '#4a4f57'
      c.font = `500 12px ${fontFamily}`
      c.fillText('MODIS (Aqua) detections, one cell, one month', box.x, box.y + box.h + 36)
      c.save()
      c.translate(box.x - 40, box.y + box.h)
      c.rotate(-Math.PI / 2)
      c.fillText('VIIRS (S-NPP), same cell and month', 0, 0)
      c.restore()
      c.setLineDash([4, 4])
      c.strokeStyle = 'rgba(22,25,29,0.35)'
      c.beginPath()
      c.moveTo(X(0), Y(0))
      c.lineTo(X(1000), Y(1000))
      c.stroke()
      c.setLineDash([])
      c.globalAlpha = 1
    }
    const ez = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : 1 - Math.pow(1 - x, 3))
    const ns = sources.length / 2
    for (let k = 0; k < pairs.length; k++) {
      const pt = pairs[k]
      const p = ez((s - pt.d * 0.35) / 0.65)
      if (p <= 0) continue
      const j = k % ns
      const sx = sources[2 * j], sy = sources[2 * j + 1]
      const tx = X(pt.x) + pt.jx * 2.2, ty = Y(pt.y) + pt.jy * 2.2
      const tt = Math.min(1, Math.log10(pt.y + 1) / 3)
      batches[Math.min(NB - 1, ((0.25 + 0.75 * tt) * NB) | 0)].push(sx + (tx - sx) * p, sy + (ty - sy) * p - Math.sin(p * Math.PI) * 70, 1.5 + (1 - p) * 1.2)
    }
    flush(0.55, 'dot')
    if (app.scatterCurve > 0) {
      const pts = medianCurve.map((b) => [X(b.x), Y(b.y)] as [number, number])
      const n = Math.max(2, Math.round(pts.length * app.scatterCurve))
      c.beginPath()
      pts.slice(0, n).forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)))
      c.strokeStyle = '#16191d'
      c.lineWidth = 2.6
      c.lineJoin = 'round'
      c.stroke()
      if (app.scatterCurve > 0.98) {
        const [lx, ly] = pts[pts.length - 1]
        c.font = `600 12px ${fontFamily}`
        c.fillStyle = '#16191d'
        c.textAlign = 'right'
        c.fillText('typical VIIRS count', lx - 8, ly - 12)
        c.fillStyle = '#6a7079'
        c.font = `11px ${fontFamily}`
        c.fillText('equal counts', X(1000) - 6, Y(1000) + 30)
        c.textAlign = 'left'
      }
    }
  }

  // ---------- frame ----------
  function draw() {
    const c = ctx
    pr = makeProj(cam)
    const p0 = pr([-cam.rot[0], -cam.rot[1]]) ?? [W / 2, H / 2]
    const p1 = pr([-cam.rot[0] + 1, -cam.rot[1]]) ?? [p0[0] + 3, p0[1]]
    deg = Math.max(0.5, Math.hypot(p1[0] - p0[0], p1[1] - p0[1]))
    // Finer coastlines as the reader zooms in, loaded once.
    if (deg > 5 && !fine && !loadingGeo.fine) {
      loadingGeo.fine = true
      import('world-atlas/countries-50m.json').then((m: any) => {
        fine = makeGeo(m.default ?? m)
        dirty = true
      })
    }
    if (deg > 40 && !finest && !loadingGeo.finest) {
      loadingGeo.finest = true
      import('world-atlas/countries-10m.json').then((m: any) => {
        finest = makeGeo(m.default ?? m)
        dirty = true
      })
    }
    if (deg > 3 && !geo.ready.points) loadPoints().then(() => (dirty = true))
    if (deg > 6 && !geo.ready.lines) loadLines().then(() => ((baseKey = String(Math.random())), (dirty = true)))

    const P = (window as any).__perfOn ? performance.now() : 0
    if (!reuseBase()) {
      drawBase()
      c.setTransform(1, 0, 0, 1, 0, 0)
      c.clearRect(0, 0, drawCv.width, drawCv.height)
      c.drawImage(base, 0, 0)
    }
    const P1 = P ? performance.now() : 0
    c.setTransform(q, 0, 0, q, 0, 0)

    const sc = app.scatter
    const fade = 1 - 0.85 * sc
    const mix = app.mode === 'raw' && app.place.kind === 'world' && deg < 7 ? 0 : tileMix()
    let tilesReady = true
    if (mix > 0) tilesReady = drawTiles(mix * fade)
    drawWorld((tilesReady ? 1 - mix : 1) * fade * (mix > 0 && tilesReady ? 1 : 1))

    const path = geoPath(pr, c)
    if (app.place.bbox && sc < 0.5) outline(path, app.place.bbox as BBox)
    if (band) bandBox(path, band)
    const P2 = P ? performance.now() : 0
    if (sc < 0.5 && affine(cam)) labelsLayer()
    if (sc > 0) drawScatter(sc)
    if (L === lo) {
      mainCtx.setTransform(1, 0, 0, 1, 0, 0)
      mainCtx.drawImage(lo.cv, 0, 0, canvas.width, canvas.height)
    }
    if (P) {
      const acc = ((window as any).__perf ??= { n: 0, base: 0, data: 0, labels: 0 })
      const P3 = performance.now()
      acc.n++
      acc.base += P1 - P
      acc.data += P2 - P1
      acc.labels += P3 - P2
    }
  }

  // ---------- input: drag with inertia, smooth wheel zoom ----------
  let dragging: { x: number; y: number; t: number; start: [number, number] | null } | null = null
  let inertia = { x: 0, y: 0 } // px per ms
  let zoomTarget: { ls: number; ax: number; ay: number } | null = null
  let zoomHint = $state(false)
  let hintTimer: ReturnType<typeof setTimeout> | undefined
  let pendingHover: [number, number] | null = null

  function local(e: PointerEvent | WheelEvent | MouseEvent): [number, number] {
    const r = canvas.getBoundingClientRect()
    return [e.clientX - r.left, e.clientY - r.top]
  }
  function invert(p: [number, number]) {
    if (anim || (cam.t > 0 && cam.t < 1)) return null
    const ll = (makeProj(cam) as any).invert?.(p)
    return ll && Number.isFinite(ll[0]) ? (ll as [number, number]) : null
  }
  function panBy(dx: number, dy: number) {
    if (cam.t < 0.5) {
      const k = 57.3 / cam.scale
      cam.rot = [cam.rot[0] + dx * k, Math.max(-85, Math.min(85, cam.rot[1] - dy * k))]
    } else {
      cam.tx += dx
      cam.ty += dy
    }
  }
  function down(e: PointerEvent) {
    if (app.scatter > 0.05) return
    const p = local(e)
    canvas.setPointerCapture(e.pointerId)
    spinning = false
    userCam = true
    anim = null
    inertia = { x: 0, y: 0 }
    touch()
    dragging = { x: p[0], y: p[1], t: performance.now(), start: app.drawing ? invert(p) : null }
    tip = null
  }
  function move(e: PointerEvent) {
    const p = local(e)
    if (!dragging) {
      pendingHover = p
      return
    }
    if (app.drawing) {
      const s = dragging.start, qq = invert(p)
      if (s && qq) band = [Math.min(s[0], qq[0]), Math.min(s[1], qq[1]), Math.max(s[0], qq[0]), Math.max(s[1], qq[1])]
    } else {
      const dx = p[0] - dragging.x, dy = p[1] - dragging.y
      const t = performance.now(), dt = Math.max(1, t - dragging.t)
      panBy(dx, dy)
      // Smoothed release velocity.
      inertia = { x: inertia.x * 0.6 + (dx / dt) * 0.4, y: inertia.y * 0.6 + (dy / dt) * 0.4 }
      dragging.t = t
    }
    dragging.x = p[0]
    dragging.y = p[1]
    dirty = true
  }
  function up() {
    if (app.drawing && band) {
      const b = band.map((v) => Math.round(v * 4) / 4) as BBox
      band = null
      app.drawing = false
      if (b[2] - b[0] >= 0.25 && b[3] - b[1] >= 0.25) (beginExplore(), selectBox(b))
    }
    if (dragging && performance.now() - dragging.t > 80) inertia = { x: 0, y: 0 }
    dragging = null
    dirty = true
  }
  function wheel(e: WheelEvent) {
    if (!(e.ctrlKey || e.metaKey)) {
      if (app.free) {
        zoomHint = true
        clearTimeout(hintTimer)
        hintTimer = setTimeout(() => (zoomHint = false), 1400)
      }
      return
    }
    e.preventDefault()
    touch()
    spinning = false
    userCam = true
    anim = null
    const [mx, my] = local(e)
    const dy = Math.max(-120, Math.min(120, e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY))
    const cur = zoomTarget?.ls ?? Math.log(cam.scale)
    const ls = Math.max(Math.log(minScale()), Math.min(Math.log(maxScale()), cur - dy * 0.0022))
    zoomTarget = { ls, ax: mx, ay: my }
  }
  export function zoomBy(f: number) {
    userCam = true
    anim = null
    const cur = zoomTarget?.ls ?? Math.log(cam.scale)
    zoomTarget = { ls: Math.max(Math.log(minScale()), Math.min(Math.log(maxScale()), cur + Math.log(f))), ax: W / 2, ay: H / 2 }
  }

  // Hover lookups: O(1) through an index of the selected place's cells.
  let cellIndex = new Map<number, [any, number]>()
  function indexPlace() {
    cellIndex = new Map()
    for (const set of [app.place.context, app.place.cells]) {
      if (!set) continue
      for (let i = 0; i < set.lat.length; i++) cellIndex.set(Math.round((set.lat[i] + 90) * 4) * 1440 + Math.round((set.lon[i] + 180) * 4), [set, i])
    }
  }
  function hover(p: [number, number]) {
    if (app.scatter > 0.05) return (tip = null)
    const ll = invert(p)
    if (!ll) return (tip = null)
    const [lon, lat] = ll
    const m = app.month
    let html = ''
    if (app.mode === 'harm') {
      const hit = cellIndex.get(Math.floor((lat + 90) * 4) * 1440 + Math.floor((lon + 180) * 4))
      if (hit) {
        const [set, i] = hit
        const v = set.est[i * set.T + m]
        html = `<b>${Number.isNaN(v) ? '—' : fmt(v, 1)}</b> detections<br><span>${monthName(MONTHS[m])} · 0.25° cell</span>`
      }
    }
    if (!html && deg > 7 && tileIndex) {
      // Zoomed in: read the 0.25° tile under the cursor (display values, so approximate).
      const ty = Math.floor((lat + 90) / 10), tx = Math.floor((lon + 180) / 10)
      const t = getTile(ty, tx, () => {})
      if (t) {
        const li = (Math.floor((lat + 90) * 4) - ty * 40) * 40 + (Math.floor((lon + 180) * 4) - tx * 40)
        let k = -1
        for (let i = 0; i < t.n; i++) if (t.idx[i] === li) ((k = i), (i = t.n))
        if (k >= 0) {
          const T = t.T
          const v = app.mode === 'raw' ? t.raw[k * T + m] : Math.expm1((t.harm[k * T + m] / 254) * Math.log1p(tileIndex.vmax))
          html =
            app.mode === 'raw' && v === 65535
              ? `<b>No value</b><br><span>${monthName(MONTHS[m])} · direct splice</span>`
              : `<b>${v < 0.5 ? 'No' : '≈ ' + fmt(v, v < 10 ? 1 : 0)}</b> detections<br><span>${monthName(MONTHS[m])} · 0.25° cell</span>`
        }
      }
      if (!html) return (tip = null)
    }
    if (!html) {
      const i = world.index[Math.floor(lat + 90) * 360 + Math.floor(lon + 180)]
      if (i < 0) return (tip = null)
      const qv = (app.mode === 'raw' ? world.raw : world.harm)[i * world.T + m]
      html =
        qv === 255
          ? `<b>No value</b><br><span>${monthName(MONTHS[m])} · direct splice</span>`
          : `<b>≈ ${fmt(levelToValue(qv, world.vmax), 0)}</b> detections<br><span>${monthName(MONTHS[m])} · 1° area</span>`
    }
    tip = { x: p[0], y: p[1], html }
  }

  // ---------- reactions ----------
  $effect(() => {
    const f = app.frame
    if (f.seq) {
      userCam = true
      fly(target(f.bbox as BBox | null, f.proj))
    }
  })
  let lastInsets = ''
  $effect(() => {
    const k = `${app.insets.left},${app.insets.right},${app.insets.top},${app.insets.bottom}`
    if (k === lastInsets) return
    lastInsets = k
    if (userCam && !anim && !dragging) fly(target(app.place.bbox as BBox | null, app.proj), 900)
  })
  $effect(() => {
    const m = app.month
    if (m === lastMonth) return
    const t = performance.now()
    const cur = blendF(t) >= 1 ? blend.b : blend.a
    blend = { a: cur, b: m, start: t, dur: reduced ? 1 : app.playing ? 1000 / (app.play.speed || 12) : 420 }
    const flare = MONTHS.indexOf('2014-01')
    if (app.mode === 'raw' && lastMonth < flare && m >= flare) app.pulse = t
    lastMonth = m
    dirty = true
  })
  $effect(() => {
    if (app.place.id !== lastPlaceId) {
      lastPlaceId = app.place.id
      outlineStart = performance.now()
      indexPlace()
      if (app.place.bbox) app.pulse = performance.now() + 1100
    }
    void app.mode, app.layer, app.highlight.cell, app.scatter, app.scatterCurve, app.introP
    dirty = true
  })
  $effect(() => {
    setPalette(app.palette)
    baseKey = app.palette
    dirty = true
  })

  onMount(() => {
    hi = makeLayer(canvas, hiQ)
    lo = makeLayer(document.createElement('canvas'), 1)
    mainCtx = hi.ctx
    useLayer(hi)
    fontFamily = getComputedStyle(document.body).fontFamily
    const ro = new ResizeObserver(() => {
      W = wrap.clientWidth
      H = wrap.clientHeight
      canvas.style.width = W + 'px'
      canvas.style.height = H + 'px'
      sizeLayer(hi)
      sizeLayer(lo)
      if (!userCam) cam = introCam()
      else if (!anim) fly(target(app.place.bbox as BBox | null, app.proj), 0)
      dirty = true
    })
    ro.observe(wrap)
    let visible = true
    const io = new IntersectionObserver(([e]) => (visible = e.isIntersecting))
    io.observe(wrap)

    const tick = (_time: number, deltaMs: number) => {
      if (document.hidden || !visible) return
      // Watch frame pacing while things move; step the sharp layer down once if it is consistently slow.
      if (drewLast && sampled < 60) {
        sampled++
        if (deltaMs > 26) slowFrames++
        if (sampled === 60 && slowFrames > 24) {
          // A slow machine: render once at 1x (no upscaling copy), no decorative spin.
          slowMachine = true
          ;(window as any).__slowMachine = true
          spinning = false
          if (hiQ > 1) {
            hiQ = 1
            hi.q = 1
            sizeLayer(hi)
            useLayer(hi)
          }
          dirty = true
        }
      }
      const t = performance.now()
      const dt = Math.min(50, deltaMs) / 1000
      now = t
      if (spinning && !anim && cam.t === 0 && !app.place.bbox && !reduced && !dragging) cam.rot = [cam.rot[0] + dt * 6, cam.rot[1]]
      if (!userCam && !anim) {
        const a = introCam(), b = target(null, 'globe')
        const k = easeCubicInOut(Math.max(0, Math.min(1, app.introP)))
        cam = { t: 0, rot: cam.rot, scale: a.scale + (b.scale - a.scale) * k, tx: a.tx + (b.tx - a.tx) * k, ty: a.ty + (b.ty - a.ty) * k }
      }
      // Inertia after a drag.
      if (!dragging && (Math.abs(inertia.x) > 0.005 || Math.abs(inertia.y) > 0.005)) {
        panBy(inertia.x * deltaMs, inertia.y * deltaMs)
        const decay = Math.exp(-deltaMs / 260)
        inertia = { x: inertia.x * decay, y: inertia.y * decay }
      }
      // Smooth zoom towards the target, anchored at the cursor on the flat map.
      if (zoomTarget) {
        const cur = Math.log(cam.scale)
        const d = zoomTarget.ls - cur
        const step = Math.abs(d) < 0.002 ? d : d * Math.min(1, dt * 14)
        const k = Math.exp(step)
        if (cam.t >= 1) {
          cam.tx = zoomTarget.ax - (zoomTarget.ax - cam.tx) * k
          cam.ty = zoomTarget.ay - (zoomTarget.ay - cam.ty) * k
        }
        cam.scale *= k
        if (step === d) zoomTarget = null
      }
      if (dragging || anim || zoomTarget || Math.abs(inertia.x) > 0.005 || Math.abs(inertia.y) > 0.005 || (!userCam && app.introP > 0 && app.introP < 1)) lastFast = t
      stepCam(t)
      const key = ck(cam)
      if (key !== camKey) {
        camKey = key
        lastMove = t
        dirty = true
      }
      moving = t - lastMove < 160
      fast = t - lastFast < 160
      // Slow auto-spin keeps full resolution; fast motion renders at 1x, then sharpens when it stops.
      // Fast motion renders on the light layer and is scaled up; it sharpens when motion stops.
      const want = fast && hiQ > 1 ? lo : hi
      if (want !== L) {
        useLayer(want)
        dirty = true
      }
      pulseK = t >= app.pulse ? Math.exp(-(t - app.pulse) / 280) : 0
      if (pulseK > 0.01 || blendF(t) < 1) dirty = true
      if (pendingHover && !moving) {
        hover(pendingHover)
        pendingHover = null
      }
      drewLast = dirty
      if (dirty) {
        dirty = false
        draw()
      }
    }
    gsap.ticker.add(tick)
    return () => {
      gsap.ticker.remove(tick)
      ro.disconnect()
      io.disconnect()
    }
  })

  const sealed = $derived(app.mode === 'raw' && MONTHS[app.month] >= '2012-01' && MONTHS[app.month] <= '2013-12')
</script>

<div class="map" bind:this={wrap} class:drawing={app.drawing}>
  <canvas
    bind:this={canvas}
    onpointerdown={down}
    onpointermove={move}
    onpointerup={up}
    onpointercancel={up}
    onpointerleave={() => ((tip = null), (pendingHover = null))}
    onwheel={wheel}
    aria-label="Map of monthly fire detections. Drag to turn or pan; Ctrl and scroll to zoom."
  ></canvas>

  {#if tip}
    <div class="tip" style:transform="translate({tip.x + 14}px, {tip.y}px) translateY(-50%)">{@html tip.html}</div>
  {/if}
  {#if sealed}
    <div class="notice" style:top="{app.insets.top + 6}px">2012–13 has no direct-splice values: those months stayed sealed for the blind test.</div>
  {/if}
  {#if zoomHint && !app.drawing}
    <div class="notice hint" style:bottom="{app.insets.bottom + 14}px">Hold Ctrl (⌘ on Mac) and scroll to zoom</div>
  {/if}
  {#if app.drawing}
    <div class="notice blue" style:top="{app.insets.top + 6}px">Drag on the map to draw an area · Esc to cancel</div>
  {/if}

  <div class="zoom" class:show={app.free} style:right="{app.insets.right + 14}px" style:bottom="{app.insets.bottom + 10}px">
    <button class="btn icon round" onclick={() => zoomBy(1.8)} aria-label="Zoom in"><Icon name="plus" /></button>
    <button class="btn icon round" onclick={() => zoomBy(1 / 1.8)} aria-label="Zoom out"><Icon name="minus" /></button>
    <button class="btn icon round" onclick={() => fly(target(app.place.bbox as BBox | null, app.proj))} aria-label="Fit to selection"><Icon name="corners" /></button>
  </div>
</div>

<svelte:window onkeydown={(e) => e.key === 'Escape' && ((app.drawing = false), (band = null), (dirty = true))} />

<style>
  .map { position: absolute; inset: 0; overflow: hidden; }
  canvas { position: absolute; inset: 0; display: block; touch-action: pan-y; cursor: grab; }
  canvas:active { cursor: grabbing; }
  .drawing canvas { cursor: crosshair; touch-action: none; }
  .tip {
    position: absolute;
    left: 0;
    top: 0;
    pointer-events: none;
    background: #fff;
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 12px;
    line-height: 1.4;
    box-shadow: 0 8px 24px -6px rgb(22 25 29 / 0.22);
    white-space: nowrap;
    z-index: 3;
    will-change: transform;
  }
  .tip :global(b) { font-size: 15px; font-weight: 600; }
  .tip :global(span) { color: var(--ink-3); }
  .notice {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    background: rgb(255 255 255 / 0.96);
    border-radius: 999px;
    padding: 7px 14px;
    font-size: 13px;
    color: var(--ink-2);
    max-width: min(92vw, 640px);
    text-align: center;
    box-shadow: 0 6px 20px -6px rgb(22 25 29 / 0.2);
    z-index: 4;
  }
  .notice.blue { color: var(--blue); }
  .notice.hint { top: auto; animation: fadein 0.3s ease; }
  @keyframes fadein { from { opacity: 0; } }
  .zoom { position: absolute; display: grid; gap: 6px; opacity: 0; transform: translateY(8px); transition: opacity 0.6s var(--ease), transform 0.6s var(--ease); pointer-events: none; z-index: 5; }
  .zoom.show { opacity: 1; transform: none; pointer-events: auto; }
  .round { border-radius: 50%; border: 0; background: #fff; box-shadow: 0 4px 14px -4px rgb(22 25 29 / 0.25); width: 34px; height: 34px; }
</style>
