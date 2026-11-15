<script lang="ts">
  import { app, names, selectWorld, selectRegion, selectBox, frame, touch, beginExplore, HOLDOUT, EXAMPLES, openExample } from '../lib/store.svelte'
  import Icon from './Icon.svelte'

  let open = $state(false)
  let q = $state('')
  let coords = $state(false)
  let w = $state(-124), s = $state(36), e = $state(-118), n = $state(41)
  let err = $state('')
  let input: HTMLInputElement
  let active = $state(0)

  type Item = { kind: 'world' | 'region' | 'example' | 'draw' | 'coords'; key: string; label: string; note?: string; run: () => void }
  const items = $derived.by<Item[]>(() => {
    const out: Item[] = []
    out.push({ kind: 'draw', key: 'draw', label: 'Draw an area on the map', run: startDraw })
    out.push({ kind: 'coords', key: 'coords', label: 'Enter coordinates', run: () => (coords = true) })
    EXAMPLES.forEach((x, i) => out.push({ kind: 'example', key: 'ex' + i, label: x.label, note: x.note, run: () => openExample(x) }))
    out.push({ kind: 'world', key: 'world', label: 'World', note: '14 regions', run: () => selectWorld() })
    for (const u of [...app.units].sort((a, b) => (names[a.name as keyof typeof names] ?? a.name).localeCompare(names[b.name as keyof typeof names] ?? b.name))) {
      const label = names[u.name as keyof typeof names] ?? u.name
      out.push({
        kind: 'region',
        key: u.name,
        label,
        note: HOLDOUT.has(u.name) ? 'holdout, low confidence' : u.kind === 'box' ? 'demonstration region' : 'region',
        run: () => selectRegion(u.name),
      })
    }
    const f = q.trim().toLowerCase()
    return f ? out.filter((i) => (i.label + ' ' + (i.note ?? '')).toLowerCase().includes(f)) : out
  })

  function startDraw() {
    app.drawing = true
    if (app.proj === 'globe') frame(app.place.bbox, 'flat')
  }
  function choose(i: Item) {
    touch()
    beginExplore()
    if (i.kind !== 'coords') close()
    i.run()
  }
  function close() {
    open = false
    coords = false
    q = ''
    input?.blur()
  }
  function key(ev: KeyboardEvent) {
    if (ev.key === 'ArrowDown') (ev.preventDefault(), (active = Math.min(items.length - 1, active + 1)))
    else if (ev.key === 'ArrowUp') (ev.preventDefault(), (active = Math.max(0, active - 1)))
    else if (ev.key === 'Enter' && items[active]) choose(items[active])
    else if (ev.key === 'Escape') close()
  }
  function apply(ev: SubmitEvent) {
    ev.preventDefault()
    if (![w, s, e, n].every(Number.isFinite) || s >= n || w === e) return (err = 'West and east must differ; south must be below north.')
    err = ''
    touch()
    beginExplore()
    close()
    selectBox([w, s, e, n])
  }
  $effect(() => {
    void q
    active = 0
  })
</script>

<svelte:window
  onpointerdown={(ev) => open && !(ev.target as HTMLElement).closest('.search') && close()}
  onkeydown={(ev) => ev.key === '/' && !(ev.target as HTMLElement).closest('input, textarea') && (ev.preventDefault(), input?.focus())}
/>

<div class="search" class:open>
  <label class="field">
    <Icon name="pin" />
    <input
      bind:this={input}
      bind:value={q}
      onfocus={() => (open = true)}
      onkeydown={key}
      placeholder={app.place.kind === 'world' ? 'Search a region, or draw on the map' : app.place.label}
      aria-label="Search places"
      aria-expanded={open}
    />
    {#if app.loading}<span class="spin" aria-label={app.loading}></span>{/if}
  </label>

  {#if open}
    <div class="menu" role="listbox">
      {#if coords}
        <form class="coords" onsubmit={apply}>
          <p class="h">Area by coordinates</p>
          <label>West <input type="number" step="any" min="-180" max="180" bind:value={w} /></label>
          <label>East <input type="number" step="any" min="-180" max="180" bind:value={e} /></label>
          <label>South <input type="number" step="any" min="-90" max="90" bind:value={s} /></label>
          <label>North <input type="number" step="any" min="-90" max="90" bind:value={n} /></label>
          {#if err}<p class="err">{err}</p>{/if}
          <button class="go" type="submit">Show this area</button>
        </form>
      {:else}
        {#each items as it, i (it.key)}
          {#if i === 0 || items[i - 1].kind !== it.kind && !(items[i - 1].kind === 'draw' && it.kind === 'coords') && !(items[i - 1].kind === 'world' && it.kind === 'region')}
            <p class="h">{it.kind === 'example' ? 'Remarkable months' : it.kind === 'world' || it.kind === 'region' ? 'Places' : 'Your own area'}</p>
          {/if}
          <button role="option" aria-selected={i === active} class:act={i === active} onmouseenter={() => (active = i)} onclick={() => choose(it)}>
            <span class="ic"><Icon name={it.kind === 'draw' ? 'select' : it.kind === 'coords' ? 'crosshair' : it.kind === 'example' ? 'info' : it.kind === 'world' ? 'globe' : 'map'} size={15} /></span>
            <span class="l">{it.label}</span>
            {#if it.note}<span class="n">{it.note}</span>{/if}
          </button>
        {/each}
      {/if}
    </div>
  {/if}
</div>

<style>
  .search { position: relative; width: min(380px, 42vw); }
  @media (max-width: 899px) { .search { width: min(260px, 64vw); } .field { height: 38px; } }
  .field {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 42px;
    padding: 0 16px;
    border-radius: 999px;
    background: rgb(255 255 255 / 0.96);
    box-shadow: 0 1px 2px rgb(22 25 29 / 0.06), 0 10px 30px -12px rgb(22 25 29 / 0.3);
    color: var(--ink-2);
    transition: box-shadow 0.3s, background 0.3s;
  }
  .open .field, .field:focus-within { background: #fff; box-shadow: 0 0 0 2px var(--blue), 0 12px 32px -10px rgb(11 61 145 / 0.35); }
  input { flex: 1; min-width: 0; border: 0; background: transparent; outline: none; font-size: 14px; color: var(--ink); }
  input::placeholder { color: var(--ink-2); }
  .spin { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--rule); border-top-color: var(--blue); animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .menu {
    position: absolute;
    top: 50px;
    left: 0;
    right: 0;
    max-height: min(520px, 70vh);
    overflow-y: auto;
    padding: 8px;
    border-radius: 18px;
    background: rgb(255 255 255 / 0.96);
    box-shadow: 0 24px 60px -20px rgb(22 25 29 / 0.4);
    animation: drop 0.32s cubic-bezier(0.16, 1, 0.3, 1);
    transform-origin: top center;
  }
  @keyframes drop { from { opacity: 0; transform: translateY(-6px) scale(0.98); } }
  .h { font-size: 11.5px; color: var(--ink-3); padding: 10px 10px 4px; }
  button[role='option'] {
    display: grid;
    grid-template-columns: 22px 1fr auto;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 10px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    text-align: left;
    font-size: 14px;
    cursor: pointer;
  }
  button.act { background: var(--blue-2); }
  .ic { color: var(--ink-3); display: inline-flex; }
  .act .ic { color: var(--blue); }
  .n { font-size: 12px; color: var(--ink-3); }
  .coords { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 4px 6px 8px; }
  .coords .h { grid-column: 1 / -1; padding: 6px 4px 2px; }
  .coords label { display: grid; gap: 3px; font-size: 12px; color: var(--ink-2); }
  .coords input { height: 34px; padding: 0 10px; border-radius: 8px; background: var(--paper); font-size: 14px; }
  .go { grid-column: 1 / -1; height: 36px; border: 0; border-radius: 999px; background: var(--blue); color: #fff; font-size: 14px; cursor: pointer; }
  .err { grid-column: 1 / -1; color: #b3261e; font-size: 12px; }
</style>
