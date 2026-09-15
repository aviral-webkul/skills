# Yoast-style SEO checklist

Run `scripts/validate_blog.py` to measure all of this. The numbers below are the thresholds it
checks against.

## Get the exact keyphrase first

Ask for the literal string the user will paste into Yoast. Scoring differs completely between
"Marketplace Mercado Pago Payment" and "Laravel Marketplace Mercado Pago Payment Gateway", and every
target below is computed against exact-phrase matches.

If the user later changes it, re-run the whole pass — intro, subheadings, body mentions and alt text
all shift.

### The keyphrase field is part of the deliverable

When you retarget an existing post, the phrase stored in Yoast does **not** change because you
edited the HTML. The post keeps scoring against the old one, and every check reads red at once:
keyphrase found 0 times, missing from the introduction, missing from subheadings, missing from the
slug, missing from the SEO title.

That pattern — *everything* red rather than a few items — is the signature. Do not start rewriting.
Measure the file against both phrases first:

```bash
python3 scripts/validate_blog.py <blog.html> --keyphrase "<new phrase>"
python3 scripts/validate_blog.py <blog.html> --keyphrase "<phrase in the Yoast field>"
```

If the new phrase scores green and the old one scores zero, the file is correct and the fix is one
field in WordPress. Say so, and hand over the four values under "Things only the user can set"
below. Only rewrite the body if the user decides to keep the old keyphrase.

## Targets

| Check | Target | How to satisfy |
|---|---|---|
| Keyphrase in introduction | present in the **first paragraph** | Lead with it: "The <keyphrase> lets your customers…" |
| Keyphrase density | 0.5%–3% (min 2 occurrences) | 6–8 exact occurrences per ~1000 words |
| — how it is computed | `occurrences / total words` | **Not** `(occurrences x phrase words) / total`. That second formula triples a 3-word phrase and reports 1.1% where Yoast sees 0.36% — green where the post is actually red. Let the validator do the arithmetic. |
| Keyphrase in subheadings | **30%–75%** of H2/H3 | 3 of 9 headings = 33% ✓. Two is often not enough |
| Keyphrase in alt text | a **subset** | ~1/3 of images. All of them reads as stuffing |
| Internal links | at least one, same host | See below |
| Passive voice | under 10% | Prefer "The module sends…" over "…is sent by" |
| Paragraph length | under ~160 words | Bagisto blogs are short-sentence by house style |
| Keyphrase length | ≤ 4 content words | **Yoast-side only** — see below |

### Distribution matters

Yoast checks that occurrences are spread, not clustered. Place them roughly: intro, 2–3 subheadings,
one body mention per major section, one in the closing paragraph.

### Keyphrase length

A keyphrase over 4 content words triggers an *improvement*, not an error, and the post can still
score green. Nothing in the article body can fix it — only changing the keyphrase in Yoast can. Tell
the user, offer the shorter variant, and note whether the shorter phrase is already a substring of
the long one (if so, density and subheading scores carry over unchanged). Then follow whichever they
chose.

## Internal links — verify, never invent

Yoast counts a link as **internal only if the host matches**. For a post on `webkul.com/blog`:

- `webkul.com/blog/...` → internal ✓
- `store.webkul.com/...` → external ✗ (different host — this is why a blog full of store links still
  reports "No internal links appear")
- `bagisto.uvdesk.com`, vendor sites → external ✗

Find real ones, never guess a slug:

```
WebSearch(query: "webkul.com/blog <module topic>", allowed_domains: ["webkul.com"])
```

Then `WebFetch` each candidate and confirm it is a live article before linking it. Three good links
is plenty.

Pick links a reader would actually follow:

- the base module this add-on requires,
- the single-store variant of the same integration,
- a sibling module solving the same problem.

Fetching them frequently pays a bonus: a sibling guide often states a version number you could not
derive from code.

## Alt text rule

Yoast matches the keyphrase inside alt text **after splitting on hyphens**, so slug-style alt
(`marketplace-store-locator-configuration`) scores exactly like prose alt and needs no rewording.
Write alt in slug form and it satisfies Yoast, the filename rule below, and a later re-capture all
at once.

### When the images are already on the CDN

If the user chose to reuse the uploaded images rather than re-capture them, `src` is an absolute
`cdnblog.webkul.com` URL and the filenames are WordPress's (`01-configuration-2-1200x943`). Neither
`alt == filename` nor `file exists` can hold, and forcing alt to match those stems would make the
alt text worse. The validator detects remote `src` and reports them INFO instead of FAIL. Do not
churn the file to silence it; note the mode in your report.

### When you captured the screenshots yourself

Alt text must stay **byte-identical to the filename** (without extension). So changing which alts
carry the keyphrase means renaming the image files and updating both `src` and `alt` together:

```python
new = "laravel-" + old.replace("marketplace-mercado-pago-payment",
                               "marketplace-mercado-pago-payment-gateway")
assert s.count(old) == 2          # src + alt, both must move
s = s.replace(old, new)
```

Re-run the validator afterwards to confirm nothing is missing or orphaned.

## Readability tab

Yoast scores readability separately from SEO, and a green SEO tab says nothing about it. Check it in
the same pass — the validator reports all of these under `== Readability ==`.

| Check | Target | How to satisfy |
|---|---|---|
| Sentence length | **under 25%** of sentences over 20 words | Split sentences doing two jobs at once |
| Subheading distribution | no section over **300 words** | Add a subheading inside the long run |
| Passive voice | under 10% | "Checkout offers each branch", not "each branch is offered" |
| Paragraph length | under ~160 words | Rarely a problem in this house style |
| Consecutive sentences | no 3 in a row starting with the same word | Vary the opener |
| Word complexity | Premium-only | Cannot be measured locally. Say so; the interface labels you must quote verbatim are usually the only long words left |

Two notes that decide how you count:

- Yoast splits sentences on `.!?` only. A semicolon does **not** end a sentence, so a
  semicolon-joined sentence still counts as one long one — and rewriting it into two sentences is
  a real fix, not a cosmetic one.
- Yoast counts every `<li>` as prose. A post with a 25-item feature list is much longer, in Yoast's
  eyes, than its paragraph count suggests.

### Splitting a long sentence pays twice

It removes one sentence from the over-20-word numerator *and* adds one to the denominator, so the
percentage falls faster than you expect. Shortening ~10 sentences moved a real post from 29.2% to
15.5%.

### Splitting a long section

Prefer a genuine split point over an inserted label — a 25-item feature list divides cleanly into
admin-side and shopper-side halves. Adding a heading changes the subheading-keyphrase ratio, so
re-run the validator afterwards: going from 4/11 to 4/12 is still inside the 30–75% band, but
4/13 would not be.

## Things only the user can set

State these in your report rather than trying to fix them in the file, and give the literal strings
with their character counts so they can be pasted straight in:

| Field | Target | Note |
|---|---|---|
| Focus keyphrase | ≤ 4 content words | Must be changed in Yoast; editing the HTML does nothing |
| SEO title | ≤ 60 chars, keyphrase **at the start** | Yoast wants an exact match of the whole phrase |
| Meta description | 120–156 chars | Over 156 truncates in the SERP |
| Slug | contains the keyphrase | Check before proposing a change — an existing slug like `bagisto-marketplace-store-locator` may already contain it, and changing a live slug costs redirects |

Also warn about a keyphrase already used on another post, which triggers Yoast's reuse warning.
