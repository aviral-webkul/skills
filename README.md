# Bagisto authoring & skills

Three Claude Code skills for Bagisto work: two that write or correct module blogs, and one that
hunts storefront UI regressions between two installs.

They share one rule — **the package `src/` is the only source of truth.** A package's own
`CLAUDE.md`, `AGENTS.md` or `README.md` drifts exactly like the blog you were asked to fix, so the
skills treat those as hints about intent and never as evidence about behaviour.

This repo doubles as a **plugin marketplace** (`.claude-plugin/marketplace.json`), so the skills can
be installed with `claude plugin` commands instead of copied by hand.

---

## What a skill is

A folder containing a `SKILL.md` whose YAML frontmatter carries a `name` and a `description`. Claude
Code reads every description at session start and loads the full instructions only when a request
matches one — so a skill costs nothing until it is needed.

```
<skill-name>/
├── SKILL.md            # frontmatter + instructions (loaded when triggered)
├── references/*.md     # detail docs, read on demand
├── scripts/            # helper scripts the skill runs
└── templates/          # output scaffolds
```

---

## Install

### Option A — command line, via this marketplace (recommended)

Register the marketplace once, then install the skills you want. The `<source>` can be a local
path, a GitHub `owner/repo`, or a URL.

```bash
# from a local checkout
claude plugin marketplace add ~/.claude/skills

# or, once this repo is pushed
claude plugin marketplace add <owner>/<repo>
```

Then install:

```bash
claude plugin install bagisto-blog-update@bagisto-skills
claude plugin install bagisto-feature-blog@bagisto-skills
claude plugin install bagisto-storefront-ui-comparison@bagisto-skills
```

**To add them to a project** — so everyone working in that repo gets them — run both commands with
`--scope project` from the project root:

```bash
cd /path/to/your-project
claude plugin marketplace add <owner>/<repo> --scope project
claude plugin install bagisto-blog-update@bagisto-skills --scope project
```

That writes `<project>/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "bagisto-skills": { "source": { "source": "github", "repo": "<owner>/<repo>" } }
  },
  "enabledPlugins": { "bagisto-blog-update@bagisto-skills": true }
}
```

Commit that file and teammates get the skills on checkout — Claude Code fetches the marketplace for
them. `--scope` takes `user` (default, every project on this machine), `project` (committed, shared)
or `local` (this project, just you, not committed).

> **Use a GitHub source for anything shared.** A `directory` source records an **absolute path**, so
> a committed `.claude/settings.json` pointing at `/home/<you>/.claude/skills` resolves to nothing on
> a teammate's machine. Local paths are fine for your own `--scope user` install.

### Option B — copy the folder

No marketplace, no manifest, works immediately:

```bash
# just for you, every project
mkdir -p ~/.claude/skills && cp -r bagisto-blog-update ~/.claude/skills/

# or committed into one project, shared with the team
mkdir -p <project>/.claude/skills && cp -r bagisto-blog-update <project>/.claude/skills/
```

Either way, **start a new Claude Code session** — the skill list is built at startup. Then describe
the task and let the description match, or force one by typing its name as a slash command:
`/bagisto-blog-update`.

### Managing what you installed

```bash
claude plugin list                                        # what is installed, and at which scope
claude plugin details bagisto-blog-update@bagisto-skills  # components + token cost per session
claude plugin update bagisto-blog-update@bagisto-skills   # pull the latest (restart to apply)
claude plugin disable bagisto-blog-update@bagisto-skills --scope local
claude plugin uninstall bagisto-blog-update@bagisto-skills
claude plugin validate .                                  # check skills/agents/commands in a dir
```

`details` is worth running before you commit a project install — it prints the always-on token cost
added to every session in that repo (a few hundred tokens per skill; the full instructions load only
when the skill fires).

A plugin enabled at **project** scope cannot be uninstalled by one person — that setting is shared.
Use `claude plugin disable … --scope local` to turn it off just for yourself.

---

## Which one do I want?

| Situation | Skill |
|---|---|
| A blog exists but has drifted from the code, or needs an SEO/readability fix | `bagisto-blog-update` |
| You want a customer-facing announcement post, not a step-by-step user guide | `bagisto-feature-blog` |
| The storefront looks wrong after an upgrade or theme migration | `bagisto-storefront-ui-comparison` |

The two blog skills overlap, so the distinction matters: **fix an existing post** vs **write an
announcement**. Picking the wrong one gets you a rewrite where you wanted a correction.

---

## `bagisto-blog-update` — correct an existing post

Audits a blog against the current package code, fixes what drifted, adds shipped features the post
is missing, and refuses to document anything the code does not actually do. Preserves the existing
Gutenberg structure rather than redesigning it.

The most built-out skill here:

| File | Covers |
|---|---|
| `references/verification-map.md` | Which source file settles which class of blog claim, and the failure modes these posts hit repeatedly |
| `references/capture-playbook.md` | Screenshot capture end to end, including every environment trap — read it *before* launching a browser |
| `references/seo-checklist.md` | Yoast SEO **and** readability thresholds, plus the traps below |
| `scripts/validate_blog.py` | Measures all of it; run after every editing pass |
| `scripts/shots.js` | Playwright helper: login, sized context, capture |
| `scripts/to_webp.sh` | PNG → WebP at an exact size |

Two traps it encodes, both of which cost real time to rediscover:

- **A Yoast report where nearly everything is red usually means the keyphrase field still holds the
  phrase the post targeted *before* the rewrite.** The file can be perfect and still score zero.
  Diagnose by running the validator against both phrases before editing anything.
- **Keyphrase density is `occurrences / total words`** — not occurrences × phrase length. The second
  formula triples a 3-word phrase and reports green where Yoast reads red.

**Needs:** Python 3 (validator is stdlib-only). Screenshots additionally need a running install,
Playwright and ImageMagick — but the whole factual audit runs with neither.

### Running the validator on its own

Useful outside the skill, on any Gutenberg blog file:

```bash
python3 bagisto-blog-update/scripts/validate_blog.py \
    path/to/blog.html --keyphrase "Your Exact Keyphrase"
```

Reports structure (block and tag balance), images, SEO (density, intro, subheadings, alt text,
internal links) and readability (sentence length, subheading distribution, passive voice, paragraph
length, repeated sentence openers). Exits non-zero on structural or local-image failures; SEO and
readability are warnings so an in-progress pass is not blocked. Images on a CDN are detected and
reported INFO — `alt == filename` cannot apply to an already-uploaded post.

## `bagisto-feature-blog` — write an announcement

Turns a module's features into a customer-facing announcement post in plain, non-technical language
— grouped sections rather than a step-by-step guide. Grounds every claim in the module code,
captures its own screenshots, and applies the same Yoast-style SEO pass.

**Needs:** a running Bagisto install, Playwright, ImageMagick with a WebP delegate.

## `bagisto-storefront-ui-comparison` — find visual regressions

Compares the **storefront only** of two installs — a stable baseline and a candidate — and writes a
`bag-report.md` of confirmed regressions. Asks which is which; never assumes a version.

Drives both sites with Playwright, pixel-diffs and builds side-by-sides at desktop and mobile, then
cross-checks each finding against the Blade/Tailwind diff and the compiled theme CSS. That last step
is the point: config, seed-data and environment differences get excluded rather than reported, so
the output is signal instead of a wall of diffs.

Start from `scripts/config.example.json`.

**Needs:** both installs reachable, Playwright, Python 3 with Pillow (`pip install Pillow`).

---

## Requirements at a glance

| Dependency | Used by | Check |
|---|---|---|
| Python 3 | all three | `python3 --version` |
| Pillow | `bagisto-storefront-ui-comparison` | `python3 -c "import PIL; print(PIL.__version__)"` |
| Playwright | all screenshot/compare work | `node -e "require('playwright')"` |
| ImageMagick + WebP | the two blog skills | `convert -list format \| grep -i webp` |

Playwright browsers are usually already cached from another local project; the skills reuse an
existing install rather than downloading their own.

---

## House conventions

- Screenshots are **1120×880 WebP**, and for locally captured shots the filename (without extension)
  is byte-identical to the `alt` text, so the deliverable verifies itself.
- Internal links are **verified, never invented** — Yoast counts a link as internal only if the host
  matches, so a `store.webkul.com` link does nothing for a post on `webkul.com/blog`.
- Never fabricate a screenshot. If a screen cannot be captured, leave no placeholder and say in the
  report which screens were skipped and why.
- The skills edit blogs and their assets. They do **not** modify package or application source, and
  they restore any `.env` value they changed.

---

## Adding a skill to this marketplace

Drop the folder in beside the others, then add an entry to `.claude-plugin/marketplace.json`:

```json
{ "name": "<skill-name>", "source": "./<skill-name>", "description": "One line." }
```

Check it before pushing:

```bash
claude plugin validate .
```
