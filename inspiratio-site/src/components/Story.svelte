<script lang="ts">
  import { onMount } from 'svelte'
  import { Tween } from 'svelte/motion'
  import { cubicOut } from 'svelte/easing'
  import { gsap } from 'gsap'
  import { SplitText } from 'gsap/SplitText'
  import { app, MONTHS, selectWorld, selectRegion, frame } from '../lib/store.svelte'
  import PixelFigure from './figures/PixelFigure.svelte'
  import ScoresFigure from './figures/ScoresFigure.svelte'
  import ExamFigure from './figures/ExamFigure.svelte'

  gsap.registerPlugin(SplitText)
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
  const m = (s: string) => MONTHS.indexOf(s)
  const clear = { sealed: false, sources: false, seam: false, cell: '' }

  let timers: gsap.core.Tween[] = []
  const later = (s: number, fn: () => void) => timers.push(gsap.delayedCall(reduced ? 0 : s, fn))
  function world(mode: 'harm' | 'raw') {
    app.mode = mode
    if (app.place.kind !== 'world') selectWorld({ reframe: false })
  }
  function scatter(on: boolean) {
    gsap.to(app, { scatter: on ? 1 : 0, duration: reduced ? 0 : on ? 1.7 : 1.1, ease: on ? 'power2.inOut' : 'power2.in', overwrite: true })
    if (on) gsap.fromTo(app, { scatterCurve: 0 }, { scatterCurve: 1, duration: reduced ? 0 : 1.1, delay: reduced ? 0 : 1.6, ease: 'power1.inOut' })
    else app.scatterCurve = 0
  }

  // Each step sets the real tool, then plays its one main move.
  const steps: (() => void)[] = [
    () => {
      app.highlight = { ...clear }
      world('harm')
      frame(null, 'globe')
      app.play = { to: -1, speed: 12 }
      app.playing = true
    },
    () => {
      app.playing = false
      app.highlight = { ...clear, seam: true }
      world('raw')
      app.month = m('2010-01')
      frame(null, 'flat')
      later(1.2, () => {
        app.play = { to: m('2015-12'), speed: 16 }
        app.playing = true
      })
    },
    () => {
      app.playing = false
      app.highlight = { ...clear }
      world('harm')
      app.month = m('2019-08')
      frame([12, -24, 42, 2], 'flat')
    },
    () => {
      app.playing = false
      app.highlight = { ...clear, sources: true }
      world('harm')
      app.month = m('2019-08')
      frame(null, 'flat')
      later(0.9, () => scatter(true))
    },
    () => {
      app.playing = false
      world('harm')
      app.month = m('2013-08')
      frame(null, 'flat')
      app.highlight = { ...clear }
      later(0.4, () => (app.highlight = { ...clear, sealed: true }))
      later(2.0, () => (app.highlight = { ...clear }))
    },
    () => {
      app.playing = false
      app.mode = 'harm'
      app.highlight = { ...clear, cell: '2020-09' }
      selectRegion('california', '2020-09')
    },
    () => {
      app.playing = false
      app.highlight = { ...clear }
    },
  ]

  // Big numbers count up when their step arrives.
  type Big = { to: number; dec: number; pre: string; unit: string; suffix?: string }
  const big: (Big | null)[] = [
    { to: 26, dec: 0, pre: '', unit: 'years, month by month' },
    { to: 5.7, dec: 1, pre: '×', unit: 'more detections, overnight' },
    null,
    { to: 444, dec: 0, pre: '', unit: 'million detections, cleaned', suffix: 'M' },
    { to: 22, dec: 0, pre: '−', unit: 'error against a simple ratio', suffix: '%' },
    { to: 21.9, dec: 1, pre: '', unit: 'a usual September', suffix: '×' },
    null,
  ]
  const counters = big.map(() => new Tween(0, { duration: reduced ? 0 : 1400, easing: cubicOut }))

  let els: HTMLElement[] = []
  let active = $state(-1)
  let narrow = $state(false)

  // A step only plays once the reader settles on it; fast scrolling skips the ones in between.
  let pendingStep: ReturnType<typeof setTimeout> | undefined
  function settle(i: number) {
    clearTimeout(pendingStep)
    pendingStep = setTimeout(() => go(i), reduced ? 0 : 220)
  }
  export function resume() {
    app.exploring = false
    const i = active
    active = -1
    go(i < 0 ? 0 : i)
  }

  function go(i: number) {
    if (i === active) return
    if (app.exploring && i !== steps.length - 1) {
      active = i
      app.step = i
      return
    }
    if (i === steps.length - 1) app.exploring = false
    const prev = active
    active = i
    app.step = i
    app.touched = false
    app.free = i === steps.length - 1
    timers.forEach((t) => t.kill())
    timers = []
    if (prev === 3 && i !== 3) scatter(false)
    steps[i]()
    reveal(i)
    big.forEach((b, k) => {
      if (!b) return
      if (k === 1) counters[1].set(k === i ? 1 : b.to, { duration: 0 })
      else if (k === i) counters[k].set(0, { duration: 0 }).then(() => (counters[k].target = b.to))
    })
  }

  // The seam's ×5.7 counts as playback crosses into 2014.
  $effect(() => {
    if (active !== 1) return
    if (app.month >= m('2014-01') && counters[1].target < 5.7) counters[1].target = 5.7
  })

  const splits: SplitText[] = []
  function reveal(i: number) {
    const el = els[i]
    if (!el || reduced) return
    gsap.fromTo(el.querySelectorAll('.line-mask > *'), { yPercent: 105 }, { yPercent: 0, duration: 1.1, ease: 'expo.out', stagger: 0.08, overwrite: true })
    gsap.fromTo(el.querySelectorAll('.fade-in'), { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 1, ease: 'expo.out', stagger: 0.09, delay: 0.2, overwrite: true })
  }

  export function skip() {
    if (narrow) return els.at(-1)?.scrollIntoView({ behavior: 'smooth' })
    app.skipping = true
    setTimeout(() => (app.skipping = false), 4000)
    els.at(-1)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  onMount(() => {
    narrow = matchMedia('(max-width: 899px)').matches
    for (const el of els) for (const h of el.querySelectorAll('h2')) splits.push(SplitText.create(h, { type: 'lines', mask: 'lines', linesClass: 'line-mask' }))
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (!e.isIntersecting) continue
          const i = +(e.target as HTMLElement).dataset.i!
          if (app.skipping && i !== steps.length - 1) continue
          if (i === steps.length - 1) app.skipping = false
          settle(i)
        }
      },
      { rootMargin: narrow ? '-35% 0px -55% 0px' : '-48% 0px -48% 0px' },
    )
    els.forEach((el) => io.observe(el))
    return () => {
      io.disconnect()
      splits.forEach((s) => s.revert())
    }
  })

  // Inactive steps show their final value; the active one counts.
  const fmtBig = (k: number) => {
    const b = big[k]!
    const v = active === k || counters[k].current > 0 ? counters[k].current : b.to
    return b.pre + v.toFixed(b.dec) + (b.suffix ?? '')
  }
</script>

{#snippet number(k: number)}
  {#if big[k]}
    <p class="big fade-in" aria-label="{big[k]!.pre}{big[k]!.to}{big[k]!.suffix ?? ''} {big[k]!.unit}">
      <span class="n" aria-hidden="true">{fmtBig(k)}</span><span class="u">{big[k]!.unit}</span>
    </p>
  {/if}
{/snippet}

<div class="story" class:free={app.free}>
  <section class="step" bind:this={els[0]} data-i="0" class:on={active === 0}>
    {@render number(0)}
    <h2>Twenty-six years, every month</h2>
    <p class="fade-in">Each dot is a month of fire detections. Watch the burning belts swing north and south with the seasons.</p>
  </section>

  <section class="step" bind:this={els[1]} data-i="1" class:on={active === 1}>
    {@render number(1)}
    <h2>The record breaks in 2012</h2>
    <p class="fade-in">Join the two satellite records end to end and detections jump almost sixfold. The fires didn't change. The camera did.</p>
  </section>

  <section class="step" bind:this={els[2]} data-i="2" class:on={active === 2}>
    <h2>A sharper camera counts more</h2>
    <p class="fade-in">The same fire covers more of the small 375 m VIIRS pixels than of the 1 km MODIS ones.</p>
    <div class="fade-in"><PixelFigure play={active === 2} /></div>
    <p class="tag fade-in">S-NPP stopped on 2 Nov 2026 · MODIS retires 2026–27</p>
  </section>

  <section class="step" bind:this={els[3]} data-i="3" class:on={active === 3}>
    {@render number(3)}
    <h2>Learning the conversion</h2>
    <p class="fade-in">Both satellites have flown together since 2012. We paired them cell by cell and trained LightGBM to turn MODIS counts into VIIRS counts.</p>
    <div class="fade-in"><ScoresFigure play={active === 3} /></div>
  </section>

  <section class="step" bind:this={els[4]} data-i="4" class:on={active === 4}>
    {@render number(4)}
    <h2>Two sealed years, one exam</h2>
    <p class="fade-in">2012 and 2013 stayed locked until the model was frozen. Then a cloud grader scored it, once.</p>
    <div class="fade-in"><ExamFigure play={active === 4} /></div>
  </section>

  <section class="step" bind:this={els[5]} data-i="5" class:on={active === 5}>
    {@render number(5)}
    <h2>California, September 2020</h2>
    <p class="fade-in">The August Complex, the Creek Fire and dozens more burned at once. Against nineteen earlier Septembers, nothing comes close.</p>
  </section>

  <section class="step last" bind:this={els[6]} data-i="6" class:on={active === 6}>
    <h2>Now, any place</h2>
    <p class="fade-in">Search a region, draw a box on the map, and download its record.</p>
  </section>
</div>

<style>
  .story { position: relative; z-index: 2; pointer-events: none; }
  .step {
    min-height: 100vh;
    width: min(460px, 100%);
    padding: 0 0 0 56px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 16px;
    opacity: 0.15;
    transition: opacity 0.7s var(--ease);
  }
  .step.on { opacity: 1; }
  .step > * { pointer-events: auto; }
  .step.last { min-height: 150vh; justify-content: flex-start; padding-top: 42vh; }
  .free .step.last { opacity: 0; transition: opacity 0.5s; }
  h2 { font-size: 40px; line-height: 1.04; letter-spacing: -0.03em; font-weight: 500; }
  p { font-size: 17px; line-height: 1.5; color: var(--ink-2); max-width: 36ch; }
  .big { display: grid; gap: 4px; margin-bottom: 6px; color: var(--ink); }
  .big .n { font-family: var(--font-cond); font-size: clamp(88px, 10vw, 156px); font-weight: 300; letter-spacing: -0.06em; line-height: 0.86; }
  .big .u { font-size: 14px; color: var(--ink-3); letter-spacing: 0; padding-left: 6px; }
  .big .n { font-variant-numeric: tabular-nums; }
  .tag { font-size: 12.5px; color: var(--ink-3); }
  @media (max-width: 899px) {
    .step { min-height: 85vh; padding: 0 20px 6vh; width: 100%; justify-content: flex-end; }
    .step.last { min-height: 85vh; padding-top: 0; }
    h2 { font-size: 28px; }
    p { font-size: 15.5px; }
    .big .n { font-size: 56px; }
    .step { opacity: 1; gap: 10px; }
    .tag { display: none; }
  }
</style>
