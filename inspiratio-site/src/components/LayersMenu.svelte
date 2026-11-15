<script lang="ts">
  import { app, touch } from '../lib/store.svelte'
  import { GRADIENT, DIV_GRADIENT, PALETTES } from '../lib/ramp'
  import Icon from './Icon.svelte'

  let open = $state(false)
  const grad = (p: keyof typeof PALETTES) => `linear-gradient(90deg, ${PALETTES[p].join(', ')})`
</script>

<svelte:window onpointerdown={(e) => open && !(e.target as HTMLElement).closest('.layers') && (open = false)} />

<div class="layers">
  <button class="trigger" aria-expanded={open} aria-label="Map layers and colours" onclick={() => (open = !open)}>
    <span class="sw" style:background={app.layer === 'anomaly' ? DIV_GRADIENT : GRADIENT}></span>
    <Icon name="caret" size={12} />
  </button>
  {#if open}
    <div class="menu">
      <p class="h">Map shows</p>
      <button class:on={app.layer === 'fire'} onclick={() => (touch(), (app.layer = 'fire'))}>
        <span class="sw big" style:background={GRADIENT}></span>
        <span><b>Fire activity</b><br />detections per cell</span>
      </button>
      <button class:on={app.layer === 'anomaly'} onclick={() => (touch(), (app.layer = 'anomaly'), (app.mode = 'harm'))}>
        <span class="sw big" style:background={DIV_GRADIENT}></span>
        <span><b>Compared with usual</b><br />this month vs the same month in earlier years</span>
      </button>
      <p class="h">Colours</p>
      <button class:on={app.palette === 'fire'} onclick={() => (touch(), (app.palette = 'fire'))}>
        <span class="sw big" style:background={grad('fire')}></span>
        <span><b>Ember</b></span>
      </button>
      <button class:on={app.palette === 'cividis'} onclick={() => (touch(), (app.palette = 'cividis'))}>
        <span class="sw big" style:background={grad('cividis')}></span>
        <span><b>Cividis</b><br />designed for colour-vision deficiency</span>
      </button>
    </div>
  {/if}
</div>

<style>
  .layers { position: relative; }
  .trigger {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 36px;
    padding: 0 10px 0 12px;
    border: 0;
    border-radius: 999px;
    background: rgb(255 255 255 / 0.96);
    box-shadow: 0 1px 2px rgb(22 25 29 / 0.06), 0 8px 24px -10px rgb(22 25 29 / 0.25);
    cursor: pointer;
    color: var(--ink-2);
  }
  .sw { width: 28px; height: 8px; border-radius: 4px; display: inline-block; flex: none; }
  .sw.big { width: 36px; height: 10px; margin-top: 4px; }
  .menu {
    position: absolute;
    right: 0;
    top: 44px;
    width: 290px;
    padding: 6px;
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 24px 60px -20px rgb(22 25 29 / 0.4);
    animation: drop 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    z-index: 30;
  }
  @keyframes drop { from { opacity: 0; transform: translateY(-4px) scale(0.98); } }
  .h { padding: 8px 10px 4px; font-size: 11.5px; color: var(--ink-3); }
  .menu button { display: flex; align-items: flex-start; gap: 10px; width: 100%; padding: 8px 10px; border: 0; border-radius: 10px; background: transparent; text-align: left; font-size: 12.5px; line-height: 1.35; color: var(--ink-3); cursor: pointer; }
  .menu button b { font-size: 13.5px; font-weight: 500; color: var(--ink); }
  .menu button:hover { background: var(--paper); }
  .menu button.on { background: var(--blue-2); }
  .menu button.on b { color: var(--blue); }
</style>
