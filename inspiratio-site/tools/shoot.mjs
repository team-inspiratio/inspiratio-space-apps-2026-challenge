// Screenshot the running dev site at given scroll positions (in viewport heights).
// Usage: node tools/shoot.mjs <outDir> <w>x<h> <pos1> <pos2> ...
import { chromium } from 'playwright-core'
import fs from 'node:fs'

const [outDir, size = '1440x900', ...positions] = process.argv.slice(2)
const [w, h] = size.split('x').map(Number)
fs.mkdirSync(outDir, { recursive: true })
const browser = await chromium.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'],
})
const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 })
const logs = []
page.on('console', (m) => m.type() === 'error' && logs.push(m.text()))
page.on('pageerror', (e) => logs.push(String(e)))
await page.goto(process.env.URL ?? 'http://localhost:5199/', { waitUntil: 'networkidle' })
await page.waitForTimeout(6500)
for (const pos of positions.length ? positions : ['0']) {
  await page.evaluate((y) => window.scrollTo(0, y * innerHeight), Number(pos))
  await page.waitForTimeout(+(process.env.WAIT ?? 2200))
  await page.screenshot({ path: `${outDir}/at-${pos}.png` })
}
if (logs.length) console.log('ERRORS:\n' + logs.join('\n'))
await browser.close()
console.log('done')
