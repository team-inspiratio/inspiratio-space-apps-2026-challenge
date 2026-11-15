<script lang="ts">
  import { app, MONTHS, LAST, monthName, touch } from '../lib/store.svelte'
  import { LUT, logRange } from '../lib/ramp'
  import Icon from './Icon.svelte'

  // The timeline is itself a chart of the place in view (one bar per month), with a date range on it.
  let w = $state(700)
  const H = 34
  let cv: HTMLCanvasElement
  let timer: ReturnType<typeof setInterval> | null = null
  const first = MONTHS.indexOf('2001-01')
  const s0 = MONTHS.indexOf('2012-01')
  let presets = $state(false)

  const x = (i: number) => (i / (MONTHS.length - 1)) * w

  // Bars are painted only when the place, mode, palette or width changes, never per month.
  $effect(() => {
    const vals = app.place.series.map((s) => (app.mode === 'raw' ? s.raw : s.value))
    void app.palette
    if (!cv || !w) return
    const dpr = Math.min(2, devicePixelRatio)
    cv.width = Math.round(w * dpr)
    cv.height = H * dpr
    const g = cv.getContext('2d')!
    g.setTransform(dpr, 0, 0, dpr, 0, 0)
    g.clearRect(0, 0, w, H)
    const v = vals.filter((x): x is number => x != null && x > 0).sort((a, b) => a - b)
    const lo = v.length ? Math.max(0.5, v[Math.floor(v.length * 0.02)]) : 1
    const hi = v.length ? v[v.length - 1] : 2
    const bw = w / MONTHS.length
    vals.forEach((val, i) => {
      if (val != null && val > 0) {
        const t = logRange(val, lo, hi)
        const h = 3 + (H - 3) * t
        g.fillStyle = LUT[Math.round(t * 255)]
        g.fillRect(i * bw, H - h, Math.max(0.6, bw - 0.7), h)
      } else if (i >= s0 && i < s0 + 24) {
        g.fillStyle = 'rgba(150,145,135,0.35)'
        for (let k = 0; k < H; k += 4) g.fillRect(i * bw, k, Math.max(0.6, bw - 0.7), 1.2)
      }
    })
  })

  $effect(() => {
    const speed = app.play.speed || 12
    if (app.playing) {
      timer && clearInterval(timer)
      timer = setInterval(() => {
        const [a, b] = app.range
        if (app.play.to >= 0 && app.month >= app.play.to) {
          app.playing = false
          app.play = { to: -1, speed: 12 }
          return
        }
        app.month = app.month >= b || app.month < a ? Math.max(a, a === 0 ? first : a) : app.month + 1
      }, 1000 / speed)
    } else if (timer) {
      clearInterval(timer)
      timer = null
    }
    return () => timer && clearInterval(timer)
  })

  let drag: 'head' | 'from' | 'to' | null = null
  let track: HTMLDivElement
  function at(ev: PointerEvent) {
    const r = track.getBoundingClientRect()
    return Math.max(0, Math.min(LAST, Math.round(((ev.clientX - r.left) / r.width) * LAST)))
  }
  function down(ev: PointerEvent, what: 'head' | 'from' | 'to') {
    ev.stopPropagation()
    touch()
    app.playing = false
    drag = what
    track.setPointerCapture(ev.pointerId)
    move(ev)
  }
  function move(ev: PointerEvent) {
    if (!drag) return
    const i = at(ev)
    if (drag === 'head') app.month = i
    else if (drag === 'from') app.range = [Math.min(i, app.range[1] - 1), app.range[1]]
    else app.range = [app.range[0], Math.max(i, app.range[0] + 1)]
  }
  function keys(ev: KeyboardEvent) {
    const d = ev.key === 'ArrowLeft' ? -1 : ev.key === 'ArrowRight' ? 1 : ev.key === 'PageDown' ? -12 : ev.key === 'PageUp' ? 12 : 0
    if (!d) return
    ev.preventDefault()
    touch()
    app.month = Math.max(0, Math.min(LAST, app.month + d))
  }
  function preset(a: string, b: string) {
    touch()
    app.range = [Math.max(0, MONTHS.indexOf(a)), MONTHS.indexOf(b) < 0 ? LAST : MONTHS.indexOf(b)]
    if (app.month < app.range[0] || app.month > app.range[1]) app.month = app.range[1]
    presets = false
  }
  const ticks = [2001, 2006, 2011, 2016, 2021, 2026].map((y) => MONTHS.indexOf(`${y}-01`))
  const full = $derived(app.range[0] === 0 && app.range[1] === LAST)
  const rangeLabel = $derived(full ? 'All years' : `${monthName(MONTHS[app.range[0]])} – ${monthName(MONTHS[app.range[1]])}`)
</script>

<svelte:window onpointerdown={(e) => presets && !(e.target as HTMLElement).closest('.range') && (presets = false)} />

<div class="bar">
  <button class="play" onclick={() => (touch(), (app.play = { to: -1, speed: 12 }), (app.playing = !app.playing))} aria-label={app.playing ? 'Pause' : 'Play through the months'}>
    <Icon name={app.playing ? 'pause' : 'play'} size={15} />
  </button>
  <div
    class="track"
    bind:this={track}
    bind:clientWidth={w}
    role="slider"
    tabindex="0"
    aria-label="Month"
    aria-valuemin="0"
    aria-valuemax={LAST}
    aria-valuenow={app.month}
    aria-valuetext={monthName(MONTHS[app.month], true)}
    onpointerdown={(e) => down(e, 'head')}
    onpointermove={move}
    onpointerup={() => (drag = null)}
    onkeydown={keys}
  >
    <canvas bind:this={cv} style:width="{w}px" style:height="{H}px"></canvas>
    <div class="veil" style:transform="translateX({x(app.month) + 1}px)"></div>
    <div class="out l" style:width="{x(app.range[0])}px"></div>
    <div class="out r" style:width="{w - x(app.range[1])}px"></div>
    <div class="head" style:transform="translateX({x(app.month)}px)"><span class="bubble">{monthName(MONTHS[app.month])}</span></div>
    <button class="h" aria-label="Range start: {monthName(MONTHS[app.range[0]])}" style:transform="translateX({x(app.range[0])}px)" onpointerdown={(e) => down(e, 'from')}></button>
    <button class="h" aria-label="Range end: {monthName(MONTHS[app.range[1]])}" style:transform="translateX({x(app.range[1])}px)" onpointerdown={(e) => down(e, 'to')}></button>
    <div class="ticks" aria-hidden="true">
      {#each ticks as t}<span style:transform="translateX({x(t)}px)">{MONTHS[t].slice(0, 4)}</span>{/each}
    </div>
  </div>
  <div class="range">
    <button class="rl" class:set={!full} onclick={() => (presets = !presets)} aria-expanded={presets}>{rangeLabel}</button>
    {#if presets}
      <div class="menu">
        <button onclick={() => preset('2000-11', '2026-10')}>All years</button>
        <button onclick={() => preset('2021-11', '2026-10')}>Last 5 years</button>
        <button onclick={() => preset('2000-11', '2011-12')}>MODIS era, to 2011</button>
        <button onclick={() => preset('2014-01', '2026-10')}>VIIRS observed, from 2014</button>
        <p>Or drag the small blue handles under the bars.</p>
      </div>
    {/if}
  </div>
  <output class="label">{monthName(MONTHS[app.month])}</output>
</div>

<style>
  .bar {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 16px 10px 12px;
    border-radius: 22px;
    background: rgb(255 255 255 / 0.96);
    box-shadow: 0 1px 2px rgb(22 25 29 / 0.06), 0 14px 36px -14px rgb(22 25 29 / 0.32);
  }
  .play {
    width: 40px;
    height: 40px;
    flex: none;
    display: grid;
    place-items: center;
    border: 0;
    border-radius: 50%;
    background: var(--ink);
    color: #fff;
    cursor: pointer;
    transition: transform 0.18s var(--ease), background 0.2s;
  }
  .play:hover { background: var(--blue); }
  .play:active { transform: scale(0.94); }
  .track { position: relative; flex: 1; min-width: 0; height: 54px; cursor: ew-resize; touch-action: none; outline: none; overflow: visible; }
  .track:focus-visible { outline: 2px solid var(--blue); outline-offset: 4px; border-radius: 4px; }
  canvas { position: absolute; left: 0; top: 4px; display: block; }
  .veil { position: absolute; left: 0; top: 4px; width: 100%; height: 34px; background: rgb(255 255 255 / 0.6); pointer-events: none; will-change: transform; }
  .out { position: absolute; top: 4px; height: 34px; background: rgb(246 245 241 / 0.88); pointer-events: none; }
  .out.l { left: 0; }
  .out.r { right: 0; }
  .head { position: absolute; left: 0; top: 0; width: 1.5px; height: 40px; background: var(--ink); pointer-events: none; will-change: transform; }
  .bubble { position: absolute; bottom: 46px; left: 50%; transform: translateX(-50%); padding: 3px 8px; border-radius: 6px; background: var(--ink); color: #fff; font-size: 11.5px; white-space: nowrap; opacity: 0; transition: opacity 0.2s; }
  .track:active .bubble { opacity: 1; }
  .h { position: absolute; left: -7px; top: 38px; width: 14px; height: 14px; padding: 0; border: 0; background: transparent; cursor: ew-resize; will-change: transform; }
  .h::before { content: ''; position: absolute; left: 5px; top: 0; width: 4px; height: 10px; border-radius: 2px; background: var(--blue); }
  .ticks { position: absolute; left: 0; top: 41px; width: 100%; height: 12px; font-size: 10.5px; color: var(--ink-3); pointer-events: none; }
  .ticks span { position: absolute; left: 6px; top: 0; }
  .range { position: relative; flex: none; }
  .rl { height: 30px; padding: 0 10px; border: 0; border-radius: 999px; background: var(--paper); font-size: 12.5px; font-weight: 500; color: var(--ink-2); cursor: pointer; white-space: nowrap; }
  .rl.set { background: var(--blue-2); color: var(--blue); }
  .menu { position: absolute; right: 0; bottom: 40px; width: 230px; padding: 6px; border-radius: 14px; background: #fff; box-shadow: 0 18px 44px -16px rgb(22 25 29 / 0.4); animation: up 0.25s var(--ease); z-index: 3; }
  @keyframes up { from { opacity: 0; transform: translateY(6px); } }
  .menu button { display: block; width: 100%; padding: 8px 10px; border: 0; border-radius: 9px; background: transparent; font-size: 13.5px; text-align: left; cursor: pointer; }
  .menu button:hover { background: var(--blue-2); color: var(--blue); }
  .menu p { padding: 6px 10px 4px; font-size: 12px; color: var(--ink-3); }
  .label { min-width: 74px; text-align: right; font-size: 16px; font-weight: 500; letter-spacing: -0.01em; }
  @media (max-width: 899px) {
    .bar { gap: 10px; padding: 10px 12px 8px 8px; }
    .play { width: 34px; height: 34px; }
    .range { display: none; }
    .label { min-width: 60px; font-size: 14px; }
  }
</style>
