# Triage — differences that look like regressions and are not

Every candidate finding goes through this list before it reaches the report. Each entry gives the
command that settles it. If a difference matches one of these, it belongs in the report's
**excluded** section with the reason — not in the findings.

The cost of getting this wrong is asymmetric: one wrongly-reported config difference makes the
reader distrust every other entry.

---

## 1. Store configuration set in one database and not the other

**Looks like:** a button, block or badge present on one storefront and absent on the other, with
identical Blade markup.

Bagisto gates a lot of storefront UI on `core_config`. A value toggled in admin months ago on one
install and never touched on the other reads exactly like a removed feature.

```bash
php artisan tinker --execute="
foreach (\Webkul\Core\Models\CoreConfig::where('code','like','%<keyword>%')->get() as \$c)
    echo \$c->code.' => '.\$c->value.PHP_EOL;
"
```

Also check whether the **code itself moved** between versions. Bagisto ships migrations that rename
config codes, so the same setting can live under two different keys:

```bash
grep -rn "<keyword>" packages/Webkul/*/src/Database/Migrations/ packages/Webkul/Admin/src/Config/system.php
grep -rn "getConfigData('.*<keyword>" packages/Webkul/Shop/src/Resources/views/
```

If the key moved *and* a relocation migration carries the old value across, the mechanism is sound
and any difference you see is just the two databases holding different values.

**Verdict:** excluded — configuration, not code. Say which key and which value differs.

## 2. Seed / catalog data that differs

**Looks like:** missing rating badges, missing "Sale" flags, different product counts, a different
number of pages.

```bash
php artisan tinker --execute="echo \Webkul\Product\Models\ProductReview::count();"
php artisan tinker --execute="echo \Webkul\Product\Models\Product::count();"
```

A star-rating badge that renders on one card and not the other is almost always "that database has
one approved review and the other has none".

**Verdict:** excluded — data. Establish these counts in Phase 1 so you never write the finding.

## 3. Theme sections / Appearance content

**Looks like:** a completely different home page — different section order, extra or missing
banners, a services strip above the footer on one side only.

Storefront home-page content lives in the database, not in Blade. Two installs seeded at different
times legitimately have different sections.

```bash
php artisan tinker --execute="
foreach (\Webkul\Theme\Models\Section::all() as \$s) echo \$s->id.' '.\$s->type.PHP_EOL;
"
```

**Verdict:** excluded — content. But note the exception: if a section *is* present on both and one
renders **blank or broken**, that is a real finding. Distinguish "different section" from "same
section, failing to render".

## 4. `APP_URL` that the test browser cannot reach

**Looks like:** broken images, missing locale flags, a broken-image icon in the header.

```bash
grep -E '^APP_URL' .env
curl -s "$URL/" | grep -oE 'src="[^"]*(locales|storage)[^"]*"' | head -3
```

If the emitted `src` points at a host or IP that is not the one you are browsing, that is your local
environment, and it usually affects both installs in slightly different ways.

**Verdict:** excluded — environment.

**But look carefully before dismissing it.** A *doubled base path* — `http://host/app/public/app/public/storage/...`
— is a code bug, not an environment one. It comes from `url()` being handed a path that already
contains the app's base path, and it only manifests on sub-directory installs:

```bash
php artisan tinker --execute="
echo parse_url(\Illuminate\Support\Facades\Storage::url('x.webp'), PHP_URL_PATH).PHP_EOL;
echo url(parse_url(\Illuminate\Support\Facades\Storage::url('x.webp'), PHP_URL_PATH)).PHP_EOL;
"
```

Report it, and state the deployment shape it depends on.

## 5. Framework default pages

**Looks like:** the 404 or 500 page restyled.

```bash
curl -s "$URL/does-not-exist" | head -c 300
find packages/Webkul -path "*views/errors*" -name "*.blade.php"
```

If both installs fall through to the framework's bundled error page rather than the shop's own error
view, the change came with the framework upgrade and no Bagisto file is involved.

**Verdict:** report at most as Low/informational, and say explicitly that it is the framework page.

## 6. Lazy-loading artifacts in `fullPage` screenshots

**Looks like:** every product image below the fold is an empty grey box on one side.

Bagisto lazy-loads with an IntersectionObserver. A `fullPage` capture that did not scroll first
shows unloaded images. Re-capture with the scroll routine (`settle()` in `capture.js`) before
believing it.

Confirm from the DOM rather than the picture:

```js
await page.$$eval('img', els => els.map(e => ({ src: e.currentSrc, nw: e.naturalWidth })));
```

`naturalWidth: 0` on an image that is *above* the fold and stays 0 after `networkidle` is real.

**Verdict:** excluded — capture artifact, unless the DOM confirms it.

## 7. Debug bar

**Looks like:** a body-height or padding difference of a few dozen pixels; a strip of UI mid-page.

The debug bar injects its own body spacing and differs by version. Hide it with `addStyleTag`; never
change `.env`. A screenshot-height delta with an empty pixel-diff bounding box is this.

**Verdict:** excluded — environment.

## 8. Accessibility refactors

**Looks like:** large Blade diffs on almost every component.

`<span role="button" tabindex="0">` becoming `<button type="button">`, added `aria-*`, `hidden`
becoming `sr-only` on peer inputs, focus-visible rings. These are deliberate and visually neutral.

**Verdict:** excluded — intentional. Confirm neutrality with `pixdiff`; only report if the element
actually moved or resized.

## 9. Colour notation changes

**Looks like:** `rgb(229, 231, 235)` becoming `oklch(0.928 0.006 264.531)` in computed styles.

Same colour, new notation from the CSS framework. Compare rendered pixels, not computed strings.

**Verdict:** excluded — notation.

---

# Differences that ARE real — the recurring shapes

| Shape | How you prove it |
|---|---|
| A visibility class was dropped (`flex hidden` → `flex`) | `analyze-diff.py classes`; confirm the matching shimmer file kept `hidden` |
| A class compiles to nothing | `missing-classes.py` on both sides; only newly-missing counts |
| A class compiles differently | grep the generated rule in both built CSS files |
| A URL is built wrong | `curl` the emitted `src` and read the status code |
| An element changed size | `measure.js` — quote the numbers |

An element that pixel-differs, has a named cause, and is not on the excluded list is a finding.
Anything else is not.
