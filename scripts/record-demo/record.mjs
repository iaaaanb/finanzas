// Graba la demo de Finanzas manejando Chromium con Playwright.
// Salida: out/demo.webm (video) + out/shots/*.png (capturas para el README).
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.DEMO_URL || "http://localhost:8080";
const OUT = path.resolve("out");
const SHOTS = path.join(OUT, "shots");
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(SHOTS, { recursive: true });

const W = 1240;
const H = 760;

// Cursor sintético: Playwright no dibuja el puntero en el video, así que lo
// pintamos nosotros escuchando los mismos eventos que dispara page.mouse.
const CURSOR_SCRIPT = () => {
  const install = () => {
    if (document.getElementById("__demo_cursor")) return;
    const c = document.createElement("div");
    c.id = "__demo_cursor";
    c.style.cssText = `
      position: fixed; left: -100px; top: -100px; z-index: 2147483647;
      width: 20px; height: 20px; margin: -10px 0 0 -10px; border-radius: 50%;
      background: rgba(255,255,255,0.95);
      box-shadow: 0 0 0 2px rgba(0,0,0,0.45), 0 3px 10px rgba(0,0,0,0.5);
      pointer-events: none; transition: transform 90ms ease;`;
    document.documentElement.appendChild(c);

    document.addEventListener("mousemove", (e) => {
      c.style.left = e.clientX + "px";
      c.style.top = e.clientY + "px";
    }, true);

    document.addEventListener("mousedown", (e) => {
      c.style.transform = "scale(0.65)";
      const r = document.createElement("div");
      r.style.cssText = `
        position: fixed; left: ${e.clientX}px; top: ${e.clientY}px;
        z-index: 2147483646; width: 20px; height: 20px; margin: -10px 0 0 -10px;
        border-radius: 50%; border: 2px solid rgba(96,165,250,0.9);
        pointer-events: none; transition: all 420ms ease-out;`;
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => {
        r.style.width = "64px";
        r.style.height = "64px";
        r.style.margin = "-32px 0 0 -32px";
        r.style.opacity = "0";
      });
      setTimeout(() => r.remove(), 500);
    }, true);

    document.addEventListener("mouseup", () => {
      c.style.transform = "scale(1)";
    }, true);
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install);
  } else {
    install();
  }
};

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: W, height: H },
    deviceScaleFactor: 1,
    locale: "es-CL",
    timezoneId: "America/Santiago",
    recordVideo: { dir: OUT, size: { width: W, height: H } },
    reducedMotion: "no-preference",
  });
  await context.addInitScript(CURSOR_SCRIPT);
  const page = await context.newPage();

  // --- helpers ---
  let cursor = { x: W / 2, y: H / 2 };
  const moveTo = async (x, y, steps = 28) => {
    await page.mouse.move(x, y, { steps });
    cursor = { x, y };
  };
  const clickOn = async (locator, { after = 700 } = {}) => {
    await locator.scrollIntoViewIfNeeded();
    const box = await locator.boundingBox();
    if (!box) throw new Error("elemento sin bounding box: " + locator);
    await moveTo(box.x + box.width / 2, box.y + box.height / 2);
    await wait(260);
    await page.mouse.down();
    await wait(90);
    await page.mouse.up();
    await wait(after);
  };
  const shot = (name) => page.screenshot({ path: path.join(SHOTS, `${name}.png`) });

  // ------------------------------------------------------------------
  // 1. Portada: saldos, presupuestos y bandeja de pendientes
  // ------------------------------------------------------------------
  await page.goto(BASE, { waitUntil: "networkidle" });
  await moveTo(W / 2, H / 2, 1);
  await wait(1900);
  await shot("01-portada");

  // ------------------------------------------------------------------
  // 2. Ir a Sincronización y traer los emails nuevos
  // ------------------------------------------------------------------
  await clickOn(page.getByRole("link", { name: /Sincronizaci/ }), { after: 1100 });
  await shot("02-sync-antes");

  await clickOn(page.getByRole("button", { name: "Traer emails nuevos" }), { after: 200 });
  await page.getByText(/traído/).first().waitFor({ timeout: 15000 });
  await wait(2400);
  await shot("03-sync-resultado");

  // ------------------------------------------------------------------
  // 3. Volver a la portada: las transacciones nuevas ya están pendientes
  // ------------------------------------------------------------------
  await clickOn(page.getByRole("link", { name: "Finanzas" }), { after: 1500 });
  await shot("04-pendientes");

  // ------------------------------------------------------------------
  // 4. Abrir un pendiente: viene con categoría y presupuesto puestos por
  //    la regla de auto-asignación, y con el email de origen adjunto
  // ------------------------------------------------------------------
  await clickOn(
    page.getByRole("link").filter({ hasText: "JUMBO KENNEDY" }).first(),
    { after: 1400 }
  );
  await shot("05-detalle-transaccion");

  // ------------------------------------------------------------------
  // 5. Ver el email del banco que originó la transacción
  // ------------------------------------------------------------------
  await clickOn(page.getByRole("button", { name: "Ver email completo" }), { after: 1200 });
  await page.mouse.wheel(0, 170);
  await wait(2100);
  await shot("06-email-origen");

  await clickOn(page.getByRole("button", { name: "Ocultar email" }), { after: 800 });
  await page.mouse.wheel(0, -170);
  await wait(500);

  // ------------------------------------------------------------------
  // 6. Confirmar: se descuenta del saldo y del presupuesto en el sidebar
  // ------------------------------------------------------------------
  await clickOn(page.getByRole("button", { name: "Confirmar" }), { after: 1200 });
  await moveTo(150, 300);
  await wait(2600);
  await shot("07-confirmada");

  // Acá termina el video: lo que sigue son capturas sueltas para el README,
  // en un contexto sin grabación para no alargar el GIF.
  const video = page.video();
  await context.close();
  fs.renameSync(await video.path(), path.join(OUT, "demo.webm"));

  // ------------------------------------------------------------------
  // Capturas extra para el README
  // ------------------------------------------------------------------
  const still = await browser.newContext({
    viewport: { width: W, height: H },
    deviceScaleFactor: 2,
    locale: "es-CL",
    timezoneId: "America/Santiago",
  });
  const spage = await still.newPage();
  const stillShot = async (name, url, { scroll = 0 } = {}) => {
    await spage.goto(`${BASE}${url}`, { waitUntil: "networkidle" });
    if (scroll) await spage.mouse.wheel(0, scroll);
    await wait(700);
    await spage.screenshot({ path: path.join(SHOTS, `${name}.png`) });
  };
  await stillShot("08-feed-transacciones", "/transactions");
  await stillShot("09-presupuestos", "/budgets");
  await stillShot("10-errores-parseo", "/errors");
  await stillShot("11-cuentas", "/accounts");
  await stillShot("12-categorias", "/categories");
  await still.close();

  // Mobile: el layout responsive con el sidebar como drawer
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    locale: "es-CL",
    timezoneId: "America/Santiago",
  });
  const mpage = await mobile.newPage();
  await mpage.goto(BASE, { waitUntil: "networkidle" });
  await wait(700);
  await mpage.screenshot({ path: path.join(SHOTS, "13-mobile.png") });
  await mobile.close();

  await browser.close();
  console.log("listo:", path.join(OUT, "demo.webm"));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
