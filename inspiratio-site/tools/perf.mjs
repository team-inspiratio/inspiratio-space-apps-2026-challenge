// Frame-time measurement of typical interactions. Usage: node tools/perf.mjs [--slow]
// --slow: 4x CPU throttling and no GPU, to imitate an ordinary laptop without a graphics card.
import { chromium } from 'playwright-core'

const slow = process.argv.includes('--slow')
const URL = process.env.URL ?? 'http://localhost:5199/'
const browser = await chromium.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  args: slow ? ['--disable-gpu'] : ['--use-angle=d3d11', '--enable-gpu'],
})
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
if (slow) {
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 })
}
await page.goto(URL, { waitUntil: 'networkidle' })
await page.waitForTimeout(slow ? 8000 : 3500)
console.log('slow machine detected:', await page.evaluate(() => !!window.__slowMachine))
await page.evaluate(() => {
  const w = window
  w.__ft = []
  let last = performance.now()
  const tick = (t) => {
    w.__ft.push(t - last)
    last = t
    requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
})
async function measure(name, fn) {
  await page.evaluate(() => ((window.__ft = []), (window.__perfOn = true), (window.__perf = null)))
  await fn()
  const ft = await page.evaluate(() => window.__ft.slice(1))
  const pp = await page.evaluate(() => window.__perf)
  ft.sort((a, b) => a - b)
  const p = (q) => ft[Math.min(ft.length - 1, Math.floor(ft.length * q))]?.toFixed(1)
  const long = ft.filter((x) => x > 100).length
  const seg = pp ? `  [draws ${pp.n}: base ${(pp.base / pp.n).toFixed(1)} data ${(pp.data / pp.n).toFixed(1)} labels ${(pp.labels / pp.n).toFixed(1)} ms]` : ''
  console.log(`${name.padEnd(26)} frames ${String(ft.length).padStart(4)}  p50 ${p(0.5)}ms  p95 ${p(0.95)}ms  max ${ft.at(-1)?.toFixed(0)}ms  >100ms: ${long}${seg}`)
}
const wheel = async (dy, n, gap) => {
  for (let i = 0; i < n; i++) {
    await page.mouse.wheel(0, dy)
    await page.waitForTimeout(gap)
  }
}
await page.mouse.move(300, 450)
await measure('intro → step 2 (scroll)', async () => {
  await wheel(120, 24, 30)
  await page.waitForTimeout(5000)
})
await measure('step 2 → scatter (step 4)', async () => {
  await wheel(120, 16, 30)
  await page.waitForTimeout(4500)
})
await measure('fast wheel 20 ticks', async () => {
  await wheel(240, 20, 10)
  await page.waitForTimeout(4000)
})
await measure('to explorer (California)', async () => {
  await page.evaluate(() => document.querySelector('.step.last')?.scrollIntoView({ block: 'center' }))
  await page.waitForTimeout(4000)
})
await page.mouse.move(700, 450)
await measure('drag map 3 s', async () => {
  await page.mouse.down()
  for (let i = 0; i < 90; i++) {
    await page.mouse.move(700 + Math.sin(i / 10) * 200, 450 + Math.cos(i / 13) * 80)
    await page.waitForTimeout(30)
  }
  await page.mouse.up()
  await page.waitForTimeout(800)
})
await measure('ctrl+wheel zoom in/out', async () => {
  await page.keyboard.down('Control')
  await wheel(-200, 12, 25)
  await wheel(200, 12, 25)
  await page.keyboard.up('Control')
  await page.waitForTimeout(1200)
})
await browser.close()
