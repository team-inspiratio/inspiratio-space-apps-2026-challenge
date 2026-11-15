// End-to-end check of the explorer's functions against the running dev site.
import { chromium } from 'playwright-core'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const URL = process.env.URL ?? 'http://localhost:5199/'
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true, permissions: ['clipboard-read', 'clipboard-write'] })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
const results = []
const ok = (name, cond, info = '') => results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${info ? '  — ' + info : ''}`)
const cards = () => page.locator('aside.cards').innerText()
const title = (t) => page.waitForFunction((t) => document.querySelector('aside.cards h2')?.textContent?.includes(t), t, { timeout: 60000 })
async function search(label) {
  await page.click('.search input')
  await page.click(`.search .menu button[role="option"]:has-text("${label}")`)
}
async function menu(label) {
  await page.click('button[aria-label="Download or share"]')
  await page.click(`.dl .menu button:has-text("${label}")`)
}

try {
  await page.goto(URL, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2000)
  await page.click('button:has-text("Go straight to the explorer")')
  await page.waitForTimeout(3500)

  // 1. Example: Chongqing
  await search('Chongqing')
  await title('Chongqing')
  await page.waitForTimeout(1600)
  let t = await cards()
  ok('Chongqing example loads', t.includes('Chongqing area'))
  ok('Aug 2022 value 420', /August 2022[^]{0,30}?\n420(?!\d)/.test(t), JSON.stringify(t.slice(0, 120)))
  ok('ratio 6.8×', t.includes('6.8×'))

  // 2. California example
  await search('California')
  await title('California')
  await page.waitForTimeout(1800)
  t = await cards()
  ok('California Sep 2020 ≈ 21.9×', t.includes('21.9×') && t.includes('September 2020'), JSON.stringify(t.slice(0, 120)))

  // 3. CSV / PNG / link
  await search('Chongqing')
  await title('Chongqing')
  const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 10000 }), menu('Monthly CSV')])
  const file = path.join(os.tmpdir(), 'insp-check.csv')
  await dl.saveAs(file)
  const csv = fs.readFileSync(file, 'utf8')
  const row = csv.split('\n').find((l) => l.includes('"2022-08"'))
  ok('CSV has 312 months + header', csv.trim().split('\n').length === 313)
  ok('CSV Aug 2022 ≈ 420.03', !!row && Math.abs(+row.split('","')[3] - 420.03) < 0.05, row)
  const [png] = await Promise.all([page.waitForEvent('download', { timeout: 10000 }), menu('Calendar PNG')])
  ok('PNG downloads', png.suggestedFilename().endsWith('.png'))
  await menu('Copy link')
  await page.waitForTimeout(300)
  const hash = await page.evaluate(() => location.hash)
  ok('link hash written', hash.includes('box=106,29,108,30.5') && hash.includes('m=2022-08'), hash)

  // 4. Region search
  await search('Central Asia')
  await title('Central Asia')
  ok('region search loads Central Asia', (await cards()).includes('Central Asia'))

  // 5. Direct splice switch
  await page.click('.top button[role="radio"]:has-text("Direct splice")')
  await page.waitForTimeout(500)
  ok('direct splice mode shows', (await cards()).includes('direct splice'))
  await page.click('.top button[role="radio"]:has-text("Harmonized")')

  // 6. Coordinates
  await search('Enter coordinates')
  const inputs = page.locator('form.coords input')
  for (const [i, v] of ['20', '30', '-10', '0'].entries()) await inputs.nth(i).fill(v)
  await page.click('button:has-text("Show this area")')
  await title('Custom area')
  ok('coordinates load a custom area', (await cards()).includes('Custom area'))

  // 7. Draw a rectangle (on a fresh area, back on the world view)
  await search('World')
  await page.waitForTimeout(1800)
  await search('Draw an area')
  await page.waitForTimeout(1800)
  await page.mouse.move(760, 430)
  await page.mouse.down()
  await page.mouse.move(800, 460, { steps: 6 })
  await page.mouse.up()
  await title('Custom area').catch(() => {})
  ok('drawing a box selects an area', (await page.evaluate(() => document.querySelector('aside.cards h2')?.textContent)) === 'Custom area')

  // 8. Play
  const before = await page.locator('.bar .label').innerText()
  await page.click('button[aria-label="Play through the months"]')
  await page.waitForTimeout(700)
  const after = await page.locator('.bar .label').innerText()
  await page.click('button[aria-label="Pause"]')
  ok('play advances months', before !== after, `${before} → ${after}`)

  // 9. Hash restore
  await page.goto('about:blank')
  await page.goto(URL + '#box=106,29,108,30.5&m=2022-08&mode=harm', { waitUntil: 'networkidle' })
  await title('Chongqing')
  await page.waitForTimeout(1800)
  ok('hash restores Chongqing', (await cards()).includes('6.8×'))
} catch (e) {
  results.push('FAIL  crashed: ' + String(e).split('\n')[0])
}
console.log(results.join('\n'))
if (errors.length) console.log('PAGE ERRORS:\n' + errors.join('\n'))
await browser.close()
