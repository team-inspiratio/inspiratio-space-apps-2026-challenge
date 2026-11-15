<script lang="ts">
  import { Tween } from 'svelte/motion'
  import { cubicInOut, cubicOut } from 'svelte/easing'
  import { annual } from '../lib/v2/science.js'
  import { app, MONTHS, compact, fmt, touch } from '../lib/store.svelte'

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
  let w = $state(316)
  const H = 150, L = 34, R = 8, T = 12, B = 20
  const Y0 = 2001, Y1 = 2025
  const YEARS = Array.from({ length: Y1 - Y0 + 1 }, (_, i) => Y0 + i)

  const pick = (key: 'value' | 'raw') => {
    const a = annual(app.place.series, key) as { year: string; value: number | null }[]
    return YEARS.map((y) => a.find((d) => +d.year === y)?.value ?? null)
  }
  const harm = $derived(pick('value'))
  const raw = $derived(app.place.hasRaw ? pick('raw') : YEARS.map(() => null))
  const ymax = $derived(Math.max(1, ...harm.map((v) => v ?? 0), ...raw.map((v) => v ?? 0)) * 1.12)

  // Lines morph between places and modes; nulls stay as gaps.
  const opts = { duration: reduced ? 0 : 800, easing: cubicInOut }
  const th = new Tween(YEARS.map(() => 0), opts)
  const tr = new Tween(YEARS.map(() => 0), opts)
  const tmax = new Tween(1, opts)
  const draw = new Tween(0, { duration: reduced ? 0 : 1100, easing: cubicOut })
  $effect(() => {
    th.target = harm.map((v) => v ?? 0)
    tr.target = raw.map((v) => v ?? 0)
    tmax.target = ymax
  })
  $effect(() => {
    void app.place.id
    draw.set(0, { duration: 0 }).then(() => (draw.target = 1))
  })

  const x = (y: number) => L + ((y - Y0) / (Y1 - Y0)) * (w - L - R)
  const y = (v: number) => T + (1 - v / tmax.current) * (H - T - B)
  function line(vals: number[], mask: (number | null)[]) {
    let s = '', pen = false
    vals.forEach((v, i) => {
      if (mask[i] == null) return (pen = false)
      s += `${pen ? 'L' : 'M'}${x(YEARS[i]).toFixed(1)},${y(v).toFixed(1)}`
      pen = true
    })
    return s
  }
  const ticks = $derived([0.33, 0.66].map((f) => nice(tmax.current * f)))
  function nice(v: number) {
    const p = Math.pow(10, Math.floor(Math.log10(Math.max(1, v))))
    return Math.round(v / p) * p
  }
  const cur = $derived(+MONTHS[app.month].slice(0, 4))
  let hover = $state<number | null>(null)
  // Click a year: jump to the same month in that year and mark its calendar row.
  function chooseYear() {
    if (hover == null) return
    touch()
    app.playing = false
    const m = MONTHS.indexOf(`${hover}${MONTHS[app.month].slice(4)}`)
    if (m >= 0) {
      app.month = m
      app.highlight = { ...app.highlight, cell: MONTHS[m] }
    }
  }
  const ry0 = $derived(+MONTHS[app.range[0]].slice(0, 4))
  const ry1 = $derived(+MONTHS[app.range[1]].slice(0, 4))
  function move(e: PointerEvent) {
    const r = (e.currentTarget as SVGElement).getBoundingClientRect()
    const yr = Math.round(Y0 + ((e.clientX - r.left - L) / (w - L - R)) * (Y1 - Y0))
    hover = yr >= Y0 && yr <= Y1 ? yr : null
  }
</script>

<div class="chart" bind:clientWidth={w}>
  <svg width={w} height={H} role="img" aria-label="Detections per year" onpointermove={move} onpointerleave={() => (hover = null)} onclick={chooseYear} style:cursor="pointer">
    <defs>
      <pattern id="ac-hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="5" stroke="#cfcbc2" stroke-width="1.2" />
      </pattern>
      <clipPath id="ac-draw"><rect x="0" y="0" width={L + (w - L) * draw.current} height={H} /></clipPath>
    </defs>
    {#if ry0 > Y0}<rect class="outr" x={L} y={T} width={Math.max(0, x(ry0 - 0.5) - L)} height={H - T - B} />{/if}
    {#if ry1 < Y1}<rect class="outr" x={x(ry1 + 0.5)} y={T} width={Math.max(0, w - R - x(ry1 + 0.5))} height={H - T - B} />{/if}
    <rect x={x(2011.5)} y={T} width={x(2013.5) - x(2011.5)} height={H - T - B} fill="url(#ac-hatch)" />
    {#each ticks as t}
      <line class="grid" x1={L} x2={w - R} y1={y(t)} y2={y(t)} />
      <text class="tick" x={L - 5} y={y(t) + 3.5} text-anchor="end">{compact(t)}</text>
    {/each}
    <line class="base" x1={L} x2={w - R} y1={H - B} y2={H - B} />
    {#each [2001, 2011, 2021] as t}
      <text class="tick" x={x(t)} y={H - 5} text-anchor="middle">{t}</text>
    {/each}
    {#if cur >= Y0 && cur <= Y1}<line class="cur" x1={x(cur)} x2={x(cur)} y1={T} y2={H - B} />{/if}
    <g clip-path="url(#ac-draw)">
      {#if app.place.hasRaw}<path class="l raw" d={line(tr.current, raw)} />{/if}
      <path class="l harm" d={line(th.current, harm)} />
    </g>
    {#if hover != null}
      {@const i = hover - Y0}
      <line class="hov" x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} />
      {#if harm[i] != null}<circle cx={x(hover)} cy={y(harm[i]!)} r="3.5" class="dot harm" />{/if}
      {#if raw[i] != null}<circle cx={x(hover)} cy={y(raw[i]!)} r="3.5" class="dot raw" />{/if}
    {/if}
  </svg>
  <p class="key">
    {#if hover != null}
      <b>{hover}</b> harmonized {fmt(harm[hover - Y0])}{app.place.hasRaw ? ` · direct splice ${fmt(raw[hover - Y0])}` : ''}
    {:else}
      <span><i class="k harm"></i>Harmonized</span>
      {#if app.place.hasRaw}<span><i class="k raw"></i>Direct splice</span>{/if}
      <span><i class="k hatch"></i>sealed test years</span>
    {/if}
  </p>
</div>

<style>
  svg { display: block; overflow: visible; }
  .grid { stroke: var(--rule-2); }
  .outr { fill: rgb(246 245 241 / 0.85); }
  .base { stroke: var(--rule); }
  .tick { fill: var(--ink-3); font-size: 10px; }
  .cur { stroke: var(--blue); stroke-dasharray: 2 3; }
  .hov { stroke: var(--ink-3); }
  .l { fill: none; stroke-width: 2.2; stroke-linejoin: round; stroke-linecap: round; }
  .l.harm { stroke: var(--ink); }
  .l.raw { stroke: var(--f3); }
  .dot.harm { fill: var(--ink); }
  .dot.raw { fill: var(--f3); }
  .key { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 6px; font-size: 11.5px; color: var(--ink-3); min-height: 18px; }
  .key span { display: inline-flex; align-items: center; gap: 5px; }
  .key b { color: var(--ink); font-weight: 600; }
  .k { width: 12px; height: 2.5px; display: inline-block; border-radius: 1px; }
  .k.harm { background: var(--ink); }
  .k.raw { background: var(--f3); }
  .k.hatch { height: 9px; width: 9px; background: repeating-linear-gradient(45deg, #cfcbc2 0 1.2px, transparent 1.2px 3.5px); }
</style>
