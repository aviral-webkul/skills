/**
 * Read computed styles for a class set on both storefronts.
 *
 *   node measure.js config.json
 *
 * Use this when a screenshot is ambiguous. It turns "the button looks smaller"
 * into "padding-left 74.5px -> 32px, width 155px -> 70px", which is the
 * difference between a report someone can act on and one they have to re-verify.
 *
 * Edit CASES below for the situation at hand: give each case the class string as
 * written in the BASELINE and as written in the CANDIDATE. The element is
 * injected off-screen on a real page, so component classes (.primary-button,
 * .secondary-button, .shimmer) resolve exactly as they do in the live layout.
 */
const fs = require('fs');

const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const { chromium } = require(cfg.playwright);

const CASES = {
    loadMoreSpinner: {
        baseline: 'secondary-button mx-auto mt-14 block w-max rounded-2xl px-[74.5px] py-3.5',
        candidate: 'secondary-button mx-auto mt-14 block w-max rounded-2xl px-18.625 py-3.5',
    },
    carouselViewAllShimmer: {
        baseline: 'shimmer mx-auto mt-16 block h-12 w-[150.172px] rounded-2xl',
        candidate: 'shimmer mx-auto mt-16 block h-12 w-37.543 rounded-2xl',
    },
};

const PROBE_PAGE = '/';

(async () => {
    const browser = await chromium.launch();
    const results = {};

    for (const side of [cfg.baseline, cfg.candidate]) {
        const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
        const page = await ctx.newPage();
        await page.goto(side.url + PROBE_PAGE, { waitUntil: 'networkidle' });

        const classes = Object.fromEntries(
            Object.entries(CASES).map(([name, v]) => [name, v[side.key] ?? v.candidate])
        );

        results[side.key] = await page.evaluate((classes) => {
            const out = {};

            for (const [name, cls] of Object.entries(classes)) {
                const el = document.createElement('div');
                el.className = cls;
                el.innerHTML = '&nbsp;';
                el.style.position = 'absolute';
                el.style.top = '-9999px';
                document.body.appendChild(el);

                const cs = getComputedStyle(el);
                const rect = el.getBoundingClientRect();

                out[name] = {
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    padding: cs.padding,
                    margin: cs.margin,
                    fontSize: cs.fontSize,
                    lineHeight: cs.lineHeight,
                    borderRadius: cs.borderRadius,
                };

                el.remove();
            }

            return out;
        }, classes);

        await ctx.close();
    }

    for (const name of Object.keys(CASES)) {
        const a = results[cfg.baseline.key][name];
        const b = results[cfg.candidate.key][name];
        const changed = Object.keys(a).filter((k) => a[k] !== b[k]);

        console.log(`\n${name}${changed.length ? '' : '  (identical)'}`);
        for (const k of changed) {
            console.log(`  ${k}: ${a[k]}  ->  ${b[k]}`);
        }
    }

    await browser.close();
})();
