<script lang="ts" generics="T extends string">
  import Icon from './Icon.svelte'
  import type { IconName } from '../lib/icons'

  let {
    options,
    value,
    onchange,
    label,
  }: { options: { value: T; label?: string; icon?: IconName; title?: string }[]; value: T; onchange: (v: T) => void; label: string } = $props()

  let btns: HTMLButtonElement[] = $state([])
  let thumb = $state({ x: 0, w: 0 })
  $effect(() => {
    const i = options.findIndex((o) => o.value === value)
    const b = btns[i]
    if (b) thumb = { x: b.offsetLeft, w: b.offsetWidth }
  })
</script>

<div class="switch" role="radiogroup" aria-label={label}>
  <span class="thumb" style:transform="translateX({thumb.x}px)" style:width="{thumb.w}px"></span>
  {#each options as o, i}
    <button
      bind:this={btns[i]}
      role="radio"
      aria-checked={o.value === value}
      aria-label={o.title ?? o.label}
      title={o.title}
      class:on={o.value === value}
      onclick={() => onchange(o.value)}
    >
      {#if o.icon}<Icon name={o.icon} />{/if}{#if o.label}<span>{o.label}</span>{/if}
    </button>
  {/each}
</div>

<style>
  .switch {
    position: relative;
    display: inline-flex;
    padding: 3px;
    border-radius: 999px;
    background: rgb(255 255 255 / 0.96);
    box-shadow: 0 1px 2px rgb(22 25 29 / 0.06), 0 8px 24px -10px rgb(22 25 29 / 0.25);
  }
  .thumb {
    position: absolute;
    top: 3px;
    bottom: 3px;
    left: 0;
    border-radius: 999px;
    background: var(--ink);
    transition: transform 0.42s cubic-bezier(0.16, 1, 0.3, 1), width 0.42s cubic-bezier(0.16, 1, 0.3, 1);
  }
  button {
    position: relative;
    z-index: 1;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 30px;
    padding: 0 13px;
    border: 0;
    background: transparent;
    border-radius: 999px;
    font-size: 13px;
    color: var(--ink-2);
    cursor: pointer;
    transition: color 0.3s;
  }
  button.on { color: #fff; }
  button:active { transform: scale(0.97); }
</style>
