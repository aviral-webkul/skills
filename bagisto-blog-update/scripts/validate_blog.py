#!/usr/bin/env python3
"""
Validate a Bagisto blog HTML file: structure, images, Yoast SEO and Yoast readability.

    python3 validate_blog.py <blog.html> [--keyphrase "exact phrase"] [--host webkul.com/blog]

Exits non-zero if any hard check fails (structure / local images). SEO and readability
targets are reported as WARN so an in-progress editing pass is not blocked.

Images referenced by an absolute URL (an already-uploaded CDN post) are checked as
remote: `alt == filename` and `file exists` cannot apply, so they are reported INFO.
That is the normal state when a blog is updated in reuse-the-CDN-images mode.
"""
import argparse
import os
import re
import sys
from collections import Counter
from itertools import groupby

VOID = {"img", "br", "hr", "meta", "input", "link", "source"}
FAIL = []
WARN = []

# Rough "be + past participle" detector. Yoast's own list is larger; this is close
# enough to keep a post under the 10% threshold without chasing every irregular verb.
PASSIVE = re.compile(
    r"\b(is|are|was|were|be|been|being)\s+(\w+ly\s+)?"
    r"(\w+ed|built|shown|sent|kept|set|made|given|taken|written|held|known|seen|done|"
    r"found|put|stamped|frozen|returned|offered|listed|charged|recorded|registered|"
    r"retained|translated|divided|configured|calculated|resolved|assigned|removed|"
    r"required|carried|labelled|published|switched|needed|split|drawn|paid|met|lost)\b",
    re.I)


def hard(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        FAIL.append(msg)


def soft(ok, msg):
    print(("  OK   " if ok else "  WARN ") + msg)
    if not ok:
        WARN.append(msg)


def prose_words(src):
    """Visible prose, excluding block comments and code blocks."""
    t = re.sub(r"<!--.*?-->", " ", src, flags=re.S)
    t = re.sub(r"<pre.*?</pre>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;|&gt;|&lt;|&amp;|&#\d+;", " ", t)
    return re.findall(r"[A-Za-z0-9'’-]+", t)


def prose_units(src):
    """Paragraph and list-item texts, with comments and code blocks removed.

    Yoast scores each <p> and each <li> as prose, so both must be counted here or
    a feature-list-heavy post reads as far shorter than Yoast sees it.
    """
    t = re.sub(r"<!--.*?-->", " ", src, flags=re.S)
    t = re.sub(r"<pre.*?</pre>", " ", t, flags=re.S)
    units = re.findall(r"<p>(.*?)</p>", t, re.S) + re.findall(r"<li>(.*?)</li>", t, re.S)
    units = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", u)).strip() for u in units]
    return [u for u in units if u]


def sentences(units):
    """Split on . ! ? only — Yoast does not treat a semicolon as a sentence end."""
    return [x.strip() for u in units
            for x in re.split(r"(?<=[.!?])\s+", u) if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blog")
    ap.add_argument("--keyphrase", default=None)
    ap.add_argument("--host", default="webkul.com/blog",
                    help="substring identifying same-host internal links")
    a = ap.parse_args()

    src = open(a.blog, encoding="utf-8").read()
    base = os.path.dirname(os.path.abspath(a.blog)) or "."

    # ---------- structure ----------
    print("\n== Structure ==")
    o = Counter(re.findall(r"<!--\s*wp:([a-z-]+)", src))
    c = Counter(re.findall(r"<!--\s*/wp:([a-z-]+)", src))
    hard(o == c, f"Gutenberg blocks balanced {dict(o)}"
         + ("" if o == c else f" vs closes {dict(c)}"))

    stack, errs = [], []
    for close, name, _attrs, selfc in re.findall(r"<(/?)([a-zA-Z0-9]+)([^>]*?)(/?)>", src):
        name = name.lower()
        if name in VOID or selfc == "/":
            continue
        if close:
            if not stack or stack[-1] != name:
                errs.append(f"unexpected </{name}>")
            else:
                stack.pop()
        else:
            stack.append(name)
    if stack:
        errs.append("unclosed: " + ", ".join(stack))
    hard(not errs, "HTML tags balanced" + ("" if not errs else " -> " + "; ".join(errs)))

    heads = [re.sub(r"<[^>]+>", "", t).strip()
             for _l, t in re.findall(r"<h(\d)[^>]*>(.*?)</h\1>", src, re.S)]
    print(f"  INFO  {len(heads)} headings")

    # ---------- images ----------
    print("\n== Images ==")
    imgs = re.findall(r'<img\s+src="([^"]+)"\s+alt="([^"]*)"', src)
    hard(bool(imgs), f"{len(imgs)} images with src+alt")

    local = [(u, alt) for u, alt in imgs if "://" not in u]
    remote = [(u, alt) for u, alt in imgs if "://" in u]

    for u, alt in local:
        stem = os.path.splitext(os.path.basename(u))[0]
        hard(stem == alt, f"alt == filename: {alt}"
             + ("" if stem == alt else f"  (file stem is '{stem}')"))
        hard(os.path.isfile(os.path.join(base, u)), f"file exists: {u}")

    if remote:
        print(f"  INFO  {len(remote)} remote image(s) — CDN reuse mode; "
              "alt==filename and file-exists not checked")
        soft(all(alt.strip() for _u, alt in remote), "every remote image has non-empty alt")

    shots_dir = os.path.join(base, "screenshots")
    if os.path.isdir(shots_dir) and local:
        refd = {os.path.basename(u) for u, _ in local}
        have = {f for f in os.listdir(shots_dir) if not f.startswith(".")}
        hard(not (refd - have), f"no missing images ({sorted(refd - have)})")
        soft(not (have - refd), f"no unused images ({sorted(have - refd)})")

    # ---------- SEO ----------
    if a.keyphrase:
        print("\n== SEO ==")
        kp = a.keyphrase.lower().strip()
        words = prose_words(src)
        low = " ".join(words).lower()
        occ = low.count(kp)
        density = occ / len(words) * 100 if words else 0
        print(f"  INFO  {len(words)} prose words (code blocks excluded)")

        first = re.search(r"<p>(.*?)</p>", src, re.S)
        first_txt = re.sub(r"<[^>]+>", "", first.group(1)).lower() if first else ""
        soft(kp in first_txt, "keyphrase in first paragraph")

        soft(occ >= 2, f"keyphrase occurrences: {occ} (min 2)")
        # Density is occurrences / total words — NOT (occurrences x phrase words) / total.
        # The second formula inflates a 3-word keyphrase threefold and hides a red Yoast.
        soft(0.5 <= density <= 3.0,
             f"density {density:.2f}% = {occ}/{len(words)} words (target 0.5-3%)")

        if heads:
            hits = [h for h in heads if kp in h.lower()]
            pct = len(hits) / len(heads) * 100
            soft(30 <= pct <= 75,
                 f"keyphrase in subheadings: {len(hits)}/{len(heads)} = {pct:.0f}% (target 30-75%)")

        if imgs:
            slug = kp.replace(" ", "-")
            n = sum(1 for _s, alt in imgs if slug in alt.lower())
            soft(0 < n < len(imgs),
                 f"keyphrase in alt text: {n}/{len(imgs)} (want a subset, not all)")

        links = re.findall(r'href="([^"]+)"', src)
        internal = [l for l in links if a.host in l]
        soft(bool(internal), f"internal links ({a.host}): {len(internal)}")
        for l in internal:
            print(f"        internal: {l}")
        for l in links:
            if l not in internal:
                print(f"        external: {l}")

    # ---------- readability ----------
    print("\n== Readability ==")
    units = prose_units(src)
    sents = sentences(units)

    if sents:
        long_s = [x for x in sents if len(x.split()) > 20]
        pct = len(long_s) / len(sents) * 100
        soft(pct <= 25,
             f"sentences over 20 words: {len(long_s)}/{len(sents)} = {pct:.1f}% (max 25%)")

        pas = [x for x in sents if PASSIVE.search(x)]
        ppct = len(pas) / len(sents) * 100
        soft(ppct < 10,
             f"passive voice: {len(pas)}/{len(sents)} = {ppct:.1f}% (max 10%)")

        firsts = [(x.split() or [""])[0].lower().strip('"\u201c\u2018(') for x in sents]
        runs = []
        for w, g in groupby(firsts):
            n = len(list(g))
            if w and n >= 3:
                runs.append(f"{w} x{n}")
        soft(not runs, "no 3+ consecutive sentences starting with the same word"
             + ("" if not runs else f" -> {', '.join(runs)}"))

    if units:
        longest = max(len(u.split()) for u in units)
        soft(longest <= 160, f"longest paragraph {longest} words (max ~160)")

    # Yoast's subheading distribution: no run of body copy over 300 words without a heading.
    secs, cur = [], "(intro, before first subheading)"
    for part in re.split(r"(<h[1-6][^>]*>.*?</h[1-6]>)", src, flags=re.S):
        if re.match(r"<h[1-6]", part or ""):
            cur = re.sub(r"<[^>]+>", "", part).strip()
            continue
        n = len(prose_words(part or ""))
        if n:
            secs.append((cur, n))
    over = [f"{h} ({n} words)" for h, n in secs if n > 300]
    soft(not over, "no section over 300 words without a subheading"
         + ("" if not over else " -> " + "; ".join(over)))

    # ---------- verdict ----------
    print("\n== Result ==")
    if FAIL:
        print(f"  {len(FAIL)} FAILED:")
        for m in FAIL:
            print("    - " + m)
    if WARN:
        print(f"  {len(WARN)} warnings:")
        for m in WARN:
            print("    - " + m)
    if not FAIL and not WARN:
        print("  all checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
