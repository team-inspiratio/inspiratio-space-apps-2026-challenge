<script lang="ts">
  import { Tween } from 'svelte/motion'
  import { cubicOut } from 'svelte/easing'
  import { anomaly, sourceLabel } from '../lib/v2/science.js'
  import { app, MONTHS, AS_OF, monthName, fmt, touch } from '../lib/store.svelte'
  import { describe, loadPoints, geo } from '../lib/geo'

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
  const dur = reduced ? 0 : 900

  const p = $derived(app.place.series[app.month])
  const month = $derived(MONTHS[app.month])
  const a = $derived(anomaly(app.place.series, month, AS_OF, app.baseline) as any)
  const raw = $derived(app.mode === 'raw')
  const shownRaw = $derived(raw ? p.raw : (a.value ?? p.value))
  const missing = $derived(shownRaw == null)
  const shown = $derived(shownRaw ?? 0)
  const sealedMonth = $derived(month >= '2012-01' && month <= '2013-12')
  let where = $state('')
  $effect(() => {
    const b = app.place.kind === 'box' ? app.place.bbox : null
    where = ''
    if (b) loadPoints().then(() => (where = describe(b as [number, number, number, number])))
    void geo
  })

  const value = new Tween(0, { duration: dur, easing: cubicOut })
  // Numbers roll from the previous value, not from zero.
  const ratio = new Tween(1, { duration: dur + 300, easing: cubicOut })
  $effect(() => {
    value.target = shown
  })
  $effect(() => {
    ratio.target = a.ratio ?? 1
  })

  const refs = $derived(
    (a.ref_years as number[]).map((y) => ({ y, v: app.place.series.find((s) => s.month === `${y}${month.slice(4)}`)!.value as number })),
  )
  const all = $derived([...refs.map((r) => r.v), a.value ?? 0].filter((v) => v > 0))
  const lo = $derived(Math.max(0.5, Math.min(...all) * 0.8))
  const hi = $derived(Math.max(...all) * 1.15 + 1)
  const sx = (v: number) => (Math.log(Math.max(v, lo)) - Math.log(lo)) / (Math.log(hi) - Math.log(lo))

  const verdict = $derived(
    raw && missing
      ? sealedMonth
        ? 'No direct-splice value: 2012–13 stayed sealed for the blind test'
        : 'No direct-splice value this month (missing satellite days)'
      : raw
      ? 'Direct splice: raw counts, not comparable across 2012'
      : a.status === 'ok'
        ? a.level === 'high'
          ? 'Unusually high for the season'
          : a.level === 'low'
            ? 'Unusually low for the season'
            : 'A usual month for the season'
        : a.status === 'insufficient_history'
          ? 'Too few earlier years to judge'
          : a.status === 'incomplete_coverage'
            ? 'Incomplete satellite coverage this month'
            : a.status === 'no_data'
              ? 'No data this month'
              : 'No earlier years to compare',
  )
  const showRatio = $derived(!raw && a.ratio != null && a.status !== 'no_data')
  let info = $state(false)
</script>

<section class="card" class:high={!raw && a.level === 'high'} class:low={!raw && a.level === 'low'} aria-live="polite">
  <header>
    <div class="where">
      <h2>{app.place.label}</h2>
      {#if where}<p class="near">{where}</p>{/if}
      <p>{monthName(month, true)}{raw ? ' · direct splice' : ''}</p>
    </div>
    <button class="i" aria-label="About this reading" aria-expanded={info} onclick={() => (info = !info)}>i</button>
  </header>

  <div class="nums">
    {#if missing}
      <p class="big none">—</p>
    {:else}
      <p class="big">{fmt(value.current)}<span>detections</span></p>
    {/if}
    {#if showRatio}
      <p class="ratio"><b>{ratio.current.toFixed(1)}×</b> a usual {monthName(month, true).split(' ')[0]}</p>
    {/if}
  </div>
  <p class="verdict">{verdict}</p>

  {#if !raw && refs.length}
    {#key app.place.id + month}
      <svg class="strip" viewBox="0 0 300 34" preserveAspectRatio="none" aria-hidden="true">
        <line x1="0" x2="300" y1="26" y2="26" />
        {#each refs as r, i}
          <circle cx={sx(r.v) * 300} cy={26 - ((i * 7) % 3) * 4} r="3" style:animation-delay="{i * 25}ms" />
        {/each}
        {#if a.value != null}<circle class="now" cx={sx(a.value) * 300} cy="20" r="5.5" style:animation-delay="{refs.length * 25 + 150}ms" />{/if}
      </svg>
    {/key}
  {/if}

  {#if info}
    <p class="more">
      VIIRS-equivalent fire detections in this area for the month ({sourceLabel[p.source as keyof typeof sourceLabel] ?? p.source}{p.nrt ? ', preliminary' : ''}).
      {#if p.lo != null && p.hi != null}Rough range {fmt(p.lo)}–{fmt(p.hi)}.{/if}
      {#if a.n_ref}Compared with the median of the same month in {a.n_ref} earlier years (dots).{/if}
      {#if app.place.lowConfidence} Low confidence: this area includes ecosystems or latitudes the model did not train on.{/if}
    </p>
    <div class="base">
      <span>Compare with</span>
      <button class:on={app.baseline === 'all'} onclick={() => (touch(), (app.baseline = 'all'))}>all years since 2001</button>
      <button class:on={app.baseline === 'snpp'} onclick={() => (touch(), (app.baseline = 'snpp'))}>VIIRS-observed years only</button>
    </div>
  {/if}
  {#if app.place.lowConfidence && !info}<p class="flag">Low confidence area</p>{/if}
</section>

<style>
  .card { padding: 20px 22px 18px; }
  header { display: flex; justify-content: space-between; align-items: start; gap: 12px; }
  h2 { font-size: 18px; font-weight: 600; letter-spacing: -0.01em; line-height: 1.2; }
  .where p { font-size: 13px; color: var(--ink-3); margin-top: 2px; }
  .i { width: 22px; height: 22px; flex: none; border-radius: 50%; border: 1px solid var(--rule); background: transparent; font-size: 12px; font-weight: 600; color: var(--ink-3); cursor: pointer; }
  .nums { margin-top: 14px; }
  .big { font-size: 44px; font-weight: 300; letter-spacing: -0.035em; line-height: 1; }
  .big span { font-size: 14px; font-weight: 400; letter-spacing: 0; color: var(--ink-3); margin-left: 8px; }
  .ratio { margin-top: 8px; font-size: 15px; color: var(--ink-2); }
  .ratio b { font-weight: 600; color: var(--ink); font-size: 20px; letter-spacing: -0.02em; }
  .high .ratio b { color: #a5361b; }
  .low .ratio b { color: var(--blue); }
  .verdict { margin-top: 4px; font-size: 13px; color: var(--ink-3); }
  .high .verdict { color: #a5361b; }
  .low .verdict { color: var(--blue); }
  .strip { width: 100%; height: 34px; margin-top: 12px; overflow: visible; }
  .strip line { stroke: var(--rule); }
  .strip circle { fill: #bdb8ad; animation: drop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both; }
  .strip circle.now { fill: #c0392b; stroke: #fff; stroke-width: 1.5; }
  .low .strip circle.now { fill: var(--blue); }
  @keyframes drop { from { opacity: 0; transform: translateY(-14px); } }
  .near { color: var(--ink-2) !important; }
  .big.none { color: var(--ink-3); }
  .base { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 10px; font-size: 12px; color: var(--ink-3); }
  .base button { border: 0; border-radius: 999px; padding: 4px 9px; background: var(--paper); font-size: 12px; color: var(--ink-2); cursor: pointer; }
  .base button.on { background: var(--ink); color: #fff; }
  .more { margin-top: 12px; font-size: 12.5px; line-height: 1.5; color: var(--ink-2); }
  .flag { margin-top: 10px; display: inline-block; font-size: 12px; color: #6b4b00; background: #fff3d6; border-radius: 999px; padding: 3px 10px; }
  @media (prefers-reduced-motion: reduce) { .strip circle { animation: none; } }
</style>
