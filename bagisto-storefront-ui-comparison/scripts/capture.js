/**
 * Screenshot two Bagisto storefronts under identical conditions.
 *
 *   node capture.js config.json [--flow pages|interactive|account|cart|shimmer|all]
 *
 * Output: <out>/<name>__<viewport>__<baseline|candidate>.png
 * The two sites are always captured in the same run so lazy-loading, fonts and
 * rendering conditions are identical on both sides.
 */
const fs = require('fs');
const path = require('path');

const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const flowArg = process.argv.includes('--flow')
    ? process.argv[process.argv.indexOf('--flow') + 1]
    : 'all';

const { chromium } = require(cfg.playwright);

const HIDE = '.phpdebugbar, #phpdebugbar { display: none !important; }';
const SIDES = [cfg.baseline, cfg.candidate];
const VIEWPORTS = cfg.viewports || [['desktop', 1440, 900], ['mobile', 390, 844]];

fs.mkdirSync(cfg.out, { recursive: true });

const shot = (page, name, vp, side, full = true) =>
    page.screenshot({ path: path.join(cfg.out, `${name}__${vp}__${side.key}.png`), fullPage: full });

/**
 * Hide the debug bar, then walk the page to the bottom so every lazy-loaded
 * image has been requested before the screenshot is taken. Without this, a
 * fullPage capture shows empty grey boxes that look exactly like broken images.
 */
async function settle(page) {
    await page.addStyleTag({ content: HIDE }).catch(() => {});
    await page.evaluate(() => new Promise((resolve) => {
        let y = 0;
        const step = () => {
            window.scrollTo(0, y);
            y += 400;
            if (y < document.body.scrollHeight + 800) {
                setTimeout(step, 60);
            } else {
                window.scrollTo(0, 0);
                setTimeout(resolve, 400);
            }
        };
        step();
    }));
    await page.waitForTimeout(2500);
}

const ok = (side, vp, name) => console.log('OK  ', side.key, vp, name);
const fail = (side, vp, name, e) => console.log('FAIL', side.key, vp, name, e.message.split('\n')[0]);

async function capturePages(page, side, vp) {
    for (const [name, url] of cfg.pages || []) {
        try {
            await page.goto(side.url + url, { waitUntil: 'networkidle', timeout: 60000 });
            await settle(page);
            await shot(page, name, vp, side);
            ok(side, vp, name);
        } catch (e) { fail(side, vp, name, e); }
    }
}

async function login(page, side) {
    const c = cfg.credentials;

    try {
        await page.goto(side.url + '/customer/register', { waitUntil: 'networkidle' });
        await page.fill('input[name="first_name"]', c.firstName);
        await page.fill('input[name="last_name"]', c.lastName);
        await page.fill('input[name="email"]', c.email);
        await page.fill('input[name="password"]', c.password);
        await page.fill('input[name="password_confirmation"]', c.password);
        await page.click('button[type="submit"]');
        await page.waitForTimeout(4000);
    } catch (e) { /* already registered on a previous run */ }

    await page.goto(side.url + '/customer/login', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', c.email);
    await page.fill('input[name="password"]', c.password);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(4000);
}

async function captureAccount(page, side, vp) {
    await login(page, side);

    for (const [name, url] of cfg.accountPages || []) {
        try {
            await page.goto(side.url + url, { waitUntil: 'networkidle', timeout: 60000 });
            await settle(page);
            await shot(page, name, vp, side);
            ok(side, vp, name);
        } catch (e) { fail(side, vp, name, e); }
    }
}

async function captureCart(page, side, vp) {
    try {
        await page.goto(side.url + cfg.standaloneProduct, { waitUntil: 'networkidle', timeout: 60000 });
        await page.addStyleTag({ content: HIDE });
        await page.locator('button[type="submit"]').filter({ hasText: /cart/i }).first().click({ timeout: 20000 });
        await page.waitForTimeout(3000);
        await shot(page, 'flash-added', vp, side, false);

        await page.goto(side.url + '/checkout/cart', { waitUntil: 'networkidle', timeout: 60000 });
        await settle(page);
        await shot(page, 'cart-filled', vp, side);

        await page.goto(side.url + '/checkout/onepage', { waitUntil: 'networkidle', timeout: 60000 });
        await settle(page);
        await shot(page, 'checkout', vp, side);
        ok(side, vp, 'cart+checkout');
    } catch (e) { fail(side, vp, 'cart+checkout', e); }
}

async function captureInteractive(page, side, vp) {
    const step = async (name, fn) => {
        try {
            await fn();
            await shot(page, name, vp, side, false);
            ok(side, vp, name);
        } catch (e) { fail(side, vp, name, e); }
    };
    const home = async () => {
        await page.goto(side.url + '/', { waitUntil: 'networkidle' });
        await page.addStyleTag({ content: HIDE });
        await page.waitForTimeout(1500);
    };

    if (vp === 'desktop') {
        await step('megamenu', async () => {
            await home();
            await page.locator('header a, header li').filter({ hasText: /^\s*MENS\s*$/i }).first().hover();
            await page.waitForTimeout(900);
        });
        await step('categories-drawer', async () => {
            await home();
            await page.locator('text=ALL').first().click({ timeout: 10000 });
            await page.waitForTimeout(1200);
        });
        await step('listview', async () => {
            await page.goto(side.url + cfg.category, { waitUntil: 'networkidle' });
            await page.addStyleTag({ content: HIDE });
            await page.waitForTimeout(1500);
            await page.locator('[class*="icon-list"]').first().click({ timeout: 10000 });
            await page.waitForTimeout(2500);
            await page.evaluate(() => window.scrollTo(0, 300));
            await page.waitForTimeout(800);
        });
        await step('minicart', async () => {
            await home();
            await page.locator('[class*="icon-cart"]').first().click({ timeout: 10000 });
            await page.waitForTimeout(1800);
        });
        await step('account-dropdown', async () => {
            await home();
            await page.locator('[class*="icon-users"]').first().click({ timeout: 10000 });
            await page.waitForTimeout(1500);
        });
    } else {
        await step('mobile-menu', async () => {
            await home();
            await page.locator('[class*="icon-hamburger"], [class*="icon-menu"]').first().click({ timeout: 10000 });
            await page.waitForTimeout(1200);
        });
        await step('mobile-filter', async () => {
            await page.goto(side.url + cfg.category, { waitUntil: 'networkidle' });
            await page.addStyleTag({ content: HIDE });
            await page.waitForTimeout(1500);
            await page.locator('text=FILTER').first().click({ timeout: 10000 });
            await page.waitForTimeout(1500);
        });
        await step('mobile-sort', async () => {
            await page.goto(side.url + cfg.category, { waitUntil: 'networkidle' });
            await page.addStyleTag({ content: HIDE });
            await page.waitForTimeout(1500);
            await page.locator('text=SORT').first().click({ timeout: 10000 });
            await page.waitForTimeout(1500);
        });
    }
}

/**
 * Hold every XHR open so the loading skeletons stay on screen. Skeleton sizing
 * regressions are invisible in a normal capture because the real content
 * replaces them within a second.
 */
async function captureShimmer(page, side, vp) {
    try {
        await page.route('**/api/**', async (route) => {
            await new Promise((r) => setTimeout(r, 60000));
            route.abort();
        });
        await page.goto(side.url + '/', { waitUntil: 'domcontentloaded' });
        await page.addStyleTag({ content: HIDE });
        await page.waitForTimeout(4000);
        await shot(page, 'shimmer-home', vp, side);

        const boxes = await page.$$eval('.shimmer', (els) => els.map((e) => {
            const r = e.getBoundingClientRect();
            return { w: Math.round(r.width), h: Math.round(r.height), cls: e.className.slice(0, 90) };
        }).filter((b) => b.w > 0 || b.h > 0));
        console.log('SHIMMER', side.key, vp, JSON.stringify(boxes.slice(0, 12)));
        ok(side, vp, 'shimmer');
    } catch (e) { fail(side, vp, 'shimmer', e); }
}

const FLOWS = {
    pages: capturePages,
    account: captureAccount,
    cart: captureCart,
    interactive: captureInteractive,
    shimmer: captureShimmer,
};

(async () => {
    const browser = await chromium.launch();

    for (const side of SIDES) {
        for (const [vp, width, height] of VIEWPORTS) {
            const wanted = flowArg === 'all' ? Object.keys(FLOWS) : [flowArg];

            for (const flow of wanted) {
                const ctx = await browser.newContext({ viewport: { width, height } });
                const page = await ctx.newPage();
                await FLOWS[flow](page, side, vp);
                await ctx.close();
            }
        }
    }

    await browser.close();
})();
