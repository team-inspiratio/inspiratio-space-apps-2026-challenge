<script lang="ts">
  import { onMount } from 'svelte'
  import Lenis from 'lenis'
  import { gsap } from 'gsap'
  import { app, loadUnits, restoreHash, frame, touch, prefetch } from './lib/store.svelte'
  import { loadWorld, type WorldGrid } from './lib/worlddata'
  import MapView from './components/MapView.svelte'
  import Story from './components/Story.svelte'
  import PlaceSearch from './components/PlaceSearch.svelte'
  import Switch from './components/Switch.svelte'
  import TimeBar from './components/TimeBar.svelte'
  import ReadingCard from './components/ReadingCard.svelte'
  import CalendarCard from './components/CalendarCard.svelte'
  import Footer from './components/Footer.svelte'
  import LayersMenu from './components/LayersMenu.svelte'
  import MapLegend from './components/MapLegend.svelte'
  import Method from './components/Method.svelte'

  let world = $state.raw<WorldGrid | null>(null)
  let story: Story
  let wide = $state(true)
  let footerIn = $state(false)
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches

  // Keep the map's framing clear of the floating UI.
  $effect(() => {
    const free = app.free
    app.insets = wide
      ? { left: free ? 32 : 500, right: 412, top: 84, bottom: 108 }
      : { left: 0, right: 0, top: 64, bottom: Math.round(innerHeight * (free ? 0.56 : 0.54)) }
  })

  onMount(() => {
    history.scrollRestoration = 'manual'
    const mq = matchMedia('(min-width: 900px)')
    const setWide = () => (wide = mq.matches)
    setWide()
    mq.addEventListener('change', setWide)

    let lenis: Lenis | null = null
    if (!reduced) {
      lenis = new Lenis({ lerp: 0.09, wheelMultiplier: 0.95 })
      gsap.ticker.add((t) => lenis!.raf(t * 1000))
      gsap.ticker.lagSmoothing(0)
    }
    const onScroll = () => {
      const v = Math.min(1, scrollY / (innerHeight * 0.85))
      if (Math.abs(v - app.introP) > 0.002 || (v === 1 && app.introP !== 1)) app.introP = v
    }
    addEventListener('scroll', onScroll, { passive: true })
    onScroll()

    // Floating UI steps aside when the footer arrives.
    const fio = new IntersectionObserver(([e]) => (footerIn = e.isIntersecting), { rootMargin: '0px 0px -30% 0px' })
    const foot = document.querySelector('footer.foot')
    if (foot) fio.observe(foot)

    loadWorld().then((w) => (world = w))
    loadUnits().then(async () => {
      // Warm the story's places in the background so later steps never wait or stutter.
      const idle = (fn: () => void) => ('requestIdleCallback' in window ? (window as any).requestIdleCallback(fn, { timeout: 2500 }) : setTimeout(fn, 1200))
      idle(() => prefetch(['california', 'TENA', 'CEAS']))
      if (await restoreHash()) {
        app.skipping = true
        document.querySelector('.step.last')?.scrollIntoView({ block: 'center', behavior: 'instant' })
      }
    })
    return () => removeEventListener('scroll', onScroll)
  })

  const chrome = $derived(Math.max(0, Math.min(1, (app.introP - 0.55) / 0.4)))
</script>

<div class="stage" aria-label="Map">
  {#if world}<MapView {world} />{/if}
</div>
<div class="veil" style:opacity={wide ? Math.min(1, app.introP * 1.5) * (app.free ? 0 : 1) : 0}></div>
<div class="veil-b" style:opacity={wide || app.free ? 0 : 1}></div>

<header class="top">
  <a class="brand" href="#top" onclick={(e) => (e.preventDefault(), scrollTo({ top: 0, behavior: 'smooth' }))}>
    <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="4" cy="4" r="2.2" fill="#f7c56f" /><circle cx="10" cy="4" r="2.8" fill="#f19a45" /><circle cx="16" cy="4" r="3.3" fill="#c0392b" /><circle cx="4" cy="10" r="2.8" fill="#f19a45" /><circle cx="10" cy="10" r="3.4" fill="#c0392b" /><circle cx="16" cy="10" r="3.6" fill="#4f1325" /><circle cx="4" cy="16" r="1.6" fill="#fbe7b1" /><circle cx="10" cy="16" r="2.4" fill="#f7c56f" /><circle cx="16" cy="16" r="3" fill="#e2662d" /></svg>
    Inspiratio
  </a>
  <div class="mid chrome" style:--k={chrome}><PlaceSearch /></div>
  <div class="right chrome" style:--k={chrome}>
    <Switch
      label="Series"
      value={app.mode}
      onchange={(v) => (touch(), (app.modeByUser = true), (app.mode = v))}
      options={[
        { value: 'harm', label: 'Harmonized' },
        { value: 'raw', label: 'Direct splice' },
      ]}
    />
    <Switch
      label="Map view"
      value={app.proj}
      onchange={(v) => (touch(), frame(app.place.bbox, v))}
      options={[
        { value: 'globe', icon: 'globe', title: 'Globe' },
        { value: 'flat', icon: 'map', title: 'Flat map' },
      ]}
    />
    <LayersMenu />
  </div>
</header>

<aside class="cards chrome" class:free={app.free} class:away={footerIn} style:--k={chrome} aria-label="Selected place">
  <div class="glass"><ReadingCard /></div>
  <div class="glass"><CalendarCard /></div>
</aside>

<div class="maplegend chrome" class:away={footerIn} style:--k={chrome} style:left="{wide ? (app.free ? 32 : 500) : 12}px">
  <MapLegend />
</div>

<div class="timeline chrome" class:free={app.free} class:away={footerIn} style:--k={chrome} style:left="{wide ? (app.free ? 32 : 500) : 12}px">
  <TimeBar />
</div>

{#if app.exploring && !app.free}
  <button class="resume" onclick={() => story.resume()}>← Back to the story</button>
{/if}

<main id="top">
  <section class="intro" style:--p={app.introP}>
    <h1>
      <span class="l1">Fire, counted from space.</span>
      <span class="l2">One scale, 26 years.</span>
    </h1>
    <p>A monthly record of satellite fire detections for any place on Earth, November 2000 to October 2026.</p>
    <button class="go" onclick={() => story.skip()}>Go straight to the explorer</button>
    <span class="cue" aria-hidden="true"></span>
  </section>
  <Story bind:this={story} />
</main>

<Method />

<Footer />

<style>
  .stage { position: fixed; inset: 0; z-index: 0; background: var(--paper); }
  .veil {
    position: fixed;
    inset: 0 auto 0 0;
    width: 620px;
    z-index: 1;
    pointer-events: none;
    background: linear-gradient(90deg, rgb(246 245 241 / 0.94) 0%, rgb(246 245 241 / 0.84) 55%, rgb(246 245 241 / 0) 100%);
    transition: opacity 0.6s var(--ease);
  }
  .top {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 20;
    height: 72px;
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 16px;
    padding: 0 28px;
    pointer-events: none;
  }
  .brand { pointer-events: auto; display: inline-flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 600; letter-spacing: -0.01em; color: var(--ink); text-decoration: none; }
  .brand svg { width: 22px; height: 22px; }
  .right { justify-self: end; display: flex; gap: 8px; }
  .chrome { opacity: var(--k); transform: translateY(calc((1 - var(--k)) * -10px)); }
  .cards.chrome { transform: translateX(calc((1 - var(--k)) * 40px)); }
  .timeline.chrome { transform: translateY(calc((1 - var(--k)) * 30px)); }
  .chrome { pointer-events: auto; }
  .cards {
    position: fixed;
    right: 24px;
    top: 84px;
    bottom: 24px;
    width: 364px;
    z-index: 10;
    display: flex;
    flex-direction: column;
    gap: 12px;
    overflow-y: auto;
    scrollbar-width: none;
  }
  .glass {
    flex: none;
    border-radius: 18px;
    background: rgb(255 255 255 / 0.96);
    box-shadow: 0 1px 2px rgb(22 25 29 / 0.06), 0 16px 40px -16px rgb(22 25 29 / 0.32);
  }
  .timeline { position: fixed; right: 412px; bottom: 22px; z-index: 10; will-change: transform, opacity; }
  .cards { will-change: transform, opacity; }
  .veil-b { display: none; }
  .maplegend { position: fixed; bottom: 112px; z-index: 9; }
  @media (max-width: 899px) { .maplegend { display: none; } }
  .resume {
    position: fixed;
    left: 28px;
    top: 76px;
    z-index: 21;
    height: 34px;
    padding: 0 14px;
    border: 0;
    border-radius: 999px;
    background: var(--ink);
    color: #fff;
    font-size: 13px;
    cursor: pointer;
    box-shadow: 0 8px 24px -10px rgb(22 25 29 / 0.5);
    animation: pop 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes pop { from { opacity: 0; transform: translateY(-6px); } }
  .away { opacity: 0 !important; pointer-events: none !important; transition: opacity 0.4s !important; }
  main { position: relative; z-index: 2; pointer-events: none; }
  .intro {
    position: relative;
    height: 100vh;
    padding: 0 56px 14vh;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    gap: 20px;
    opacity: calc(1 - var(--p) * 1.6);
    transform: translateY(calc(var(--p) * -60px));
  }
  .intro > * { pointer-events: auto; }
  h1 { font-family: var(--font-cond); display: grid; gap: 0.08em; font-size: clamp(56px, 7vw, 108px); line-height: 0.95; letter-spacing: -0.045em; font-weight: 300; max-width: min(5.6em, 46vw); }
  h1 .l1 { animation: rise 1.4s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both; }
  h1 .l2 { color: var(--ink-3); animation: rise 1.4s cubic-bezier(0.16, 1, 0.3, 1) 0.38s both; }
  .intro p { max-width: 34ch; font-size: 18px; color: var(--ink-2); animation: rise 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.6s both; }
  .go {
    align-self: flex-start;
    height: 40px;
    padding: 0 18px;
    border: 0;
    border-radius: 999px;
    background: var(--ink);
    color: #fff;
    font-size: 14px;
    cursor: pointer;
    animation: rise 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.75s both;
    transition: background 0.2s, transform 0.18s;
  }
  .go:hover { background: var(--blue); }
  .go:active { transform: scale(0.97); }
  .cue { position: absolute; left: 50%; bottom: 28px; width: 1px; height: 46px; background: linear-gradient(var(--ink-3), transparent); animation: cue 2s ease-in-out infinite; pointer-events: none; }
  @keyframes rise { from { opacity: 0; transform: translateY(28px); } }
  @keyframes cue { 0%, 100% { transform: scaleY(0.4); transform-origin: top; opacity: 0.3; } 50% { transform: scaleY(1); opacity: 1; } }

  @media (max-width: 899px) {
    .top { grid-template-columns: auto 1fr; padding: 0 14px; height: 60px; }
    .right { display: none; }
    .mid { justify-self: end; }
    .veil-b {
      display: block;
      position: fixed;
      inset: auto 0 0 0;
      height: 55vh;
      z-index: 1;
      pointer-events: none;
      background: linear-gradient(0deg, rgb(246 245 241 / 0.97) 55%, rgb(246 245 241 / 0));
      transition: opacity 0.5s;
    }
    .cards { left: 10px; right: 10px; top: auto; bottom: 92px; width: auto; max-height: 50vh; opacity: 0; pointer-events: none; transform: translateY(30px); transition: opacity 0.5s var(--ease), transform 0.6s var(--ease); }
    .cards.free { opacity: 1; pointer-events: auto; transform: none; }
    .timeline { right: 10px; left: 10px !important; bottom: 10px; opacity: 0; pointer-events: none; transition: opacity 0.5s; }
    .timeline.free { opacity: 1; pointer-events: auto; }
    .intro { padding: 0 20px 12vh; }
    h1 { font-size: 46px; max-width: none; }
  }
  @media (prefers-reduced-motion: reduce) {
    h1 span, .intro p, .go, .cue { animation: none; }
  }
</style>
