<script lang="ts">
  import { csv } from '../lib/v2/science.js'
  import { app, MONTHS, hashState, fmt } from '../lib/store.svelte'
  import { ramp, logRange, ZERO } from '../lib/ramp'
  import Calendar from './Calendar.svelte'
  import AnnualChart from './AnnualChart.svelte'
  import Switch from './Switch.svelte'
  import Icon from './Icon.svelte'

  let tab = $state<'calendar' | 'yearly'>('calendar')
  let menu = $state(false)
  let copied = $state(false)
  const slug = $derived(app.place.label.toLowerCase().replace(/[^a-z0-9]+/g, '-'))

  function save(blob: Blob, name: string) {
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = name
    a.style.display = 'none'
    document.body.appendChild(a)
    a.click()
    setTimeout(() => (URL.revokeObjectURL(a.href), a.remove()), 4000)
  }
  const r0 = $derived(app.range[0])
  const r1 = $derived(app.range[1])
  const span = $derived(`${MONTHS[r0]}_to_${MONTHS[r1]}`)
  function downloadCsv() {
    const region = app.place.kind === 'box' ? `${app.place.label} ${app.place.bbox!.join(',')}` : app.place.label
    save(new Blob([csv(app.place.series.slice(r0, r1 + 1), region, 'global-v1')], { type: 'text/csv' }), `inspiratio-${slug}-monthly-${span}.csv`)
    menu = false
  }
  // Every 0.25° cell in the area, every month in the range: the detections behind the totals.
  const cellRows = $derived(app.place.cells ? app.place.cells.lat.length * (r1 - r0 + 1) : 0)
  const CELL_LIMIT = 2_000_000
  function downloadCells() {
    const c = app.place.cells
    if (!c || cellRows > CELL_LIMIT) return
    const lines = ['﻿lat_south,lon_west,lat_center,lon_center,month,detections,source']
    for (let i = 0; i < c.lat.length; i++) {
      const la = c.lat[i], lo = c.lon[i]
      const pre = `${la},${lo},${la + 0.125},${lo + 0.125},`
      for (let m = r0; m <= r1; m++) {
        const v = c.est[i * c.T + m]
        lines.push(pre + MONTHS[m] + ',' + (Number.isNaN(v) ? '' : +v.toFixed(3)) + ',' + app.place.series[m].source)
      }
    }
    save(new Blob([lines.join('\n')], { type: 'text/csv' }), `inspiratio-${slug}-cells-${span}.csv`)
    menu = false
  }
  // Individual hotspots for the selected month, on NASA FIRMS.
  const firms = $derived.by(() => {
    const b = app.place.bbox ?? [-180, -60, 180, 80]
    const m = MONTHS[app.month]
    const [y, mo] = m.split('-').map(Number)
    const last = new Date(Date.UTC(y, mo, 0)).getUTCDate()
    const cx = ((b[0] + b[2]) / 2).toFixed(2), cy = ((b[1] + b[3]) / 2).toFixed(2)
    const zoom = Math.max(2, Math.min(10, Math.round(Math.log2(360 / Math.max(0.5, b[2] - b[0])) + 1)))
    return `https://firms.modaps.eosdis.nasa.gov/map/#d:${m}-01..${m}-${String(last).padStart(2, '0')};@${cx},${cy},${zoom}.0z`
  })
  function downloadPng() {
    const s = 2, cw = 22, ch = 14, gap = 2, left = 56, top = 92
    const W = left + 12 * (cw + gap) + 24, Hh = top + 27 * (ch + gap) + 64
    const c = document.createElement('canvas')
    c.width = W * s
    c.height = Hh * s
    const g = c.getContext('2d')!
    g.scale(s, s)
    g.fillStyle = '#ffffff'
    g.fillRect(0, 0, W, Hh)
    const font = getComputedStyle(document.body).fontFamily
    g.fillStyle = '#16191d'
    g.font = `600 16px ${font}`
    g.fillText(app.place.label, 24, 32)
    g.font = `12px ${font}`
    g.fillStyle = '#4a4f57'
    g.fillText(`${app.mode === 'raw' ? 'Direct splice' : 'Harmonized'} monthly fire detections, 2000–2026`, 24, 52)
    g.fillText('VIIRS-equivalent detections per month · Inspiratio global-v1', 24, 68)
    const vals = app.place.series.map((p) => (app.mode === 'raw' ? p.raw : p.value))
    const sorted = vals.filter((v): v is number => v != null && v > 0).sort((a, b) => a - b)
    const lo = sorted.length ? Math.max(0.5, sorted[Math.floor(sorted.length * 0.02)]) : 1
    const hi = sorted.length ? Math.max(lo * 2, sorted[Math.floor(sorted.length * 0.98)]) : 2
    'JFMAMJJASOND'.split('').forEach((m, i) => {
      g.fillStyle = '#7b8089'
      g.fillText(m, left + i * (cw + gap) + cw / 2 - 3, top - 6)
    })
    for (let y = 2000; y <= 2026; y++) {
      const r = y - 2000
      g.fillStyle = '#7b8089'
      g.fillText(String(y), 24, top + r * (ch + gap) + 11)
      for (let m = 0; m < 12; m++) {
        const i = MONTHS.indexOf(`${y}-${String(m + 1).padStart(2, '0')}`)
        if (i < 0) continue
        const v = vals[i]
        g.fillStyle = v == null ? '#f1efe9' : v <= 0 ? ZERO : ramp(logRange(v, lo, hi))
        g.fillRect(left + m * (cw + gap), top + r * (ch + gap), cw, ch)
      }
    }
    g.fillStyle = '#7b8089'
    g.fillText(`Colour: log scale from ${fmt(lo)} to ${fmt(hi)} detections.`, 24, Hh - 28)
    c.toBlob((b) => b && save(b, `inspiratio-${slug}-calendar.png`), 'image/png')
    menu = false
  }
  async function copyLink() {
    const url = location.origin + location.pathname + hashState()
    history.replaceState(null, '', hashState())
    try {
      await navigator.clipboard.writeText(url)
    } catch {
      prompt('Copy this link', url)
    }
    copied = true
    setTimeout(() => ((copied = false), (menu = false)), 1200)
  }
</script>

<svelte:window onpointerdown={(e) => menu && !(e.target as HTMLElement).closest('.dl') && (menu = false)} />

<section class="card">
  <header>
    <Switch
      label="View"
      value={tab}
      onchange={(v) => (tab = v)}
      options={[
        { value: 'calendar', label: 'Calendar' },
        { value: 'yearly', label: 'Yearly' },
      ]}
    />
    <div class="dl">
      <button class="icon-btn" aria-label="Download or share" aria-expanded={menu} onclick={() => (menu = !menu)}><Icon name="download" /></button>
      {#if menu}
        <div class="menu">
          <p class="h">{r0 === 0 && r1 === MONTHS.length - 1 ? 'All months' : `${MONTHS[r0]} to ${MONTHS[r1]}`}</p>
          <button onclick={downloadCsv}><Icon name="download" size={15} /> Monthly CSV</button>
          <button onclick={downloadCells} disabled={!app.place.cells || cellRows > CELL_LIMIT} title={!app.place.cells ? 'Choose a region or draw an area first' : cellRows > CELL_LIMIT ? 'Too large: narrow the date range' : ''}>
            <Icon name="download" size={15} /> Cell CSV <span class="n">{app.place.cells ? (cellRows > CELL_LIMIT ? 'narrow the range' : `${(cellRows / 1000).toFixed(0)}k rows`) : 'pick an area'}</span>
          </button>
          <button onclick={downloadPng}><Icon name="image" size={15} /> Calendar PNG</button>
          <button onclick={copyLink}><Icon name={copied ? 'check' : 'link'} size={15} /> {copied ? 'Link copied' : 'Copy link'}</button>
          <a class="ext" href={firms} target="_blank" rel="noreferrer"><Icon name="corners" size={15} /> Individual hotspots on NASA FIRMS</a>
        </div>
      {/if}
    </div>
  </header>
  <div class="body">
    {#if tab === 'calendar'}<Calendar />{:else}<AnnualChart />{/if}
  </div>
</section>

<style>
  .card { padding: 14px 18px 16px; }
  header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  header :global(.switch) { box-shadow: none; background: var(--paper); }
  header :global(.switch button) { height: 26px; font-size: 12.5px; }
  .dl { position: relative; }
  .icon-btn { width: 32px; height: 32px; display: grid; place-items: center; border: 0; border-radius: 50%; background: var(--paper); color: var(--ink-2); cursor: pointer; transition: background 0.2s, transform 0.18s; }
  .icon-btn:hover { background: var(--blue-2); color: var(--blue); }
  .icon-btn:active { transform: scale(0.94); }
  .menu {
    position: absolute;
    right: 0;
    top: 38px;
    z-index: 10;
    width: 250px;
    padding: 6px;
    border-radius: 14px;
    background: #fff;
    box-shadow: 0 18px 44px -16px rgb(22 25 29 / 0.4);
    animation: drop 0.28s cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes drop { from { opacity: 0; transform: translateY(-4px) scale(0.98); } }
  .menu button { display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 10px; border: 0; border-radius: 9px; background: transparent; font-size: 13.5px; text-align: left; cursor: pointer; }
  .menu button:hover, .menu a:hover { background: var(--blue-2); color: var(--blue); }
  .menu button:disabled { opacity: 0.45; cursor: default; background: transparent; color: inherit; }
  .menu .n { margin-left: auto; font-size: 11.5px; color: var(--ink-3); }
  .menu .h { padding: 6px 10px 2px; font-size: 11.5px; color: var(--ink-3); }
  .menu a { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 9px; font-size: 13.5px; color: var(--ink); text-decoration: none; border-top: 1px solid var(--rule-2); margin-top: 4px; }
  .body { animation: fade 0.4s var(--ease); }
  @keyframes fade { from { opacity: 0; transform: translateY(4px); } }
</style>
