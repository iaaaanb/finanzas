// Captura la portada a la medida de la tarjeta social de GitHub (1280x640).
// Sale de record.sh; se puede correr sola con la demo levantada.
import { chromium } from "playwright";

const BASE = process.env.DEMO_URL || "http://localhost:8080";

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 640 },
  deviceScaleFactor: 2, // se baja a 1280x640 con ffmpeg: texto más nítido
  locale: "es-CL",
  timezoneId: "America/Santiago",
});
const page = await ctx.newPage();
await page.goto(BASE, { waitUntil: "networkidle" });
await page.waitForTimeout(800);
await page.screenshot({ path: "out/social.png" });
await browser.close();
