<script lang="ts">
  // The one-time blind test, graded in GitHub Actions (reports/final-test.md §1). MALE, lower is better.
  let { play = false }: { play?: boolean } = $props()
  const tests = [
    { name: 'Training regions, 2012–13', lgbm: 0.258, m1s: 0.332 },
    { name: 'Three unseen regions', lgbm: 0.644, m1s: 0.857 },
  ]
  const x = (v: number) => (v / 1) * 100
  let w = $state(300)
</script>

<figure class:play title="Mean absolute log error. Source: reports/final-test.md">
  {#each tests as t, i}
    <div class="test" style:--d="{900 + i * 160}ms">
      <p>{t.name}</p>
      <div class="axis" bind:clientWidth={w}>
        <span class="seg" style:left="{x(t.lgbm)}%" style:width="{x(t.m1s - t.lgbm)}%"></span>
        <span class="dot m1s" style:--px="{t.m1s * w}px"></span>
        <span class="dot lgbm" style:--px="{t.lgbm * w}px"><b>{t.lgbm.toFixed(2)}</b></span>
      </div>
    </div>
  {/each}
  <p class="key"><span><i class="dot-k lgbm"></i>our model</span><span><i class="dot-k m1s"></i>simple ratio</span><span>error, lower is better · unseen regions are harder</span></p>
</figure>

<style>
  figure { margin: 6px 0 0; display: grid; gap: 12px; }
  .test p { font-size: 13px; color: var(--ink-2); margin-bottom: 22px; }
  .axis { position: relative; height: 14px; }
  .axis::before { content: ''; position: absolute; left: 0; right: 0; top: 6px; height: 2px; border-radius: 1px; background: rgb(22 25 29 / 0.08); }
  .seg { position: absolute; top: 6px; height: 2px; background: var(--blue); opacity: 0; transition: opacity 0.4s calc(var(--d) + 500ms); }
  .dot { position: absolute; top: 0; left: 0; width: 14px; height: 14px; margin-left: -7px; border-radius: 50%; border: 2.5px solid #fff; box-shadow: 0 1px 4px rgb(22 25 29 / 0.25); transition: transform 1.1s cubic-bezier(0.16, 1, 0.3, 1) var(--d); }
  .play .dot { transform: translateX(var(--px)); }
  .play .seg { opacity: 0.35; }
  .dot.lgbm { background: var(--blue); }
  .dot.m1s { background: #9a9fa7; }
  .dot b { position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); font-size: 12px; color: var(--blue); font-weight: 600; }
  .key { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12px; color: var(--ink-3); }
  .key span { display: inline-flex; align-items: center; gap: 5px; }
  .dot-k { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
  .dot-k.lgbm { background: var(--blue); }
  .dot-k.m1s { background: #9a9fa7; }
</style>
