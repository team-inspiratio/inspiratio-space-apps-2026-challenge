<script lang="ts">
  import { onMount } from 'svelte'
  const REPO = 'https://github.com/team-inspiratio/inspiratio-space-apps-2026-challenge'

  // Blind test error per region (MALE, lower is better). Source: reports/final-test.md, section 2.
  const regions = [
    { name: 'Southern Africa', test: 1, lgbm: 0.193, m1s: 0.249 },
    { name: 'California', test: 1, lgbm: 0.282, m1s: 0.387 },
    { name: 'Córdoba', test: 1, lgbm: 0.298, m1s: 0.361 },
    { name: 'N. Australia', test: 2, lgbm: 0.321, m1s: 0.424 },
    { name: 'Indo-Gangetic Plain', test: 2, lgbm: 0.47, m1s: 0.767 },
    { name: 'Central Siberia', test: 2, lgbm: 1.142, m1s: 1.381 },
  ]
  const MAX = 1.45
  const steps = [
    ['529 M', 'raw satellite fire detections, Terra, Aqua, S-NPP and NOAA-20'],
    ['444 M', 'after quality control: vegetation fires only, confidence thresholds, duplicates merged, static heat sources masked'],
    ['0.25° × month', '278,000 cells, 312 months, 86.8 M cell-months'],
    ['2014–2021', 'paired Aqua and S-NPP months used for training; 2012–13 kept sealed'],
    ['LightGBM', 'MODIS inputs only: no year, region or VIIRS value as input'],
    ['Frozen, graded once', 'sealed 2012–13 and three unseen regions, in the cloud'],
  ]
  let el: HTMLElement
  let shown = $state(false)
  onMount(() => {
    const io = new IntersectionObserver(([e]) => e.isIntersecting && ((shown = true), io.disconnect()), { threshold: 0.15 })
    io.observe(el)
    return () => io.disconnect()
  })
</script>

<section class="method" id="method" bind:this={el} class:shown>
  <header>
    <p class="kicker">Method & evidence</p>
    <h2>How the record was made, and how we know it holds</h2>
  </header>

  <div class="cols">
    <div class="col">
      <h3>The pipeline</h3>
      <ol class="steps">
        {#each steps as [k, v], i}
          <li style:--d="{i * 80}ms"><b>{k}</b><span>{v}</span></li>
        {/each}
      </ol>
    </div>

    <div class="col">
      <h3>The blind test, region by region</h3>
      <div class="chart" role="img" aria-label="Blind-test error by region: the model beats the simple ratio everywhere; unseen regions are harder.">
        {#each regions as r, i}
          <div class="rrow" class:t2={r.test === 2} style:--d="{300 + i * 90}ms">
            <span class="rn">{r.name}{#if r.test === 2}<em>unseen</em>{/if}</span>
            <span class="track">
              <i class="gap" style:left="{(r.lgbm / MAX) * 100}%" style:width="{((r.m1s - r.lgbm) / MAX) * 100}%"></i>
              <i class="dot m" style:left="{(r.m1s / MAX) * 100}%"></i>
              <i class="dot l" style:left="{(r.lgbm / MAX) * 100}%"></i>
            </span>
            <span class="rv">{r.lgbm.toFixed(2)}</span>
          </div>
        {/each}
        <p class="key"><span><i class="dot l"></i>our model</span><span><i class="dot m"></i>simple ratio</span><span>error (MALE), lower is better</span></p>
      </div>
      <p class="note">Graded once by a GitHub Actions workflow on data no one had seen. Training regions: 22% lower error than the simple ratio. Unseen regions: 25% lower, but errors about 2.5 times larger.</p>
    </div>

    <div class="col">
      <h3>Limits, plainly</h3>
      <ul class="limits">
        <li><b>New ecosystems are harder.</b> Boreal forest (Central Siberia) has the largest errors; boreal and Middle East regions are flagged as low confidence.</li>
        <li><b>Early months are rougher.</b> Nov 2000 – Sep 2002 rely on Terra alone.</li>
        <li><b>Recent months may change.</b> Near-real-time VIIRS from Aug 2026 will be revised by NASA.</li>
        <li><b>Ranges are rough.</b> The “rough range” shows model stability, not a confidence interval.</li>
        <li><b>Detections, not fires.</b> Values count satellite fire detections, not fire events, burned area or danger.</li>
      </ul>
      <p class="links">
        <a href="{REPO}/blob/main/reports/final-test.md" target="_blank" rel="noreferrer">Final test report</a>
        <a href="{REPO}/blob/main/reports/validation.md" target="_blank" rel="noreferrer">Validation report</a>
        <a href="{REPO}/blob/main/docs/data-card.md" target="_blank" rel="noreferrer">Data card</a>
      </p>
    </div>
  </div>
</section>

<style>
  .method { position: relative; z-index: 3; background: var(--paper); padding: 96px 32px 72px; border-top: 1px solid var(--rule); }
  header { max-width: 760px; margin-bottom: 40px; }
  .kicker { font-size: 13px; color: var(--ink-3); margin-bottom: 10px; }
  h2 { font-size: 40px; line-height: 1.05; letter-spacing: -0.03em; font-weight: 500; }
  .cols { display: grid; grid-template-columns: 1fr 1.2fr 1fr; gap: 40px; max-width: 1400px; }
  h3 { font-size: 15px; font-weight: 600; margin-bottom: 16px; }
  .steps { list-style: none; margin: 0; padding: 0; display: grid; gap: 0; counter-reset: s; }
  .steps li { display: grid; gap: 2px; padding: 12px 0 12px 16px; border-left: 2px solid var(--rule); position: relative; opacity: 0; transform: translateY(8px); transition: opacity 0.6s var(--ease) var(--d), transform 0.8s var(--ease) var(--d); }
  .steps li::before { content: ''; position: absolute; left: -5px; top: 17px; width: 8px; height: 8px; border-radius: 50%; background: var(--paper); border: 2px solid var(--ink); }
  .steps li:last-child::before { background: var(--blue); border-color: var(--blue); }
  .steps b { font-size: 18px; font-weight: 500; letter-spacing: -0.01em; }
  .steps span { font-size: 13px; color: var(--ink-2); }
  .shown .steps li, .shown .rrow { opacity: 1; transform: none; }
  .chart { display: grid; gap: 10px; }
  .rrow { display: grid; grid-template-columns: 150px 1fr 40px; gap: 12px; align-items: center; opacity: 0; transform: translateY(8px); transition: opacity 0.6s var(--ease) var(--d), transform 0.8s var(--ease) var(--d); }
  .rn { font-size: 13.5px; }
  .rn em { font-style: normal; margin-left: 6px; font-size: 11px; color: #8a6200; background: #fff3d6; border-radius: 999px; padding: 1px 7px; }
  .track { position: relative; height: 14px; }
  .track::before { content: ''; position: absolute; left: 0; right: 0; top: 6px; height: 2px; background: rgb(22 25 29 / 0.08); border-radius: 1px; }
  .gap { position: absolute; top: 6px; height: 2px; background: var(--blue); opacity: 0.3; }
  .dot { position: absolute; top: 1px; width: 12px; height: 12px; margin-left: -6px; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 1px 3px rgb(22 25 29 / 0.25); }
  .dot.l { background: var(--blue); }
  .dot.m { background: #9a9fa7; }
  .rv { font-size: 13px; color: var(--blue); font-weight: 600; text-align: right; }
  .key { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12px; color: var(--ink-3); margin-top: 4px; }
  .key span { display: inline-flex; align-items: center; gap: 6px; }
  .key .dot { position: static; margin: 0; width: 10px; height: 10px; }
  .note { margin-top: 16px; font-size: 13.5px; color: var(--ink-2); line-height: 1.55; }
  .limits { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; font-size: 13.5px; color: var(--ink-2); line-height: 1.5; }
  .limits b { color: var(--ink); font-weight: 600; }
  .links { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 20px; font-size: 13.5px; }
  @media (max-width: 1100px) { .cols { grid-template-columns: 1fr; } }
  @media (max-width: 899px) { .method { padding: 64px 20px 48px; } h2 { font-size: 28px; } .rrow { grid-template-columns: 120px 1fr 36px; } }
  @media (prefers-reduced-motion: reduce) { .steps li, .rrow { opacity: 1; transform: none; transition: none; } }
</style>
