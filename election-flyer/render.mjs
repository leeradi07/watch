// Renders index.html to flyer.png (3x, ~288dpi) and flyer.pdf (A4).
// Usage: node election-flyer/render.mjs
import { chromium } from "playwright";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const dir = path.dirname(fileURLToPath(import.meta.url));
const url = pathToFileURL(path.join(dir, "index.html")).href + "?static";

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 900, height: 1200 },
  deviceScaleFactor: 3,
});
await page.goto(url);
await page.evaluate(() => document.fonts.ready);

await page.locator("#sheet").screenshot({ path: path.join(dir, "flyer.png") });

await page.emulateMedia({ media: "print" });
await page.pdf({
  path: path.join(dir, "flyer.pdf"),
  format: "A4",
  printBackground: true,
  margin: { top: 0, right: 0, bottom: 0, left: 0 },
});

await browser.close();
console.log("wrote flyer.png, flyer.pdf");
