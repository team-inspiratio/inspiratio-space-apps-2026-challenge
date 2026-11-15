<script lang="ts">
  import { app } from '../lib/store.svelte'
  import { GRADIENT, DIV_GRADIENT } from '../lib/ramp'
  const g = $derived((void app.palette, app.layer === 'anomaly' ? DIV_GRADIENT : GRADIENT))
</script>

<div class="legend" aria-label="Map legend">
  <span class="bar" style:background={g}></span>
  {#if app.layer === 'anomaly'}
    <span class="ends"><span>¼× usual</span><span>usual</span><span>8×</span></span>
    <span class="note">Approximate, from the map grid · exact values in the card</span>
  {:else}
    <span class="ends"><span>fewer</span><span>more detections per cell</span></span>
  {/if}
</div>

<style>
  .legend { display: grid; gap: 4px; width: 230px; padding: 10px 12px; border-radius: 12px; background: rgb(255 255 255 / 0.92); box-shadow: 0 8px 24px -12px rgb(22 25 29 / 0.3); pointer-events: none; }
  .bar { height: 7px; border-radius: 4px; }
  .ends { display: flex; justify-content: space-between; font-size: 11px; color: var(--ink-3); }
  .note { font-size: 10.5px; color: var(--ink-3); }
</style>
