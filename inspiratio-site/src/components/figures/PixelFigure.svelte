<script lang="ts">
  import { Tween } from 'svelte/motion'
  import { cubicOut } from 'svelte/easing'
  let { play = false }: { play?: boolean } = $props()
  // Illustration: the same fire front seen through 1 km and 375 m pixels.
  // A pixel "detects" when the fire covers enough of it; counts are computed from the drawn shape.
  const S = 120 // one panel = 3 km × 3 km, 120 px
  const fire = (x: number, y: number) => {
    // A thin, irregular fire line plus two small spot fires (coordinates in km, 0..3).
    const line = Math.abs(y - (1.1 + 0.35 * Math.sin(x * 2.1) + 0.25 * x)) < 0.07 + 0.03 * Math.sin(x * 7)
    const spot1 = (x - 0.55) ** 2 + (y - 2.35) ** 2 < 0.012
    const spot2 = (x - 2.45) ** 2 + (y - 2.55) ** 2 < 0.008
    return line || spot1 || spot2
  }
  function detect(px: number) {
    const n = Math.round(3 / px), cells: { x: number; y: number; on: boolean }[] = []
    for (let i = 0; i < n; i++)
      for (let j = 0; j < n; j++) {
        let hit = 0, tot = 0
        for (let a = 0; a < 8; a++)
          for (let b = 0; b < 8; b++) {
            tot++
            if (fire((i + (a + 0.5) / 8) * px, (j + (b + 0.5) / 8) * px)) hit++
          }
        // Small pixels need less burning area to trigger; large pixels need the fire to fill more of them.
        cells.push({ x: i, y: j, on: hit / tot > (px > 0.5 ? 0.06 : 0.1) })
      }
    return { n, size: S / n, cells, count: cells.filter((c) => c.on).length }
  }
  const modis = detect(1)
  const viirs = detect(0.375)
  const nm = new Tween(0, { duration: 900, easing: cubicOut })
  const nv = new Tween(0, { duration: 1500, easing: cubicOut })
  $effect(() => {
    nm.target = play ? modis.count : 0
    nv.target = play ? viirs.count : 0
  })
  const shape: string[] = []
  for (let i = 0; i < 90; i++) for (let j = 0; j < 90; j++) if (fire((i + 0.5) / 30, (j + 0.5) / 30)) shape.push(`${(i * S) / 90},${(j * S) / 90}`)
</script>

<figure>
  <div class="pair">
    {#each [{ d: modis, name: 'MODIS', px: '1 km pixels', n: nm }, { d: viirs, name: 'VIIRS', px: '375 m pixels', n: nv }] as p}
      <div>
        <svg viewBox="-1 -1 {S + 2} {S + 2}" role="img" aria-label="{p.name}: {p.d.count} detections">
          <rect x="0" y="0" width={S} height={S} fill="#f3f1ec" />
          {#each p.d.cells.filter((c) => c.on) as c, k}
            <rect class="lit" class:go={play} x={c.x * p.d.size} y={c.y * p.d.size} width={p.d.size} height={p.d.size} fill="#e2662d" style:--d="{300 + k * 90}ms" />
          {/each}
          {#each shape as s}
            {@const [x, y] = s.split(',').map(Number)}
            <rect {x} {y} width={S / 90 + 0.2} height={S / 90 + 0.2} fill="#4f1325" />
          {/each}
          {#each Array(p.d.n + 1) as _, i}
            <line x1={i * p.d.size} x2={i * p.d.size} y1="0" y2={S} stroke="#16191d" stroke-opacity="0.18" stroke-width="0.6" />
            <line y1={i * p.d.size} y2={i * p.d.size} x1="0" x2={S} stroke="#16191d" stroke-opacity="0.18" stroke-width="0.6" />
          {/each}
        </svg>
        <p><span class="n">{Math.round(p.n.current)}</span> <b>{p.name}</b> detections<br />{p.px}</p>
      </div>
    {/each}
  </div>
  <figcaption>Illustration · one fire, a 3 × 3 km patch</figcaption>
</figure>

<style>
  figure { margin: 18px 0 0; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  svg { width: 100%; display: block; border-radius: 4px; }
  p { margin-top: 6px; font-size: 13px; color: var(--ink-2); line-height: 1.4; }
  p b { color: var(--ink); font-weight: 600; }
  .n { font-size: 30px; font-weight: 300; letter-spacing: -0.03em; color: var(--ink); }
  figcaption { margin-top: 8px; font-size: 12px; color: var(--ink-3); }
  .lit { opacity: 0; transition: opacity 0.35s ease var(--d); }
  .lit.go { opacity: 0.85; }
</style>
