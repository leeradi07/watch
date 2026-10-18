// Renders each flyer to PNG (3x, ~288dpi) and A4 PDF.
// Usage: node election-flyer/render.mjs
import { chromium } from "playwright";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const dir = path.dirname(fileURLToPath(import.meta.url));
const pages = [
  ["index.html", "flyer"],     // 배동윤 후보 4대 약속
  ["turnout.html", "turnout"], // 투표 참여 안내
];

const browser = await chromium.launch();
for (const [file, out] of pages) {
  const page = await browser.newPage({
    viewport: { width: 900, height: 1200 },
    deviceScaleFactor: 3,
  });
  await page.goto(pathToFileURL(path.join(dir, file)).href + "?static");
  await page.evaluate(() => document.fonts.ready);
  await page.waitForLoadState("networkidle");

  await page.locator("#sheet").screenshot({ path: path.join(dir, `${out}.png`) });

  await page.emulateMedia({ media: "print" });
  await page.pdf({
    path: path.join(dir, `${out}.pdf`),
    format: "A4",
    printBackground: true,
    margin: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  await page.close();
  console.log(`wrote ${out}.png, ${out}.pdf`);
}
await browser.close();
