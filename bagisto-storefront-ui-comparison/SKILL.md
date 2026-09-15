---
name: bagisto-storefront-ui-comparison
description: Compare the storefront (shop) UI of two Bagisto installations — a stable baseline and a candidate — and report only genuine visual gaps and regressions in a bag-report.md. Asks which project is the stable baseline and which is under test; never assumes a version. Drives both sites with Playwright, pixel-diffs and side-by-sides every page at desktop and mobile, and cross-checks findings against the Blade/Tailwind diff and the compiled theme CSS so config, seed-data and environment differences are excluded rather than reported. Use when asked to compare storefront UI between two Bagisto projects/versions, find UI regressions after an upgrade, or QA a theme migration.
---

# Bagisto Storefront UI Comparison

Compares the **storefront only** of two Bagisto installations and produces a report of confirmed
visual regressions.

## The one rule that governs everything

**A difference is not a finding until you know what causes it.**

Most differences between two Bagisto installs are *not* regressions. They are store-config values,
seed data, theme-section content, or a broken `APP_URL`. Reporting those as bugs makes the report
worthless, because the reader has to re-verify everything you wrote.

Every entry in the report must survive this test: **you can name the file, the class, the config
key or the DB row that causes it, and you have checked that the other install does not simply have
different data.** If you cannot, it goes in the "excluded" section with the reason — not in the
findings.

## Scope

**In scope:** layout and spacing, typography, buttons and icons, forms and inputs, product listings
and product pages, cart and checkout, header/footer/navigation/menus, filters and sorting, modals,
dropdowns, drawers, alerts and flash messages, responsive/mobile layout, empty states, loading
skeletons.

**Out of scope — do not check or report:** the admin panel, feature changes, functionality changes,
backend/API behaviour, performance. Do not modify application code in either project.

---

## Phase 0 — Establish the two projects (always ask)

**Never assume which install is the baseline, and never infer it from version numbers, directory
names, or git branches.** Two directories called `bagisto24` and `bag-master2` tell you nothing
about which one the user considers stable.

1. Discover candidates:

   ```bash
   ls -d /path/to/webroot/*/ | head -50
   ```

   For each plausible directory, read its identity without guessing:

   ```bash
   grep -m1 '"version"' composer.json; git log --oneline -1; grep -E '^APP_URL|^DB_DATABASE' .env
   ```

2. **Ask the user with `AskUserQuestion`** — two single-select questions in one call:

   - "Which project is the **stable baseline** (the reference the other is measured against)?"
   - "Which project do you want to **check for regressions**?"

   Offer the most likely directories as options (max 4 each; the user can always pick "Other" and
   type a path). Label each option with the directory name and, in the description, its detected
   version / branch / database so the user can tell them apart.

3. Record the answer in your own words before proceeding, e.g.
   *"Baseline = `bagisto24`; under test = `bag-master2`."* Everything downstream reads
   `BASELINE` and `CANDIDATE` — **never hard-code a version number anywhere**, including the
   report. Refer to them by the user's project names, adding the detected version only as a
   parenthetical.

---

## Phase 1 — Make the comparison valid

A side-by-side is only evidence if both sides are actually comparable. Gate on all four:

1. **Both storefronts respond.**

   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" -m 10 "$BASELINE_URL/"
   curl -s -o /dev/null -w "%{http_code}\n" -m 10 "$CANDIDATE_URL/"
   ```

   Use the URL the browser can actually reach, which is often **not** the `APP_URL` in `.env`.
   Note any mismatch — it explains broken images later and must not be reported as a regression.

2. **Seed data matches.** Compare categories and products in both databases:

   ```bash
   php artisan tinker --execute="
   foreach(\Webkul\Category\Models\CategoryTranslation::take(10)->get() as \$c) echo \$c->category_id.' '.\$c->slug.PHP_EOL;
   foreach(\Webkul\Product\Models\Product::take(8)->get() as \$p) echo \$p->id.' '.\$p->type.' '.\$p->url_key.PHP_EOL;
   "
   ```

   If the slugs and URL keys line up, every page can be compared at the same URL path. If they do
   not, say so in the report and compare only pages that do not depend on catalog data.

3. **Record the data that will differ anyway.** Counts you will need in order to *dismiss* false
   findings later — do this now, not after you have written a wrong finding:

   ```bash
   php artisan tinker --execute="echo \Webkul\Product\Models\ProductReview::count();"   # rating badges
   php artisan tinker --execute="foreach(\Webkul\Customer\Models\Customer::take(3)->get() as \$c) echo \$c->id.' '.\$c->email.PHP_EOL;"
   ```

4. **Find a usable Playwright.** The repo's own `node_modules` often has a version whose browser
   revision was never downloaded. List what is installed and match it to the cached browsers:

   ```bash
   ls ~/.cache/ms-playwright                                     # e.g. chromium-1234
   find ~ -maxdepth 8 -type d -name playwright-core -path "*node_modules*" 2>/dev/null |
     while read d; do echo "$(grep -m1 '"version"' "$d/package.json") $d"; done
   ```

   Use the **newest** matching install; require it by absolute path in the scripts. If none works,
   `npm install playwright && npx playwright install chromium` in the scratchpad — never in either
   project.

---

## Phase 2 — Capture

Use `scripts/capture.js` with a JSON config (see `scripts/config.example.json`). It captures both
sites in one run so lighting conditions are identical.

Three capture rules that are not optional, because each one caused a false finding when skipped:

- **Hide the debug bar** (`.phpdebugbar, #phpdebugbar { display: none !important }`) via
  `addStyleTag`. Never disable it in `.env` — that modifies the project.
- **Scroll the page to the bottom in steps before screenshotting.** Bagisto lazy-loads images with
  an IntersectionObserver. A `fullPage` screenshot without scrolling shows empty grey boxes that
  look exactly like broken images.
- **Capture at 1440×900 and 390×844.** Several regressions only exist in one of the two.

Cover, at minimum:

| Group | Pages / states |
|---|---|
| Catalog | home, category listing (grid **and** list view), search results, empty search |
| Product | simple product, configurable product, reviews tab, image zoomer |
| Cart & checkout | empty cart, filled cart, one-page checkout as guest **and** logged in, coupon block |
| Account | login, register, forgot password, profile, orders, addresses, address create, wishlist (empty and with items), reviews |
| Other | compare (empty and with items), CMS page, contact, 404 |
| Interactive | mega menu, all-categories drawer, mini cart, account dropdown, mobile hamburger menu, mobile filter drawer, mobile sort drawer, flash message |
| Loading | shimmer states — see Phase 4 |

For logged-in pages, register one test customer through the storefront form on **both** sites
(`scripts/capture.js --flow account`). That is data in a dev database, not a code change; say so in
the report.

To reach a filled cart you need a product that is **visible individually** and has no super
attributes:

```bash
php artisan tinker --execute="
foreach(\Webkul\Product\Models\Product::where('type','simple')->whereNull('parent_id')->get() as \$p)
  if (\$p->visible_individually && ! \$p->super_attributes->count()) { echo \$p->url_key.PHP_EOL; }
" | head -3
```

## Phase 3 — Compare the pixels

`scripts/compare.py` provides three modes. Use them in this order:

```bash
python3 compare.py pixdiff <dir> <page> <viewport>   # first: is there any difference at all?
python3 compare.py sbs     <dir> <page> <viewport> [y0 y1]   # then: what does it look like?
python3 compare.py zoom    <dir> <page> <viewport> x0 y0 x1 y1 scale   # finally: what exactly changed?
```

`pixdiff` prints a bounding box and the row bands that differ. **Run it on every page first** — it
turns a 25-page eyeball exercise into a short list of regions worth looking at, and it proves
equivalence on the pages where nothing changed (worth stating in the report).

Screenshot heights will differ slightly even on identical pages because the debug bar leaves body
padding. A `None` bbox with a small height delta means "identical".

## Phase 4 — Cross-check against the code

Pixels tell you *that* something changed. These four checks tell you *why*, and they are what
separates a finding from a guess.

### 4a. Structural Blade diff

```bash
diff -ru "$BASELINE/packages/Webkul/Shop/src/Resources/views" \
         "$CANDIDATE/packages/Webkul/Shop/src/Resources/views" > shop-views.diff
python3 scripts/analyze-diff.py shop-views.diff structural
```

`structural` strips `class="…"` from both sides and prints only the hunks whose *markup* changed,
which filters out the thousands of pure styling renames. Most of what survives is accessibility
work (`<span role=button>` → `<button>`, `aria-*`, `sr-only`) — read it, do not report it.

### 4b. Visibility-class diff

```bash
python3 scripts/analyze-diff.py shop-views.diff classes
```

Prints, per file, layout-critical class tokens that were **removed or added** — `hidden`, `flex`,
`block`, `absolute`, `sr-only`, `overflow-*`, `z-*`. A dropped `hidden` is the classic way a
placeholder becomes visible. Cross-check each hit against the matching shimmer/skeleton file: if
the skeleton kept `hidden` and the real component lost it, the change is unintended.

### 4c. Classes that compile to nothing

This is the highest-yield check after a Tailwind major upgrade, and it is invisible in a Blade diff.

```bash
python3 scripts/missing-classes.py \
  "$CANDIDATE/packages/Webkul/Shop/src/Resources/views" \
  "$CANDIDATE/public/themes/shop/default/build/assets/*.css"
```

Run it on the **baseline too** and report only what is newly missing — some misses are pre-existing
and not regressions.

Known cause: **Tailwind v4 only generates spacing utilities for multiples of `0.25`.** An automated
`px-[74.5px]` → `px-18.625` conversion silently emits no rule at all, and the element falls back to
whatever a component class gives it. Values like `w-37.543`, `h-9.375`, `px-12.7` are always bugs.

### 4d. Same class, different meaning

A class can compile and still behave differently. Grep for stacked variants where a pseudo-element
variant comes first, then compare the generated rule in both builds:

```bash
grep -rhoE '\b(after|before|placeholder|file|marker|selection|backdrop):[a-z-]+:[a-z0-9-]+' \
  "$CANDIDATE/packages/Webkul/Shop/src/Resources/views" | sort -u

grep -o '\.after\\:last\\:hidden[^{]*{[^}]*}' "$BASELINE"/public/themes/shop/default/build/assets/*.css
grep -o '\.after\\:last\\:hidden[^{]*{[^}]*}' "$CANDIDATE"/public/themes/shop/default/build/assets/*.css
```

Tailwind v4 reversed stacked-variant order, so `after:last:hidden` (v3: `:last-child::after
{display:none}`) now means something else and the rule is lost. Other v4 traps worth a look:
`ring` default width, bare `shadow`/`rounded`/`blur` renames, `outline-none` → `outline-hidden`,
and the default border colour (check for a `border-color` compat block in the theme's `app.css`).

### 4e. Hard numbers when a screenshot is ambiguous

Inject the class onto a throwaway element on the live page and read the computed style. This turns
"the button looks smaller" into "padding-left 74.5px → 32px, width 155px → 70px", which is what
makes a report actionable:

```bash
node scripts/measure.js config.json   # edit the CLASSES map inside for the case at hand
```

---

## Phase 5 — Triage before you write

Run every candidate finding through `references/triage.md`. It lists the differences that look like
regressions and are not, with the exact command that proves it — store config, seed data, theme
sections, `APP_URL`, framework error pages, lazy-load screenshot artifacts.

A finding is only real when you can state its cause. Everything you dismissed goes into the
report's "excluded" section **with the reason**, so the reader does not re-open it.

## Phase 6 — Write `bag-report.md`

Write it to the **candidate** project root (the one under test), using
`templates/report-template.md`. Every finding carries:

- Page/section
- Severity — High (breaks a primary page for real users) / Medium (visible on many pages, or wrong
  content shown) / Low (transient, loading-only, or cosmetic in one place)
- Expected UI, described as the baseline behaves — by project name, not by version number
- Actual UI in the candidate
- Cause, with the file:line, class, or config key
- Steps to reproduce
- Measured numbers where you have them

Then two sections that make the report trustworthy:

- **Excluded as intentional / config / data / environment**, each with its reason.
- **Areas checked and found equivalent** — naming what you verified, so the reader knows the
  coverage rather than guessing.

Finally, report honestly in your summary message: what you changed (only `bag-report.md`), what
data you created (the test customer), and any finding whose severity depends on deployment shape.

---

## Reference files

| File | Use |
|---|---|
| `scripts/config.example.json` | Config shape for every script |
| `scripts/capture.js` | Screenshot both sites: pages, viewports, interactive states, account flow |
| `scripts/compare.py` | `pixdiff` / `sbs` / `zoom` |
| `scripts/analyze-diff.py` | `structural` / `classes` views of a Blade diff |
| `scripts/missing-classes.py` | Classes used in Blade but absent from the compiled CSS |
| `scripts/measure.js` | Computed-style numbers for a specific class set |
| `references/triage.md` | The false-positive catalogue and how to prove each one |
| `templates/report-template.md` | Report skeleton |
