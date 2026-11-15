import { chromium } from "playwright";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { gzipSync } from "node:zlib";
await fs.mkdir("test-results", { recursive: true });
const browser = await chromium.launch({
  executablePath: process.env.BROWSER_EXECUTABLE || "/usr/bin/chromium",
  headless: true,
  args: ["--no-sandbox"],
});
const page = await browser.newPage({
  viewport: { width: 1440, height: 1100 },
  deviceScaleFactor: 1,
});
const baseURL = process.env.FRONTEND_URL || "http://127.0.0.1:5174/";
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
try {
  // Keep the fallback checks deterministic even when full released assets exist.
  await page.route("**/data/global-v1/ready.json", route => route.fulfill({status:404,body:""}));
  await page.goto(baseURL);
  await page.locator(".value").waitFor();
  assert.equal(await page.locator("html").getAttribute("lang"), "en");
  assert.doesNotMatch(
    await page.locator("body").innerText(),
    /[\u3400-\u9fff]/,
  );
  assert.equal(await page.locator("#target").inputValue(), "2020-09");
  assert.match(await page.locator(".value").innerText(), /125,460/);
  assert.match(await page.locator(".finding").innerText(), /21.90/);
  await page.screenshot({ path: "test-results/desktop.png", fullPage: true });
  await page.selectOption("#baseline", "snpp");
  assert.match(
    await page.locator(".finding").innerText(),
    /Not enough history/,
  );
  await page.selectOption("#baseline", "all");
  await page.selectOption("#region", "cordoba");
  await page.waitForFunction(
    () => document.querySelector("#place-name").textContent === "Córdoba",
  );
  assert.match(await page.locator(".value").innerText(), /1,272/);
  assert.match(await page.locator(".finding").innerText(), /0.30/);
  const download = page.waitForEvent("download");
  await page.click("#download-csv");
  const d = await download;
  await d.saveAs("test-results/export.csv");
  assert.match(await fs.readFile("test-results/export.csv", "utf8"), /v1/);
  const png = page.waitForEvent("download");
  await page.click("#download-image");
  const p = await png;
  await p.saveAs("test-results/calendar.png");
  assert.equal(
    (await fs.readFile("test-results/calendar.png")).subarray(1, 4).toString(),
    "PNG",
  );
  await page.reload();
  await page.locator(".value").waitFor();
  assert.equal(await page.locator("#region").inputValue(), "cordoba");
  // Display preferences persist, and date filtering also scopes exports.
  await page.locator(".accessibility summary").click();
  await page.check("#color-assist");
  await page.selectOption("#palette", "mono");
  await page.check("#contrast");
  await page.check("#large-text");
  await page.check("#reduce-motion");
  await page.locator(".accessibility summary").click();
  await page.locator("#range-start").fill("2020-01");
  await page.locator("#range-start").dispatchEvent("change");
  await page.locator("#range-end").fill("2021-12");
  await page.locator("#range-end").dispatchEvent("change");
  assert.equal(await page.locator(".cell").count(), 24);
  assert.equal(await page.locator(".annual-total").count(), 2);
  assert.match(await page.locator(".annual-total").first().innerText(), /—/);
  const ranged = page.waitForEvent("download");
  await page.click("#download-csv");
  await (await ranged).saveAs("test-results/ranged.csv");
  const exported = await fs.readFile("test-results/ranged.csv", "utf8");
  assert.doesNotMatch(exported, /2019-|2022-/);
  await page.reload();
  await page.locator(".value").waitFor();
  assert.equal(await page.locator("#palette").inputValue(), "mono");
  assert.equal(await page.locator("#range-start").inputValue(), "2020-01");
  assert.ok(await page.locator("html.contrast.large-text.reduce-motion").count());
  await page.click("#range-reset");
  await page.locator(".cell:not(:disabled)").first().focus();
  await page.keyboard.press("Enter");
  assert.ok(await page.locator(".cell.selected").count());
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    "mobile viewport overflow",
  );
  // Synthetic interface fixture, isolated to browser routes, never product data.
  const full = await browser.newPage();
  full.on("pageerror", (e) => errors.push(e.message));
  const payload = {
    months: ["2026-08", "2026-09", "2026-10"],
    month_source: ["model_aqua", "snpp", "snpp"],
    month_nrt: [false, true, true],
    month_input_complete: [true, true, true],
    totals: {
      est: [30, 60, 90],
      lo_90: [10, 60, 90],
      hi_90: [50, 60, 90],
      est_m0: [5, 60, 90],
    },
    cells: { lat_idx: [360, 360], lon_idx: [720, 721] },
    est: [
      [10, 20, 30],
      [20, 40, 60],
    ],
  };
  await full.route("**/data/global-v1/**", (route) => {
    const url = route.request().url();
    if (url.endsWith("ready.json"))
      return route.fulfill({ json: { version: "global-v1" } });
    if (url.endsWith("index.json"))
      return route.fulfill({
        json: {
          version: "global-v1",
          units: [
            {
              name: "test_region",
              label: "Integration test region",
              role: "train",
              bbox: [-180, 0, 180, 0.25],
              kind: 'region',
              file: "test_region.json.gz",
            },
          ],
        },
      });
    return route.fulfill({
      contentType: "application/gzip",
      body: gzipSync(JSON.stringify(payload)),
    });
  });
  await full.goto(baseURL);
  await full.locator(".value").waitFor();
  assert.equal(await full.locator("#target").inputValue(), "2026-10");
  assert.match(await full.locator("#notice").innerText(), /global-v1/);
  await full.click("#raw");
  assert.equal(await full.locator("#raw").getAttribute("aria-pressed"), "true");
  await full.locator("[name=w]").fill("0");
  await full.locator("[name=s]").fill("0");
  await full.locator("[name=e]").fill("0.375");
  await full.locator("[name=n]").fill("0.25");
  await full.locator("#bbox-form button[type=submit]").click();
  await full.waitForFunction(()=>document.querySelector('#place-name').textContent==='Custom area');
  assert.match(await full.locator(".value").innerText(), /60/);
  assert.match(await full.locator("#place-name").innerText(), /Custom area/);
  assert.match(await full.locator(".interval").innerText(), /Unavailable/);
  await full.reload();
  await full.waitForFunction(() =>
    document.querySelector("#place-name").textContent.includes("Custom area"),
  );
  assert.match(await full.locator(".value").innerText(), /60/);
  await full.click("#clear-box");
  assert.match(await full.locator(".value").innerText(), /90/);
  payload.cells.lon_idx=[1439,0];
  await full.reload();
  await full.locator('.value').waitFor();
  for(const [name,value] of Object.entries({w:'170',s:'0',e:'-170',n:'0.25'}))await full.locator(`[name=${name}]`).fill(value);
  await full.locator('#bbox-form button[type=submit]').click();
  await full.waitForFunction(()=>document.querySelector('#place-name').textContent==='Custom area');
  assert.match(await full.locator('#place-name').innerText(),/Custom area/);
  assert.match(await full.locator('.value').innerText(),/90/);
  assert.ok(Math.abs(Number((await full.locator('#map').getAttribute('data-center')).match(/, ([\d.-]+)/)[1])-180)<1,'date-line custom area must center near 180');
  await full.close();
  const real = await browser.newPage({viewport:{width:1440,height:1000},locale:"zh-CN"});
  real.on("pageerror",e=>errors.push(e.message));
  real.on("requestfailed",r=>console.log("Request failed",r.url(),r.failure()));
  await real.goto(baseURL);
  await real.locator(".value").waitFor({timeout:10000}).catch(async e=>{console.log(await real.locator("#notice").innerText(),errors);throw e;});
  assert.match(await real.locator("#notice").innerText(), /global-v1/);
  assert.equal(await real.locator("#range-start").getAttribute("type"),"text");
  assert.doesNotMatch(await real.locator("body").innerText(), /[\u3400-\u9fff]/);
  assert.ok(await real.locator("#map .fire-canvas").count() > 0);
  assert.ok(await real.locator(".cell:not(:disabled)").count() >= 300);
  const before = await real.locator(".fire-canvas").evaluate(c=>c.toDataURL());
  await real.selectOption("#target","2020-09");
  assert.notEqual(await real.locator(".fire-canvas").evaluate(c=>c.toDataURL()),before);
  await real.locator('#map').evaluate(e=>window.scrollTo({top:window.scrollY+e.getBoundingClientRect().top-100,behavior:'instant'}));
  await real.waitForTimeout(300);
  const mapBox=await real.locator('#map').boundingBox();
  await real.mouse.move(mapBox.x+mapBox.width/2,mapBox.y+mapBox.height/2);
  const preZoom=await real.locator('#map').getAttribute('data-zoom');
  await real.mouse.wheel(0,-500);
  await real.waitForTimeout(700);
  assert.notEqual(await real.locator('#map').getAttribute('data-zoom'),preZoom,'wheel must change geographic scale');
  const preDrag=await real.locator('#map').getAttribute('data-center');
  const dragBox=await real.locator('#map').boundingBox();
  await real.mouse.move(dragBox.x+dragBox.width/2,dragBox.y+dragBox.height/2);
  await real.mouse.down();
  await real.mouse.move(dragBox.x+dragBox.width/2+120,dragBox.y+dragBox.height/2+60,{steps:15});
  await real.mouse.up();
  await real.waitForTimeout(700);
  assert.notEqual(await real.locator('#map').getAttribute('data-center'),preDrag,'drag must pan the geographic view');
  await real.click('#zoom-reset');
  await real.waitForTimeout(400);
  const red = await real.locator('.cell[data-month="2020-09"]').evaluate(e=>e.style.backgroundColor);
  await real.locator(".accessibility summary").click();
  assert.equal(await real.locator("#color-assist").isChecked(),false);
  await real.check("#color-assist");
  assert.notEqual(await real.locator('.cell[data-month="2020-09"]').evaluate(e=>e.style.backgroundColor),red);
  await real.uncheck("#color-assist");
  await real.locator(".accessibility summary").click();
  await real.screenshot({path:"test-results/global-desktop.png",fullPage:true});
  await real.click('#chongqing-example');
  await real.waitForFunction(()=>document.querySelector('#place-name').textContent==='Custom area'&&document.querySelector('#target').value==='2022-08');
  assert.match(await real.locator('.value').innerText(),/420/);
  assert.match(await real.locator('.finding').innerText(),/6.77/);
  assert.match(await real.locator('#map-grid-status').innerText(),/Local color scale.*Scaled NOAA-20/);
  assert.match(await real.locator('#bbox-message').innerText(),/Central Asia/);
  await real.locator('.geography').screenshot({path:'test-results/chongqing-area.png'});
  const previousHash=new URL(real.url()).hash;
  await real.click('#draw-area');
  await real.locator('#map').evaluate(e=>window.scrollTo({top:window.scrollY+e.getBoundingClientRect().top-100,behavior:'instant'}));
  const drawingBox=await real.locator('#map').boundingBox();
  await real.mouse.move(drawingBox.x+drawingBox.width*.35,drawingBox.y+drawingBox.height*.35);
  await real.mouse.down();
  await real.mouse.move(drawingBox.x+drawingBox.width*.6,drawingBox.y+drawingBox.height*.7,{steps:15});
  await real.mouse.up();
  await real.waitForFunction(old=>location.hash!==old,previousHash);
  await real.waitForFunction(()=>!document.querySelector('#workspace').hasAttribute('aria-busy'));
  assert.equal(await real.locator('#pan-map').getAttribute('aria-pressed'),'true');
  assert.match(await real.locator('#bbox-message').innerText(),/intersecting cells/);
  const selectedArea=new URLSearchParams(new URL(real.url()).hash.slice(1)).get('bbox').split(',').map(Number);
  assert.ok(selectedArea[0]>106&&selectedArea[2]<108);
  assert.ok(selectedArea[1]>29&&selectedArea[3]<30.5);
  await real.click('#draw-area');
  await real.keyboard.press('Escape');
  assert.equal(await real.locator('#pan-map').getAttribute('aria-pressed'),'true');
  for (const region of ['AUST','CEAM']) {
    await real.selectOption('#region',region);
    await real.waitForFunction(name=>location.hash.includes('region='+name),region);
    await real.waitForTimeout(500);
    assert.ok(Number(await real.locator('#map').getAttribute('data-zoom'))>=2);
    await real.locator('.geography').screenshot({path:`test-results/map-${region}.png`});
  }
  await real.setViewportSize({width:390,height:844});
  assert.ok(await real.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await real.screenshot({path:"test-results/global-mobile.png",fullPage:true});
  await real.close();
  assert.deepEqual(errors, []);
  console.log(
    "Browser PASS: actual values, baseline, region switch, reload state, CSV/PNG exports, keyboard and mobile layout.",
  );
} finally {
  await browser.close();
}
