<script lang="ts">
  // Validation error of the four methods, global run (reports/global-scores.md §1). Lower is better.
  let { play = false }: { play?: boolean } = $props()
  const rows = [
    { name: 'LightGBM', v: 0.534 },
    { name: 'Simple ratio', v: 0.619 },
    { name: 'Quantile mapping', v: 0.68 },
    { name: 'No conversion', v: 2.03 },
  ]
</script>

<figure class:play title="Mean absolute log error on the validation years (2014–17), global run. Source: reports/global-scores.md">
  {#each rows as r, i}
    <div class="row" style:--d="{i * 110}ms">
      <span class="n" class:best={i === 0}>{r.name}</span>
      <span class="bar"><i style:width="{(r.v / 2.1) * 100}%" class:best={i === 0}></i></span>
      <span class="v">{r.v.toFixed(2)}</span>
    </div>
  {/each}
  <figcaption>Validation error, lower is better</figcaption>
</figure>

<style>
  figure { margin: 6px 0 0; display: grid; gap: 7px; }
  .row { display: grid; grid-template-columns: 118px 1fr 36px; gap: 10px; align-items: center; font-size: 13px; }
  .n { color: var(--ink-2); }
  .n.best { color: var(--ink); font-weight: 600; }
  .bar { height: 8px; border-radius: 4px; background: rgb(22 25 29 / 0.06); overflow: hidden; }
  .bar i { display: block; height: 100%; border-radius: 4px; background: #bdb8ad; transform: scaleX(0); transform-origin: left; transition: transform 0.9s cubic-bezier(0.16, 1, 0.3, 1) var(--d); }
  .bar i.best { background: var(--blue); }
  .play .bar i { transform: scaleX(1); }
  .v { text-align: right; color: var(--ink-3); font-size: 12px; }
  figcaption { font-size: 12px; color: var(--ink-3); margin-top: 2px; }
</style>
