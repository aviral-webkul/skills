# Verification map — blog claim → code evidence

Build a claim→evidence note as you go. Every sentence you keep or write must map to a file and a
line you have actually read.

## Menu paths

The most frequently wrong claim in an old Bagisto blog, because menus get reorganised between
releases while the blog keeps the old breadcrumb.

- Admin: `src/Config/admin-menu.php` — the `key` gives the nesting
  (`marketplace.sales.mercadopago_payouts` → **Marketplace > Sales > Mercado Pago Payouts**).
- Seller: `src/Config/seller-menu.php` (`settings.mercadopago` → **Settings > Mercado Pago
  Configuration**).
- The visible label is the `name` key resolved through `src/Resources/lang/en/app.php`, **not** the
  menu key.
- Confirm visually in the running admin. A screenshot of the sidebar settles it instantly.

## Admin setting labels

`src/Config/system.php` gives field *names*; `lang/en/app.php` gives the *labels the user sees*.
These diverge, and blogs copy the wrong one.

A real example that shipped wrong for months:

```php
'api_key'             => 'Public Key',    // NOT "API Key"
'api_publishable_key' => 'Access Token',  // NOT "Publishable Key"
```

A blog that says "API Key (Access Token)" has them backwards. Resolve every label properly:

```bash
php artisan tinker --execute="echo trans('<ns>::app.admin.system.api_key').PHP_EOL;"
```

Shared Bagisto labels (`status`, `logo`, `sort-order`) come from `admin::app.configuration.index.
sales.payment-methods.*` — resolve those too rather than guessing.

Also diff the field list itself. New config fields are the most common *missing* feature: a
`webhook_secret` added in a later release will be absent from an older blog entirely.

## Installation steps

- **Dependencies:** read the package `composer.json`. If `"require": {}` is empty, any
  `composer require ...` step in the blog is wrong. Packages that call the API through Laravel's
  `Http` facade need no vendor SDK, even though the blog may tell readers to install one.
- **Registration:** a Bagisto package normally registers twice — the main provider in
  `bootstrap/providers.php`, and `ModuleServiceProvider` in `config/concord.php`. Check both, plus
  the `psr-4` entry in the root `composer.json`. Blogs routinely omit the concord step.
- **Install command:** the real signature, from `src/Console/Commands/*.php`.
- **Version:** `packages/Webkul/Core/src/Core.php` → `const BAGISTO_VERSION`. For a *sibling*
  package with no version string, do not guess — either find it on the live product/blog page via
  `WebFetch`, or state it as an assumption in your report.

## DataGrid claims

From `src/DataGrids/**`, per column: `searchable`, `sortable`, `filterable`. Do not write "sort any
column" when one column has `'sortable' => false`. Say "search by X, Y or Z, sort the list, filter by
A or B" and make each name true.

`prepareQueryBuilder()` also tells you what the grid is *of* — e.g. a `where('method', 'MercadoPago')`
over `marketplace_transactions` means the page lists **payouts**, not **accounts**.

## Views — what the user literally sees

Button and heading text comes from the Blade file, via its lang keys. Check for features the blog
claims that the view does not have. A page with a single "Allow for X Payment" button does **not**
have a connection-status panel or a revoke option, however sensible those would be.

Blade views also encode behaviour worth documenting: an inline validation warning, an SDK widget's
configured payment types (`creditCard: "all"`, `debitCard: "all"`), a theme option, a device
fingerprint script.

## Listeners and events — check the wiring, not just the class

Read the class **and** how it is registered. A correct listener registered wrongly never runs.

`Event::listen()` takes **one** listener. Passing the `$listen`-array shape is a real, shipped bug:

```php
// BROKEN — throws "Array callback must have exactly two elements" on dispatch
Event::listen('marketplace.sales.order.save.after', [[Order::class, 'makeTransations']]);

// CORRECT
Event::listen('marketplace.sales.order.save.after', [Order::class, 'makeTransations']);
```

Note the failure mode: the listener *registers* fine, so `getListeners()` shows the expected count.
It only throws when the event is dispatched. To test:

```bash
php artisan tinker --execute="
try { Event::dispatch('<event>', (object)['order_id'=>1,'marketplace_seller_id'=>1]); echo 'ok'; }
catch (\Throwable \$e) { echo 'ERR: '.\$e->getMessage(); }"
```

If a feature depends on a broken listener, say so in your report. The page exists and ships, so it
belongs in the blog — but the user must know it will stay empty until the wiring is fixed.

## Controllers — the flows

Trace each route to its controller method and note the user-visible consequences:

- Guard clauses → the rules to document ("one seller per cart", "seller must connect first").
- Side effects → order created, invoice raised, cart deactivated, status set.
- External calls → which API, what fields (a commission sent as `application_fee` vs
  `marketplace_fee`), and what happens on failure.
- Status maps → `approved → processing`, `rejected → canceled`, etc.

Where a guard exists in two places (a Blade-side warning *and* a controller redirect), the blog
should describe the user-facing one.

## Claims that need extra suspicion

| Blog says | Verify by |
|---|---|
| A menu path | `admin-menu.php` / `seller-menu.php` + a screenshot |
| A field label | `lang/en/app.php`, resolved with `trans()` |
| "seller can revoke / edit / delete X" | the Blade view — is there such a control? |
| `composer require <sdk>` | package `composer.json` |
| A version number | `Core::BAGISTO_VERSION`; siblings need a source |
| "admin can see all X accounts" | the DataGrid's `prepareQueryBuilder()` — what table? |
| "sort any column" | each column's `sortable` flag |
| Anything about emails/payouts firing | the listener **and** its registration |
