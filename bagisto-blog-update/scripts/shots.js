/**
 * Playwright helper for Bagisto blog screenshots.
 *
 *   const S = require('<skill>/scripts/shots.js');
 *   S.configure({ base: 'http://host/project/public', playwright: '/path/node_modules/playwright' });
 *
 *   const b  = await S.browser();
 *   const c  = await S.ctx(b, 'admin-state.json');
 *   const p  = await c.newPage();
 *   await S.loginAdmin(p); await c.storageState({ path: 'admin-state.json' });
 *   await p.goto(S.BASE + '/admin/configuration/sales/payment_methods', { waitUntil: 'networkidle' });
 *   await S.scrollTo(p, '[name="sales[payment_methods][x][title]"]', 150);
 *   await S.shot(p, 'shots', 'my-screenshot-name');
 *
 * Capture PNG here; convert with to_webp.sh.
 */

let PW = null;
let cfg = {
  base: process.env.BAGISTO_URL || 'http://localhost',
  width: 1120,
  height: 880,
  // Grids drop trailing columns at 1120px. Same 1.2727 aspect ratio, downscaled later.
  gridWidth: 1440,
  gridHeight: 1131,
  admin: { email: 'admin@example.com', password: 'admin123' },
  seller: { email: 'seller@example.com', password: 'password123' },
};

function configure(opts = {}) {
  if (opts.playwright) PW = require(opts.playwright);
  Object.assign(cfg, opts);
  module.exports.BASE = cfg.base;
  return cfg;
}

function pw() {
  if (PW) return PW;
  // Reuse a Playwright install from another local project; browsers are usually cached already.
  for (const p of (cfg.playwrightCandidates || [])) {
    try { PW = require(p); return PW; } catch (e) { /* try next */ }
  }
  PW = require('playwright');
  return PW;
}

async function browser() {
  return pw().chromium.launch({ args: ['--force-device-scale-factor=1'] });
}

/** Standard 1120x880 context. Pass grid:true for the wide grid context. */
async function ctx(b, state, opts = {}) {
  const w = opts.grid ? cfg.gridWidth : cfg.width;
  const h = opts.grid ? cfg.gridHeight : cfg.height;
  return b.newContext({
    viewport: { width: w, height: h },
    deviceScaleFactor: 1,
    storageState: state && require('fs').existsSync(state) ? state : undefined,
  });
}

/** Submit with Enter — button[type=submit] matches a hidden search button on Bagisto login pages. */
async function login(page, url, email, password, waitFor) {
  await page.goto(cfg.base + url, { waitUntil: 'domcontentloaded' });
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.press('input[name="password"]', 'Enter');
  if (waitFor) await page.waitForURL(waitFor, { timeout: 30000 });
  else await page.waitForTimeout(4000);
}

const loginAdmin = (p) =>
  login(p, '/admin/login', cfg.admin.email, cfg.admin.password, '**/admin/dashboard**');
const loginSeller = (p) =>
  login(p, '/seller/login', cfg.seller.email, cfg.seller.password, null);

/** Scroll so `selector` sits `offset` px below the viewport top. */
async function scrollTo(page, selector, offset = 120, closest = null) {
  await page.evaluate(([sel, off, cl]) => {
    let el = document.querySelector(sel);
    if (!el) return false;
    if (cl) el = el.closest(cl) || el;
    window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - off, behavior: 'instant' });
    return true;
  }, [selector, offset, closest]);
  await page.waitForTimeout(400);
}

/** Reset window AND any inner scrollers (Bagisto sidebars scroll independently). */
async function resetScroll(page) {
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    document.querySelectorAll('*').forEach((el) => { if (el.scrollTop > 0) el.scrollTop = 0; });
  });
  await page.waitForTimeout(400);
}

async function shot(page, dir, name) {
  const fs = require('fs');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${dir}/${name}.png` });
  console.log('captured', name);
}

/** List every named form field — use to confirm the real config field set. */
const fields = (page) =>
  page.evaluate(() =>
    [...document.querySelectorAll('input[name],select[name],textarea[name]')].map((e) => e.name));

module.exports = {
  configure, browser, ctx, login, loginAdmin, loginSeller,
  scrollTo, resetScroll, shot, fields, cfg,
  BASE: cfg.base,
};
