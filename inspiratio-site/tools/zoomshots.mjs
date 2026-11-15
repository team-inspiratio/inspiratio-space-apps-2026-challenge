// Screenshots of the explorer zoomed into a few places, to check detail levels and labels.
import { chromium } from 'playwright-core'
const out = process.argv[2] ?? 'out/zoom'
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
await page.goto(process.env.URL ?? 'http://localhost:5199/', { waitUntil: 'networkidle' })
await page.waitForTimeout(2000)
await page.click('button:has-text("Go straight to the explorer")')
await page.waitForTimeout(3000)
async function search(label) {
  await page.click('.search input')
  await page.click(`.search .menu button[role="option"]:has-text("${label}")`)
  await page.waitForTimeout(4500)
}
async function zoom(n) {
  await page.mouse.move(720, 450)
  await page.keyboard.down('Control')
  for (let i = 0; i < n; i++) (await page.mouse.wheel(0, -120), await page.waitForTimeout(40))
  await page.keyboard.up('Control')
  await page.waitForTimeout(2500)
}
await search('California')
await page.screenshot({ path: `${out}-california.png` })
await zoom(6)
await page.screenshot({ path: `${out}-california-close.png` })
await search('Chongqing')
await page.screenshot({ path: `${out}-chongqing.png` })
await search('World')
await page.waitForTimeout(1000)
await page.click('.top button[aria-label="Flat map"]')
await page.waitForTimeout(2500)
await page.mouse.move(560, 520)
await page.keyboard.down('Control')
for (let i = 0; i < 8; i++) (await page.mouse.wheel(0, -120), await page.waitForTimeout(40))
await page.keyboard.up('Control')
await page.waitForTimeout(3000)
await page.screenshot({ path: `${out}-amazon.png` })
if (errors.length) console.log(errors.join('\n'))
await browser.close()
console.log('done')
