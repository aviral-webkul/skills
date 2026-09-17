---
name: bagisto-release-blog
description: Write the WordPress release-note blog for a Bagisto version, and produce every image it needs. Asks which version to build, reads that version's CHANGELOG section as the only source of content, verifies each claim against the package code, reuses the previous release note's structure, repaints the release banner to the new version number, captures the screenshots with Playwright from a running install, converts them to lossless WebP, and runs a Yoast pass (keyphrase density, link anchors, alt text, passive voice, sentence length). Use when asked to create, update or illustrate a Bagisto release note or version announcement blog, or to refresh its banner and screenshots.
---

Bagisto Release Blog

Purpose
- Turn one CHANGELOG version section into a finished WordPress release note.
- Produce the blog HTML plus the banner and every screenshot it references.
- Keep every sentence traceable to that version's changelog.

Step 1 - ask the user, before anything else
- Which Bagisto version to build, for example v2.4.11. Use AskUserQuestion.
- Offer the versions found in CHANGELOG.md as the options.
- Then confirm, in one question each where the answer is not obvious:
  - The blog file to write, and the previous release note to copy structure from.
  - The running install URL and the admin login for screenshots.
  - The WordPress uploads month folder, for example 2026/09.
- Do not start writing until the version is known.

Step 2 - read the changelog, and treat it as the only source
- Extract exactly one version's entries:
  awk '/^## \*\*v<NEW>/,/^## \*\*v<PREVIOUS>/' CHANGELOG.md
- Read every entry before writing a single line.
- Cover all of them. Count the entries, then count your bullets.
- Never carry a feature or fix from the previous version into this post.
- Never invent anything the changelog does not say.
- Entries tagged [feature] are features. Everything else is a fix or improvement.
- Keep every issue number, such as #11441, and put it in <strong> tags.

Step 3 - verify the claims against the code
- The changelog is terse; confirm what each entry means before describing it.
- Check the tag is present: git describe --tags.
- Grep the packages for the setting, column, config key or controller named.
- Confirm a feature exists before writing that it ships.
- If the code and the changelog disagree, follow the code and say so.

Step 4 - write the post
- Copy the previous release note's structure exactly. Change only the content.
- Keep: the intro <p> with its inline style, four summary bullets, the banner,
  the "Overall ..." line, then h3 New Features / Improvements / Bug Fixes /
  Conclusion, h4 subsections, &nbsp; spacers, the closing boilerplate.
- Indent every <li> with one space and one tab, as the previous file does.
- Group fixes into h4 sections by area, for example Appearance, Images,
  Settings, Caching, Checkout, Catalogue.
- End the fixes with the security-fixes line if the changelog has one.

Step 5 - write in plain words
- No code identifiers. Not swatch_value_url, not image_urls(), not config keys.
- No framework or library names. Not Laravel, TinyMCE, Vee Validate, Socialite.
- No internal class, method, helper or driver names.
- Say what the shopper or the store owner sees, not how the code does it.
- Keep admin labels a user can read on screen, such as RMA, GDPR, Full Page
  Cache, Use Layered Navigation. Those are signposts, not jargon.
- Replace "cached" with "saved copy", "index" with "search", and so on.

Step 6 - keep every block short
- WordPress renders each bare line and each <li> as its own block.
- Every block must come in under 160 characters, about two lines on screen.
- An editorial pass flags anything longer, so write short from the start.
- When a bullet runs long, split it into more bullets. Do not cut the content.
- Keep the issue number on the lead bullet and let the rest follow beneath it,
  which is how the Features and Improvements sections already read:
    <li><strong>#11440</strong> Fixed the payment button overlapping the logo.</li>
    <li>The card now leaves room for the button, so its wording stays clear.</li>
- Split a long paragraph on a blank line. That is a paragraph break in WordPress.
- scripts/check.py measures this; it counts 160 itself as too long.

Step 7 - the banner
- Reuse the previous release banner and change only its version text.
- Download it, note its exact size, and keep that size.
- scripts/banner.py does the repaint. Run it with --inspect first to print the
  glyph positions, set them, then run it for real.
- It rebuilds the pill background per row from clean pixels either side of the
  text, so the gradient stays seamless.
- It drops image coverage more than two pixels from solid ink, which removes
  the source WebP's ringing halo. Skip that and the new text sits in a
  visible mottled box.
- Re-centre the string when the new number is narrower or wider.
- Save as WebP at the original dimensions. Compare old and new side by side.

Step 8 - screenshots
- Start the app with workers. A single-worker server deadlocks under Playwright:
  PHP_CLI_SERVER_WORKERS=8 php artisan serve
- Never pkill a pattern that matches your own command line; use artisan[ ]serve.
- The admin Sign In button has no type=submit. Click it by role and name.
- Hide the debug bar before any click, through context.addInitScript, not
  addStyleTag after the fact. Its restore button swallows clicks.
- Seed any demo data the feature needs first, so the shot actually shows it.
- Capture with an explicit clip at the exact target size. Do not resize after.
- Sizes that match the existing posts: banner 1774x887, wide admin grids
  1400x560, panels and drawers 1120x880.
- Collapse the admin sidebar when a grid is too wide to fit.
- Hide the sticky header if the clip would catch a sliver of it.
- Clip height must fit above the page bottom, or the image comes out short.
- Look at every screenshot before accepting it.

Step 9 - images for WordPress
- Convert to lossless WebP. For UI screenshots it beats PNG and lossy WebP
  on size and keeps text crisp:
  convert x.png -define webp:lossless=true -define webp:method=6 x.webp
- Prove it is unchanged: compare -metric AE x.png x.webp null:  must be 0.
- Name each file for what it shows, lowercase with hyphens.
- Reference them as https://bagisto.com/wp-content/uploads/<YYYY>/<MM>/<name>.webp
- Never invent wp-image-<id> classes. WordPress builds srcset from that id, so
  a wrong one serves an unrelated image. Omit the class; WordPress adds the
  right one when the image is inserted from the Media Library.
- After the user uploads, check every URL:
  curl -s -o /dev/null -w "%{http_code}" <url>
- A 404 means the file is not uploaded, whatever the local file is named.

Step 10 - the Yoast pass
- Run scripts/check.py <blog.html> <keyphrase>. Fix what it reports, then rerun.
- Keyphrase is the version itself, for example "Bagisto v2.4.11". It is unique
  per post, which clears the reused-keyphrase warning.
- Density: at least 8 occurrences, and 0.5 to 3 percent.
- The keyphrase must not be the anchor text of any link. Keep it in the
  sentence and link different words, such as "release notes on GitHub".
- Put the keyphrase in most image alt attributes, and describe the shot too.
- Passive voice under 10 percent. Name the actor: "Bagisto drops an empty one",
  not "an empty one is left out".
- Under 25 percent of sentences over 20 words. Split the long ones; that also
  raises the sentence count, which lowers both percentages at once.
- Splitting sentences can break other checks, so confirm afterwards that no
  three sentences in a row open with the same word.

Step 11 - items only the user can set in Yoast
- The focus keyphrase.
- The meta description. Draft one for them, about 150 characters, keyphrase first.
- The featured image alt text, which Yoast counts but the post body does not hold.

Finish
- Run scripts/check.py one last time and report its output.
- Confirm every changelog entry is represented, and no previous version remains.
- Confirm each image's declared width and height match the real file.
- Deliver the blog file, the images, and the meta description to paste.
