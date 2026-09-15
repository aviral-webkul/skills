---
name: bagisto-feature-blog
description: Write and illustrate a product-feature announcement blog for a Bagisto module or extension, in WordPress Gutenberg HTML, and capture the screenshots it needs. Reads the module code to ground every claim, restructures the post into grouped announcement-style sections in plain non-technical language, sets up demo data in a live install, captures every placeholder image with Playwright at a fixed size, converts to WebP, and applies Yoast-style SEO (keyphrase distribution, subheadings, alt text, internal links, active voice). Use when asked to create, restructure, illustrate, or SEO-optimize a Bagisto feature/announcement blog post, or to capture the blog's screenshots from a running install.
---

Bagisto Feature Blog

Purpose
- Turn a Bagisto module's features into a polished announcement blog.
- Produce the blog HTML plus all screenshots it references.
- Keep every claim traceable to the module code.

Before starting, ask the user
- Where the blog file is, or whether to create one.
- The focus keyphrase for SEO.
- Which running install and URL to capture screenshots from.
- The super-admin and tenant logins, or permission to set them.
- The target screenshot size (past work used 1120x880).

Ground every claim in code
- Read the module under packages/Webkul/<Module>/src.
- Use dated migrations to decide what is new in the release.
- Read Config menu.php, system.php and Routes to map screens.
- Read Models, Repositories, Jobs, Listeners for behavior.
- Keep a notes file mapping each blog claim to a code line.
- Never invent a feature that the code does not support.

Blog structure and tone
- Write in WordPress Gutenberg block comments, matching the existing file.
- Open with a short intro of 2 to 3 paragraphs.
- Follow with a grouped feature list, one group per platform area.
- Give each area its own section, biggest news first.
- Add smooth one-line transitions between sections.
- Close with a short conclusion and a support block.

Writing rules
- Keep each paragraph under 160 words.
- Write for a non-technical reader.
- Avoid code blocks, event names, headers, hashing and payload jargon.
- Avoid step-by-step guides unless the user asks for them.
- Do not repeat the same connective words back to back.
- Write image alt text in plain language.
- Keep the HTML clean and consistent with the file.
- Preserve every real feature already in the file.

Screenshots
- Confirm the site is reachable and the DB has demo data.
- If data is missing, set it up before capturing.
- Register a tenant through the real sign-up flow when possible.
- Create supporting data through the admin UI, not raw SQL, where practical.
- Fire real events so logs and lists look populated.
- Drive capture with Playwright using a browser already in the cache.
- Reuse a Playwright module from another local project if none is installed.
- Set the viewport to the target size and deviceScaleFactor 1.
- Log in, then capture each URL as PNG.
- Scroll to a section by its smallest matching visible element, not a parent.
- Dismiss any modal or age-gate before capturing a storefront.
- Convert PNG to WebP at the exact target size.
- Save images to the folder the blog expects.
- Name each image file to match its placeholder name in the blog.
- Review each screenshot before finalizing.

Common environment fixes
- Remove any trailing slash from APP_URL; it breaks tenant resolution.
- Fix public/storage if it points at the wrong project; run storage:link.
- These two often cause broken tenant pages and missing theme images.

SEO pass (Yoast style)
- Put the focus keyphrase in the first paragraph.
- Distribute the keyphrase evenly across the whole text.
- Add the keyphrase to several H2 and H3 subheadings.
- Add the keyphrase to a subset of image alt tags, not all.
- Add internal links to other posts on the same domain.
- Keep passive voice under 10 percent; prefer active voice.
- Keep paragraphs short and trim over-long sentences.
- Do not change image src paths the user has already set.

Items the user must set in Yoast, not in the file
- The focus keyphrase, at the start of the SEO title.
- A unique keyphrase per post to avoid the reuse warning.

Finish
- Deliver the updated blog file.
- Deliver the screenshots and confirm names match placeholders.
- Write a short plain work report if the user asks.
