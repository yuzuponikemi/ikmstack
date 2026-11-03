// Runtime gate for course-build pages (references/chapter-spec.md §5).
// Usage: node browser_check.mjs <outdir> page1.html [page2.html ...]
// For each page: load via file:// at 360 px and 1280 px, wait for scripts, then report
//   - uncaught exceptions (pageerror) and console.error lines  -> FAIL
//   - horizontal overflow at 360 px (scrollWidth > innerWidth)  -> FAIL
//   - failed external requests (CDN fonts/KaTeX)                -> WARN (sandbox may block them)
//   - KaTeX render errors (.katex-error elements)               -> FAIL
// and saves screenshots <outdir>/<name>-360.png / -1280.png (first viewport + full page at 1280).
// KaTeX offline: if the CDN is blocked (sandbox), set KATEX_DIST=<node_modules/katex/dist> (npm i katex@0.16.9)
// and cdnjs KaTeX requests are served from that directory, so formulas really render and TeX errors surface.
// SECTIONS=1 also saves one screenshot per h2 section at 900 px (<name>-s<k>.png) for the visual typography review
// (a full-page shot is too downscaled to judge formulas).
// Uses the preinstalled Playwright; if require fails, set PLAYWRIGHT path or run where it is installed.
import { createRequire } from "module";
import path from "path";
import fs from "fs";
import { pathToFileURL } from "url";

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require("playwright")); }
catch { ({ chromium } = await import("playwright")); }

const [outdir, ...pages] = process.argv.slice(2);
if (!outdir || !pages.length) { console.error("usage: node browser_check.mjs <outdir> page.html ..."); process.exit(2); }
fs.mkdirSync(outdir, { recursive: true });

const KATEX_DIST = process.env.KATEX_DIST && fs.existsSync(process.env.KATEX_DIST) ? process.env.KATEX_DIST : null;
const MIME = { ".js": "text/javascript", ".css": "text/css", ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf" };
const browser = await chromium.launch();
let bad = 0;
for (const p of pages) {
  const url = pathToFileURL(path.resolve(p)).href;
  const name = path.basename(p, ".html");
  const fails = [], warns = [];
  for (const width of [360, 1280]) {
    const ctx = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    if (KATEX_DIST) {
      await page.route(/cdnjs\.cloudflare\.com\/ajax\/libs\/KaTeX\/[^/]+\/(.+)$/, (route) => {
        const rel = route.request().url().match(/\/KaTeX\/[^/]+\/(.+)$/)[1].split("?")[0];
        const f = path.join(KATEX_DIST, rel);
        if (!fs.existsSync(f)) return route.abort();
        route.fulfill({ status: 200, contentType: MIME[path.extname(f)] || "application/octet-stream", body: fs.readFileSync(f) });
      });
    }
    page.on("pageerror", (e) => fails.push(`[${width}] pageerror: ${e.message}`));
    page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) fails.push(`[${width}] console.error: ${m.text()}`); });
    page.on("requestfailed", (r) => warns.push(`[${width}] request failed: ${r.url().slice(0, 90)}`));
    await page.goto(url, { waitUntil: "load", timeout: 30000 }).catch((e) => fails.push(`[${width}] goto: ${e.message}`));
    await page.waitForTimeout(1500);
    const probe = await page.evaluate(() => ({
      sw: document.documentElement.scrollWidth, iw: window.innerWidth,
      katexErr: document.querySelectorAll(".katex-error").length,
      katex: document.querySelectorAll(".katex").length,
      canvases: [...document.querySelectorAll("canvas")].filter((c) => c.width > 0 && c.height > 0).length,
      canvasTotal: document.querySelectorAll("canvas").length,
    })).catch((e) => { fails.push(`[${width}] evaluate: ${e.message}`); return null; });
    if (probe) {
      if (width === 360 && probe.sw > probe.iw) fails.push(`[360] horizontal overflow: scrollWidth ${probe.sw} > ${probe.iw}`);
      if (probe.katexErr) fails.push(`[${width}] KaTeX errors: ${probe.katexErr}`);
      if (width === 1280) warns.push(`info: katex=${probe.katex} canvases sized=${probe.canvases}/${probe.canvasTotal}`);
    }
    await page.screenshot({ path: path.join(outdir, `${name}-${width}.png`), fullPage: width === 1280 }).catch(() => {});
    if (process.env.SECTIONS && width === 1280) {
      await page.setViewportSize({ width: 900, height: 900 });
      await page.waitForTimeout(300);
      const n = await page.evaluate(() => document.querySelectorAll("main h2[id]").length);
      for (let k = 0; k < n; k++) {
        const box = await page.evaluate((k) => {
          const hs = [...document.querySelectorAll("main h2[id]")];
          const a = hs[k].getBoundingClientRect().top + scrollY;
          const b = k + 1 < hs.length ? hs[k + 1].getBoundingClientRect().top + scrollY : document.querySelector("main").getBoundingClientRect().bottom + scrollY;
          return { y: Math.max(0, a - 8), h: Math.min(b - a + 8, 6000) };
        }, k);
        await page.screenshot({ path: path.join(outdir, `${name}-s${String(k + 1).padStart(2, "0")}.png`), fullPage: true,
          clip: { x: 0, y: box.y, width: 900, height: box.h } }).catch(() => {});
      }
    }
    await ctx.close();
  }
  console.log(`${fails.length ? "FAIL" : "PASS"} ${p}`);
  for (const w of [...new Set(warns)].slice(0, 12)) console.log(`  ${w.startsWith("info") ? w : "WARN: " + w}`);
  for (const f of fails) console.log(`  FAIL: ${f}`);
  bad += fails.length ? 1 : 0;
}
await browser.close();
process.exit(bad ? 1 : 0);
