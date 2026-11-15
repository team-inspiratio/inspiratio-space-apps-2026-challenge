<script lang="ts">
  import { sourceLabel } from '../lib/v2/science.js'
  import { app, MONTHS, monthName, fmt, compact, touch } from '../lib/store.svelte'
  import { ramp, logRange, ZERO, GRADIENT } from '../lib/ramp'

  const YEARS = Array.from({ length: 27 }, (_, i) => 2000 + i)
  const M = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
  const idx = new Map(MONTHS.map((m, i) => [m, i]))
  const at = (y: number, m: number) => idx.get(`${y}-${String(m + 1).padStart(2, '0')}`)

  const val = (i: number) => {
    const s = app.place.series[i]
    return app.mode === 'raw' ? s.raw : s.value
  }
  // Colour range from the place's own low and high months (log), so small and large places both read well.
  const range = $derived.by(() => {
    void app.mode, app.palette
    const v = app.place.series.map((_, i) => val(i)).filter((x): x is number => x != null && x > 0).sort((a, b) => a - b)
    if (!v.length) return [1, 2]
    const lo = Math.max(0.5, v[Math.floor(v.length * 0.02)])
    const hi = Math.max(lo * 2, v[Math.floor(v.length * 0.98)])
    return [lo, hi]
  })
  const inRange = (i: number) => i >= app.range[0] && i <= app.range[1]

  // Which years burn most: annual totals of complete years in the selected range.
  const totals = $derived.by(() => {
    void app.mode, app.range
    return YEARS.map((y) => {
      let s = 0
      for (let m = 0; m < 12; m++) {
        const i = at(y, m)
        if (i == null || !inRange(i)) return null
        const v = val(i)
        if (v == null) return null
        s += v
      }
      return s
    })
  })
  const maxTotal = $derived(Math.max(1, ...totals.map((t) => t ?? 0)))
  const topYear = $derived(totals.indexOf(Math.max(...totals.map((t) => t ?? -1))))
  // Which months burn most: median of each calendar month across years in the range.
  const medians = $derived.by(() => {
    void app.mode, app.range
    return M.map((_, m) => {
      const v: number[] = []
      for (const y of YEARS) {
        const i = at(y, m)
        if (i != null && inRange(i) && y >= 2001) {
          const x = val(i)
          if (x != null) v.push(x)
        }
      }
      v.sort((a, b) => a - b)
      return v.length ? (v[(v.length - 1) >> 1] + v[v.length >> 1]) / 2 : null
    })
  })
  const topMonth = $derived(medians.indexOf(Math.max(...medians.map((t) => t ?? -1))))

  let tip = $state<{ html: string; x: number; y: number } | null>(null)
  let grid: HTMLDivElement
  let cellW = $state(20)

  function color(v: number | null | undefined) {
    if (v == null) return ''
    return v <= 0 ? ZERO : ramp(logRange(v, range[0], range[1]))
  }
  function sourceKind(s: string) {
    return s === 'snpp' ? 'obs' : s === 'noaa20_scaled' ? 'scaled' : s === 'model_terra_bridge' ? 'bridge' : s === 'mixed' ? 'mixed' : 'model'
  }
  function rowSource(y: number) {
    const counts: Record<string, number> = {}
    for (let m = 0; m < 12; m++) {
      const i = at(y, m)
      if (i == null) continue
      const k = sourceKind(app.place.series[i].source)
      counts[k] = (counts[k] ?? 0) + 1
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'model'
  }
  function show(e: MouseEvent, html: string) {
    const r = grid.getBoundingClientRect()
    const c = (e.currentTarget as HTMLElement).getBoundingClientRect()
    tip = { html, x: c.left - r.left + c.width / 2, y: c.top - r.top }
  }
  function cellTip(e: MouseEvent, i: number) {
    const p = app.place.series[i]
    const v = app.mode === 'raw' ? p.raw : p.value
    const note = app.mode === 'raw' ? (v == null ? 'No direct-splice value' : 'Direct splice') : (sourceLabel[p.source as keyof typeof sourceLabel] ?? p.source)
    const rr = app.mode === 'harm' && p.lo != null ? ` · rough range ${fmt(p.lo)}–${fmt(p.hi)}` : ''
    show(e, `<b>${monthName(p.month)}</b> · ${fmt(v)} detections<br><span>${note}${rr}${p.nrt ? ' · preliminary' : ''}</span>`)
  }
  // The selected month is marked by one moving outline, not by restyling every cell.
  const sel = $derived.by(() => {
    const m = MONTHS[app.month]
    return { r: +m.slice(0, 4) - 2000, c: +m.slice(5) - 1 }
  })
  const hl = $derived.by(() => {
    const m = app.highlight.cell
    return m ? { r: +m.slice(0, 4) - 2000, c: +m.slice(5) - 1 } : null
  })
  const ROW = 14 // 12px cell + 2px gap
</script>

<section class="cal" aria-label="Burn calendar: one row per year, one column per month">
  <div class="grid" bind:this={grid} class:sealedOn={app.highlight.sealed || app.mode === 'raw'}>
    <div class="row head" aria-hidden="true">
      <span class="yl"></span><span class="src"></span>
      {#each M as m, k}<span class="ml" class:top={k === topMonth}>{m}</span>{/each}
      <span class="tl">year</span>
    </div>
    <div class="body" bind:clientWidth={cellW}>
      {#key app.place.id}
        {#each YEARS as y, r}
          <div class="row" style:--d="{r * 16}ms" class:sealed={y === 2012 || y === 2013} class:yhl={app.highlight.cell.startsWith(String(y))}>
            {#if y === 2012 || y === 2013}<span class="seal" aria-hidden="true"></span>{/if}
            <span class="yl" class:strong={y % 5 === 1 || y === 2026}>{y % 5 === 1 || y === 2026 || y === 2012 || y === 2013 ? y : ''}</span>
            <span class="src {rowSource(y)}"></span>
            {#each M as _, m}
              {@const i = at(y, m)}
              {#if i == null}
                <span class="cell none"></span>
              {:else}
                <button
                  class="cell"
                  class:null={val(i) == null}
                  class:out={!inRange(i)}
                  style:background={color(val(i))}
                  style:--c={m}
                  onclick={() => (touch(), (app.playing = false), (app.month = i))}
                  onmouseenter={(e) => cellTip(e, i)}
                  onmouseleave={() => (tip = null)}
                  aria-label="{monthName(MONTHS[i])}: {fmt(val(i))} detections"
                ></button>
              {/if}
            {/each}
            <span class="tot" onmouseenter={(e) => totals[r] != null && show(e, `<b>${y}</b> · ${fmt(totals[r])} detections in the year`)} onmouseleave={() => (tip = null)} role="presentation">
              {#if totals[r] != null}<i style:transform="scaleX({totals[r]! / maxTotal})" class:top={r === topYear}></i>{/if}
            </span>
          </div>
        {/each}
      {/key}
      <span class="cursor" aria-hidden="true" style:transform="translate(calc(35px + {sel.c} * (100% + 2px)), {sel.r * ROW}px)"></span>
      {#if hl}<span class="cursor hl" aria-hidden="true" style:transform="translate(calc(35px + {hl.c} * (100% + 2px)), {hl.r * ROW}px)"></span>{/if}
    </div>
    <div class="row med">
      <span class="yl">median</span><span class="src none"></span>
      {#each medians as v, m}
        <span class="cell mcell" style:background={color(v)} onmouseenter={(e) => show(e, `<b>${'JFMAMJJASOND'[m]} · median</b> ${fmt(v)} detections`)} onmouseleave={() => (tip = null)} role="presentation"></span>
      {/each}
      <span class="tot"></span>
    </div>
    {#if tip}
      <div class="tip" style:left="{tip.x}px" style:top="{tip.y}px">{@html tip.html}</div>
    {/if}
  </div>

  <footer class="legend">
    <span class="ramp"><i style:background={GRADIENT}></i>fewer → more</span>
    <span><i class="bar obs"></i>observed</span>
    <span><i class="bar model"></i>estimated</span>
    <span><i class="mk"></i>busiest</span>
  </footer>
</section>

<style>
  .cal { padding: 0; }
  .grid { position: relative; display: grid; gap: 2px; }
  .body { position: relative; display: grid; gap: 2px; }
  .row { --cols: 28px 3px repeat(12, minmax(0, 1fr)) 34px; position: relative; display: grid; grid-template-columns: var(--cols); gap: 2px; align-items: center; animation: rowin 0.6s var(--ease) both; animation-delay: var(--d); }
  .row.head, .row.med { animation: none; }
  .row.med { margin-top: 6px; }
  @keyframes rowin { from { opacity: 0; transform: translateX(-6px); } }
  .yl { font-size: 10.5px; color: var(--ink-3); line-height: 1; }
  .yl.strong { color: var(--ink-2); }
  .med .yl { font-size: 9.5px; letter-spacing: 0.02em; }
  .ml { font-size: 10.5px; color: var(--ink-3); text-align: center; }
  .ml.top, .tl { color: var(--ink-2); }
  .ml.top::after { content: ''; display: block; width: 4px; height: 4px; margin: 2px auto 0; border-radius: 50%; background: #c0392b; }
  .tl { font-size: 9.5px; text-align: left; padding-left: 2px; }
  .src { height: 12px; border-radius: 1px; background: #c8c4ba; }
  .src.obs, .src.scaled { background: var(--blue); }
  .src.bridge { background: repeating-linear-gradient(0deg, #c8c4ba 0 2px, transparent 2px 4px); }
  .src.none { background: transparent; }
  .cell {
    height: 12px;
    border: 0;
    padding: 0;
    border-radius: 2px;
    cursor: pointer;
    /* Colour changes ripple across the months, left to right. */
    transition: background 0.55s var(--ease) calc(var(--c, 0) * 28ms), opacity 0.4s, transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  }
  .cell:hover { transform: scale(1.25); position: relative; z-index: 1; }
  .cell:active { transform: scale(1.4); }
  .cell.none, .mcell { cursor: default; }
  .cell.out { opacity: 0.22; }
  .cell.null { background: repeating-linear-gradient(45deg, #d9d6cf 0 1.5px, #fff 1.5px 4px) !important; }
  .tot { height: 12px; display: flex; align-items: center; }
  .tot i { display: block; height: 6px; width: 100%; border-radius: 3px; background: #bdb8ad; transform-origin: left; transition: transform 0.6s var(--ease); }
  .tot i.top { background: #c0392b; }
  .yhl .yl { color: var(--blue); font-weight: 600; }
  .cursor {
    position: absolute;
    left: 0;
    top: 0;
    width: calc((100% - 93px) / 12);
    height: 12px;
    border-radius: 3px;
    outline: 2px solid var(--ink);
    outline-offset: 1px;
    pointer-events: none;
    z-index: 4;
    transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .cursor.hl { outline-color: var(--blue); outline-offset: 2px; animation: pulse 1.6s ease-in-out infinite; }
  @keyframes pulse { 50% { outline-offset: 4px; } }
  .seal {
    position: absolute;
    left: 35px;
    right: 36px;
    top: -1px;
    bottom: -1px;
    z-index: 3;
    pointer-events: none;
    border-radius: 2px;
    background: repeating-linear-gradient(45deg, rgb(22 25 29 / 0.55) 0 1.5px, rgb(255 255 255 / 0.35) 1.5px 4px);
    clip-path: inset(0 100% 0 0);
    transition: clip-path 0.7s cubic-bezier(0.65, 0, 0.35, 1);
  }
  .sealedOn .seal { clip-path: inset(0 0 0 0); }
  .sealedOn .row.sealed .yl { color: var(--blue); font-weight: 600; }
  .tip {
    position: absolute;
    transform: translate(-50%, calc(-100% - 8px));
    background: #fff;
    border-radius: 8px;
    padding: 6px 9px;
    font-size: 12px;
    line-height: 1.45;
    white-space: nowrap;
    pointer-events: none;
    box-shadow: 0 8px 22px -8px rgb(22 25 29 / 0.3);
    z-index: 6;
  }
  .tip :global(span) { color: var(--ink-3); }
  .legend { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; margin-top: 10px; font-size: 11.5px; color: var(--ink-3); }
  .legend span { display: inline-flex; align-items: center; gap: 5px; }
  .ramp i { width: 40px; height: 7px; border-radius: 2px; display: inline-block; }
  .bar { width: 3px; height: 10px; display: inline-block; }
  .bar.obs { background: var(--blue); }
  .bar.model { background: #c8c4ba; }
  .mk { width: 6px; height: 6px; border-radius: 50%; background: #c0392b; display: inline-block; }
</style>
