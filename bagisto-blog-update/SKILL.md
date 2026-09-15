---
name: bagisto-blog-update
description: Audit and update an EXISTING blog/user-guide HTML file for a Bagisto module so every claim matches the current package code, then recapture the screenshots it references. Re-reads the module source as the only source of truth (package CLAUDE.md/AGENTS.md/README are treated as stale), finds outdated or wrong claims, adds shipped features the blog is missing, refuses to document features the code does not have, and preserves the existing Gutenberg/HTML structure exactly. Seeds demo data in a running install, captures screenshots with Playwright at a fixed size, converts to WebP with filename == alt text, and runs a Yoast-style SEO pass (keyphrase in intro/subheadings/density, verified internal links). Use when asked to update / refresh / correct / fact-check / re-illustrate / SEO-fix an existing Bagisto module blog or user guide.
---

# Bagisto Blog Update

Update an **existing** blog file so it tells the truth about the **current** code, without redesigning it.

This is not the skill for writing a new post from scratch (`bagisto-blog`) or for turning a module
into a fresh announcement post (`bagisto-feature-blog`). Use this one when a blog already exists and
has drifted from the package.

## The one rule that governs everything

**The package `src/` is the only source of truth.**

The package's own `CLAUDE.md`, `AGENTS.md` and `README.md` are documentation, and documentation
drifts exactly like the blog you were asked to fix. In real runs they have described controllers,
DataGrids, routes, view paths and composer package names that no longer exist. Treat them as hints
about intent, never as evidence about behaviour.

Corollary: **never describe a feature you have not located in code**, and never delete a claim you
have not disproved in code. "I could not find it" is a question for the user, not a licence to cut.

## Order of work

1. Gather inputs (below).
2. Map the package — the real file tree, not the documented one.
3. Build a claim → code map for every sentence already in the blog.
4. Write the updated blog.
5. Seed data and capture screenshots.
6. Validate (structure, images, SEO).
7. Report — including any bugs you found in the module.

Steps 2–4 do not need a running site. Do them first; they are the bulk of the value and they are
never blocked. Only step 5 needs the install.

## Gather first

Ask only for what you cannot determine yourself, and ask it in one batch:

- **Blog file path** — usually `packages/Webkul/<Module>/blog.html`. Often already open in the IDE.
- **Focus keyphrase**, exactly as it will be set in Yoast. Ask for the literal string; "Marketplace
  Mercado Pago Payment" and "Laravel Marketplace Mercado Pago Payment Gateway" score completely
  differently and you cannot guess which one they set.
- **Install URL + logins**, if screenshots are wanted. Check `.env` `APP_URL` and the package's
  `tests/e2e-pw/utils/*.ts` first — credentials are usually already there, so this often needs no
  asking.
- **Real gateway/API credentials, or permission to use dummy ones.** Decide this before capturing:
  screens rendered by a third party (a payment SDK widget, a hosted checkout, an OAuth consent page)
  **cannot** be captured with dummy keys. Say so up front rather than discovering it late.

Do not ask for the screenshot size unless the blog is inconsistent. **1120x880 WebP** is the house
standard.

## Map the package before reading the blog

```bash
find packages/Webkul/<Module>/src -type f | sort
cat packages/Webkul/<Module>/composer.json
```

Diff that tree against what the package docs claim. Where they disagree, the tree wins — and say so
in your final report, because a stale package CLAUDE.md is itself worth flagging.

Then read, in this order, because each one settles a different class of blog claim:

| Read | Settles |
|---|---|
| `src/Config/system.php` + `src/Resources/lang/en/app.php` | The admin settings list, and the **exact field labels** |
| `src/Config/admin-menu.php`, `seller-menu.php`, `acl.php` | The real menu paths — the single most common stale claim |
| `src/Routes/*.php` | Which screens exist at all |
| `src/Http/Controllers/**` | What actually happens on each action |
| `src/Listeners/*`, `src/Providers/EventServiceProvider.php` | Background behaviour, and whether it is wired correctly |
| `src/Resources/views/**` | What the user literally sees; button and heading text |
| `src/DataGrids/**` | Grid columns, and which are searchable/sortable/filterable |
| `composer.json` | Real dependencies — installation steps love to invent these |
| `packages/Webkul/Core/src/Core.php` → `BAGISTO_VERSION` | The version line |

`references/verification-map.md` has the detail, including the failure modes these blogs hit again
and again. Read it before you start editing.

## Preserve the structure

The user is asking for a content correction, not a redesign. Hold these fixed:

- Same number of headings, at the same levels, in the same order.
- Same block types in the same sequence.
- Same trailing whitespace, `&nbsp;`, `&#91;` and curly-quote quirks in untouched blocks.

What you **may** change: heading *wording* (when it is factually wrong, or to carry the keyphrase),
sentences, list items, and image blocks. Adding a list item or a paragraph inside an existing section
is a content change and is fine. Adding a new `<h3>` section is not — fold the new feature into the
section where it belongs.

Edit with `Edit` or a small Python replace script that **asserts each `old` string was found**, so a
silent no-op cannot pass as success. Never regenerate the whole file from memory just to change a
few sentences; that is how the quirks get lost.

## Screenshots

Full playbook, including every environment trap, is in `references/capture-playbook.md`. **Read it
before launching a browser** — it will save you the ~40 minutes of hangs and mis-clicks this
workflow costs when rediscovered from scratch.

The short version:

- Reuse a Playwright install from another local project; browsers are usually already cached.
  `scripts/shots.js` is a ready-made helper (login, sized context, capture).
- Set `DEBUGBAR_ENABLED=false` **and** `RESPONSE_CACHE_ENABLED=false` before anything else.
- Seed through the real UI and repositories, not raw SQL, so the data is genuinely representative.
- Capture PNG at 1120x880, then `scripts/to_webp.sh` to convert.
- **Restore every `.env` value you changed** when you finish.

Naming, which the validator enforces:

- Filename (without extension) and `alt` must be **byte-identical**.
- Put the keyphrase in roughly a third of the alts, not all of them.
- `src` points at `screenshots/<name>.webp`, relative to the blog, so the deliverable is
  self-verifying. Tell the user to swap in CDN URLs at upload time.

**Never fabricate a screenshot.** If a screen cannot be captured, leave no placeholder for it, and
say in your report which screens were skipped and why.

## SEO and readability pass

Thresholds and the exact Yoast checks are in `references/seo-checklist.md`. Enforce with:

```bash
python3 scripts/validate_blog.py <blog.html> --keyphrase "<exact keyphrase>"
```

It reports block balance, tag balance, alt/filename match, missing and orphaned images, keyphrase
density, keyphrase in the first paragraph, keyphrase-carrying subheadings, internal link count, and
the Yoast **readability** checks — sentence length, subheading distribution, passive voice,
paragraph length. Run it after every editing pass, not just at the end.

Yoast has two tabs and a green SEO tab says nothing about readability. Cover both, or the user
comes back with the second half.

**If the user pastes a Yoast report where nearly every line is red, check the keyphrase field before
touching the file.** On an updated post it usually still holds the phrase the article targeted
*before* your rewrite, so a perfectly good file scores zero. The checklist has the two-command
diagnosis.

Four things live in WordPress, not in the HTML, and the job is not finished until you have handed
them over as literal strings with character counts: **focus keyphrase, SEO title, meta description,
slug**.

**Internal links must be verified, never invented.** Yoast counts only same-host links, so a
`store.webkul.com` link does not satisfy a `webkul.com/blog` post. Find real ones:

```
WebSearch(query: "webkul.com/blog <topic>", allowed_domains: ["webkul.com"])
```

then `WebFetch` each candidate to confirm it is a live article before linking it. Three is plenty.
Fetching them often pays a bonus — a sibling guide will state the module version you were unsure of.

## Report honestly

Finish with a table of **what was wrong and what the code actually says**, one row per correction.
That table is the deliverable the reviewer actually reads.

Also surface, separately:

- **Bugs you found in the module.** Auditing a package against its docs is an effective bug
  detector, and a broken feature changes what the blog may claim. Report it; do not silently fix it
  (you were asked to edit a blog) and do not silently document behaviour that cannot happen.
- **Assumptions** you could not verify in code, such as a sibling package's version number.
- **Screens you could not capture**, and what would unblock them.

## Never

- Document a feature the code does not implement, however plausible.
- Modify package or application source. You are editing a blog and its assets.
- Leave `.env` modified.
- Invent a URL, a version number, or a field label.
