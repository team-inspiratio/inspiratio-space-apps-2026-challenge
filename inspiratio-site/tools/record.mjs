// Record a scroll-through of the story as an mp4 (CDP screencast frames + ffmpeg).
// Usage: node tools/record.mjs <out.mp4> [width]x[height]
import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'
import { execFileSync } from 'node:child_process'

const [out = 'out/scroll.mp4', size = '1440x900'] = process.argv.slice(2)
const [w, h] = size.split('x').map(Number)
const dir = path.join(path.dirname(out), 'frames')
fs.rmSync(dir, { recursive: true, force: true })
fs.mkdirSync(dir, { recursive: true })
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', args: ['--use-angle=d3d11', '--enable-gpu'] })
const page = await browser.newPage({ viewport: { width: w, height: h } })
await page.goto(process.env.URL ?? 'http://localhost:5199/', { waitUntil: 'networkidle' })
await page.waitForTimeout(3000)
const cdp = await page.context().newCDPSession(page)
const frames = []
cdp.on('Page.screencastFrame', async (f) => {
  frames.push({ t: f.metadata.timestamp, data: f.data })
  await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {})
})
await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 82, maxWidth: w, maxHeight: h, everyNthFrame: 1 })
await page.mouse.move(w * 0.2, h * 0.5)
// Hold on the opening, then scroll step by step, pausing on each.
await page.waitForTimeout(2500)
const holds = [3000, 3000, 6500, 3500, 4500, 4000, 4000, 3500]
for (const hold of holds) {
  for (let k = 0; k < 18; k++) {
    await page.mouse.wheel(0, h / 18)
    await page.waitForTimeout(40)
  }
  await page.waitForTimeout(hold)
}
await cdp.send('Page.stopScreencast')
await browser.close()
let list = ''
frames.forEach((f, i) => {
  const name = `f${String(i).padStart(5, '0')}.jpg`
  fs.writeFileSync(path.join(dir, name), Buffer.from(f.data, 'base64'))
  const d = i + 1 < frames.length ? Math.max(0.001, frames[i + 1].t - f.t) : 0.04
  list += `file '${name}'\nduration ${d.toFixed(4)}\n`
})
fs.writeFileSync(path.join(dir, 'list.txt'), list)
execFileSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', path.join(dir, 'list.txt'), '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-crf', '20', out])
fs.rmSync(dir, { recursive: true, force: true })
console.log('frames', frames.length, '->', out)
