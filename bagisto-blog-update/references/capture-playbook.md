# Screenshot capture playbook

Every item here cost real debugging time on a live Bagisto install. Read it before launching a
browser.

## Environment — set these first

```bash
# In the project .env. Record the originals; restore them when you finish.
DEBUGBAR_ENABLED=false        # otherwise the debug bar sits across the bottom of every shot
RESPONSE_CACHE_ENABLED=false  # see below — this one is not cosmetic
php artisan optimize:clear
```

`RESPONSE_CACHE_ENABLED=true` makes repository writes that flush the full-page cache **hang for
minutes** under `artisan tinker`. If `InvoiceRepository::create()` or a similar call times out, this
is almost always why. Turning it off fixed a reproducible 120s+ hang.

If a write still hangs, the next suspect is mail. Inside the tinker script:

```php
config(['mail.default' => 'array']);
\Illuminate\Support\Facades\Mail::fake();
\Illuminate\Support\Facades\Notification::fake();
```

`MAIL_MAILER` in `.env` may be overridden by Bagisto's dynamic SMTP transport, so fake it in-process
rather than relying on the env var alone.

**Restore `.env` afterwards.** Delete keys you added; restore values you changed.

## Playwright without installing it

Browsers are usually already in `~/.cache/ms-playwright`. Reuse a module from another local project:

```js
const { chromium } = require('/path/to/other-project/node_modules/playwright');
```

`scripts/shots.js` wraps this — set `BASE`, then use `browser()`, `ctx(b, stateFile)`,
`loginAdmin()`, `loginSeller()`, `shot(page, name)`.

## Logging in

Credentials are usually already in the package's own e2e tests — check
`packages/Webkul/<Module>/tests/e2e-pw/utils/{admin,seller,customer}.ts` before asking the user.
Typical defaults: `admin@example.com / admin123`, `seller@example.com / password123`.

**Submit with `Enter`, not a click.** `button[type="submit"]` matches a hidden search button on
Bagisto login pages and the click times out:

```js
await page.fill('input[name="password"]', pass);
await page.press('input[name="password"]', 'Enter');   // works
```

Save `storageState` per role and reuse it; re-logging in for every shot is slow and flaky.

## URLs and selectors that bite

- **Admin config uses underscores:** `/admin/configuration/sales/payment_methods`. The hyphenated
  form 500s with `Undefined array key "payment-methods"`.
- **Config fields** are named `sales[payment_methods][<code>][<field>]`. Enumerate them to confirm
  the real field list:
  ```js
  await p.evaluate(() => [...document.querySelectorAll('input[name],select[name],textarea[name]')].map(e => e.name))
  ```
- **Modals/drawers** open from a `div`, not a `<button>`. Match the component's own class and scope
  it, or a sidebar link with the same word wins:
  ```js
  // "Refund" also matches the Sales > Refunds sidebar link — this picks the order action
  await p.locator('div.transparent-button').filter({ hasText: /^\s*Refund\s*$/ }).first().click();
  ```
- **Radios are visually hidden** (Tailwind `peer` pattern). Clicking the input does not fire Vue's
  `@change`; click the label: `label[for="flatrate_flatrate"]`.
- **Toggles** are checkboxes — flip with `el.evaluate(e => e.click())` after checking `isChecked()`.
- **The sidebar scrolls independently.** `window.scrollTo(0,0)` is not enough:
  ```js
  await p.evaluate(() => {
    window.scrollTo(0, 0);
    document.querySelectorAll('*').forEach(el => { if (el.scrollTop > 0) el.scrollTop = 0; });
  });
  ```

## DataGrids hide columns at 1120px

Bagisto's grid drops trailing columns when narrow, so a 1120-wide capture can silently lose the last
column. Capture at **1440x1131** and downscale to 1120x880 — the aspect ratio is identical
(1.2727), so nothing distorts:

```bash
convert grid-1440.png -resize 1120x880! grid.png
```

Verify the headers are all present before accepting the shot.

## Framing

Scroll to the smallest element that identifies the section, with headroom for its heading:

```js
await p.evaluate(() => {
  const f = document.querySelector('[name="sales[payment_methods][mercadopago][checkout_type]"]');
  const card = f.closest('.box-shadow');
  window.scrollTo({ top: card.getBoundingClientRect().top + window.scrollY - 150, behavior: 'instant' });
});
```

Always open the PNG with `Read` and look at it. Cropped headings, a stray debug bar, an empty grid
or the wrong page are obvious to the eye and invisible to the script.

## Seeding demo data

Prefer the real UI and real repositories; fall back to models; avoid raw SQL. Order for a
marketplace payment module:

1. Save the module's admin config (this also produces the config screenshot).
2. Create the seller via **Marketplace > Sellers > Add Sellers**, then approve
   (`Seller::find(1)->update(['is_approved' => 1])`).
3. Assign products — `admin/marketplace/catalog/products/assign/{sellerId}/{productId}`. The
   **Condition** select is required and easy to miss; the save silently no-ops without it.
4. Pick products that are `type=simple`, `parent_id IS NULL`, **and `visible_individually=1`**.
   Configurable variants look like simple products in the table but 404 on the storefront.
5. Set `marketplace_products.is_owner = 1`. Without it the cart item carries no
   `additional.seller_info`, and every seller-scoped feature stays empty.
6. Register the customer through the storefront sign-up.
7. Drive the storefront to the payment step.

### Checkout state does not survive a reload

The one-page checkout step resets on `goto`. Address → shipping → payment must happen in **one
continuous page session**. Also make the address step adaptive: once the customer has a saved
address, the form is replaced by a saved-address picker, so a script that blindly fills
`input[name="billing.first_name"]` works the first run and times out the second.

### When the gateway blocks the real flow

With dummy credentials the SDK will not initialise, so the order cannot complete in the browser.
Create it through the module's own code path instead — mirror the controller's `createOrder()`:

```php
$data  = (new \Webkul\Sales\Transformers\OrderResource($cart))->jsonSerialize();
$order = $orderRepo->create($data);
$orderRepo->update(['status' => 'processing', '<gateway>_payment_id' => '...'], $order->id);
// then invoice; then $cart->update(['is_active' => 0]);
```

**Create the invoice with events enabled.** Marketplace's own invoice listener is what populates
`marketplace_orders.base_seller_total_invoiced`, and downstream payout logic reads it — with events
suppressed the invoice exists but every seller total stays 0. If a listener in the chain is broken,
call the specific listeners you need by hand rather than suppressing all of them.

Verify seeded state in the DB before capturing; an empty grid wastes a whole capture pass.

## Converting

```bash
scripts/to_webp.sh <png-dir> <out-dir>     # resizes to 1120x880 and converts, quality 85
```

Requires ImageMagick with WebP support: `convert -list format | grep -i webp`.
