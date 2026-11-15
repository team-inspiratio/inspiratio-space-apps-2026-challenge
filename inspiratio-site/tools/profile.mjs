// CPU profile of scrolling through the story; prints the functions with the most self time.
import { chromium } from 'playwright-core'
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
await page.goto(process.env.URL ?? 'http://localhost:5199/', { waitUntil: 'networkidle' })
await page.waitForTimeout(3500)
const cdp = await page.context().newCDPSession(page)
await cdp.send('Profiler.enable')
await cdp.send('Profiler.setSamplingInterval', { interval: 200 })
await cdp.send('Profiler.start')
await page.mouse.move(300, 450)
for (let i = 0; i < 24; i++) (await page.mouse.wheel(0, 120), await page.waitForTimeout(30)); await page.waitForTimeout(5000); await cdp.send("Profiler.stop"); await cdp.send("Profiler.start"); for (let i = 0; i < 16; i++) (await page.mouse.wheel(0, 120), await page.waitForTimeout(30))
await page.waitForTimeout(6000)
const { profile } = await cdp.send('Profiler.stop')
const self = new Map()
const dt = profile.timeDeltas
const byId = new Map(profile.nodes.map((n) => [n.id, n]))
for (let i = 0; i < profile.samples.length; i++) {
  const n = byId.get(profile.samples[i])
  const f = n.callFrame
  const key = `${f.functionName || '(anon)'}  ${f.url.split('/').pop()}:${f.lineNumber}`
  self.set(key, (self.get(key) ?? 0) + (dt[i] ?? 0) / 1000)
}
const top = [...self].sort((a, b) => b[1] - a[1]).slice(0, 25)
for (const [k, ms] of top) console.log(ms.toFixed(0).padStart(6), 'ms ', k)
await browser.close()
