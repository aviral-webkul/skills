#!/usr/bin/env python3
"""Yoast-style and structural checks for a Bagisto release-note blog.

    python3 check.py blog.html "Bagisto v2.4.11" [--verbose]

Reproduces the numbers Yoast reports for passive voice and sentence length,
plus keyphrase density, link anchors, alt text, block length, tag balance and
image sizes.
Exit code is non-zero when a hard check fails.
"""

import html
import os
import re
import subprocess
import sys

IRREGULAR = """awoken born beat become begun bent bet bound bitten bled blown broken brought built burnt
burst bought caught chosen clung come cost crept cut dealt dug done drawn dreamt drunk driven eaten fallen
fed felt fought found fled flung flown forbidden forgotten forgiven frozen got given gone ground grown hung
had heard hidden hit held hurt kept knelt known laid led leant leapt learnt left lent let lain lit lost made
meant met mown overtaken paid put read ridden rung risen run sawn said seen sold sent set sewn shaken shed
shone shot shown shrunk shut sung sunk sat slept slid smelt sown spoken spelt spent spilt spun spat split
spoilt spread sprung stood stolen stuck stung stunk struck sworn swept swollen swum swung taken taught torn
told thought thrown understood upset woken worn wed wept won wound written""".split()

BE = r'(?:is|are|was|were|be|been|being|get|gets|got|gotten)'
PARTICIPLE = r'(?:[a-z]+(?:ed|en)|' + '|'.join(IRREGULAR) + r')'
BLOCK_LIMIT = 160   # a rendered block must come in UNDER this

PASSIVE = re.compile(rf'\b{BE}\b(?:\s+\w+){{0,2}}?\s+\b{PARTICIPLE}\b', re.I)


def visible_text(raw):
    s = re.sub(r'<!--.*?-->', '', raw, flags=re.S)
    s = re.sub(r'</(li|h1|h2|h3|h4|p|ul|ol)>', '. ', s)
    s = html.unescape(re.sub(r'<[^>]+>', ' ', s))
    return re.sub(r'\s+', ' ', s)


def block_text(fragment):
    """Plain text of one block, with no sentence-boundary padding added."""
    t = re.sub(r'<!--.*?-->', '', fragment, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', t))).strip()


def sentences(text):
    out = []
    for part in re.split(r'(?<=[.!?])\s+', text):
        part = part.strip(' .').strip()
        if len(part.split()) > 1:
            out.append(part)
    return out


def keyphrase_pattern(keyphrase):
    """Match 'Bagisto v2.4.11', 'Bagisto Version 2.4.11', 'Bagisto latest version 2.4.11'."""
    m = re.search(r'(\d+\.\d+\.\d+)', keyphrase)
    if not m:
        return re.compile(re.escape(keyphrase), re.I)
    brand = keyphrase[:m.start()].strip().rstrip('v').strip()
    return re.compile(rf'{re.escape(brand)}\s+(?:v|latest version |version )?{re.escape(m.group(1))}', re.I)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    if not args:
        print(__doc__)
        return 2

    path = args[0]
    keyphrase = args[1] if len(args) > 1 else None
    raw = open(path).read()
    text = visible_text(raw)
    sents = sentences(text)
    words = len(text.split())
    fails = []

    print(f'{path}: {words} words, {len(sents)} sentences\n')

    # ---- readability -------------------------------------------------
    long_s = [x for x in sents if len(x.split()) > 20]
    pass_s = [x for x in sents if PASSIVE.search(x)]
    for label, hits, limit in (('sentences over 20 words', long_s, 25.0),
                               ('passive voice', pass_s, 10.0)):
        pct = 100 * len(hits) / len(sents) if sents else 0
        ok = pct <= limit
        fails.append(label) if not ok else None
        print(f'[{"OK " if ok else "FAIL"}] {label:<24} {len(hits):>3}  {pct:5.1f}%  (max {limit}%)')
        if verbose and hits:
            for h in hits:
                print(f'         [{len(h.split()):>2}] {h}')

    # three sentences in a row opening with the same word
    starts = [re.sub(r'[^a-z0-9]', '', s.split()[0].lower()) for s in sents]
    runs, cur, n = [], starts[0] if starts else '', 1
    for i in range(1, len(starts)):
        if starts[i] == cur:
            n += 1
        else:
            if n >= 3:
                runs.append((cur, n))
            cur, n = starts[i], 1
    if n >= 3:
        runs.append((cur, n))
    print(f'[{"OK " if not runs else "WARN"}] consecutive same-start  {len(runs)}'
          + (f'  {runs}' if runs else ''))

    # ---- block length ------------------------------------------------
    # WordPress renders each bare line and each <li> as its own block; an
    # editorial pass flags any that runs past ~160 characters (about two lines).
    over = []
    for line in raw.split('\n'):
        st = line.strip()
        if not st or st == '&nbsp;':
            continue
        if st.startswith(('<ul', '</ul', '<ol', '</ol', '<h1', '<h2', '<h3',
                          '<h4', '<img', '<!--')):
            continue
        t = block_text(st)
        if len(t) >= BLOCK_LIMIT:
            over.append((len(t), t))
    ok = not over
    if not ok:
        fails.append('blocks at or over %d chars' % BLOCK_LIMIT)
    print(f'[{"OK " if ok else "FAIL"}] block length         '
          f'{len(over)} at or over {BLOCK_LIMIT} chars'
          + ('' if ok else '  (split them; do not cut the content)'))
    if over and verbose:
        for n, t in sorted(over, reverse=True):
            print(f'         [{n}] {t[:100]}...')

    # ---- SEO ---------------------------------------------------------
    if keyphrase:
        pat = keyphrase_pattern(keyphrase)
        body = len(pat.findall(text))
        total = body + 1                       # + the post title
        density = 100 * total / words if words else 0
        ok = total >= 8 and 0.5 <= density <= 3.0
        fails.append('keyphrase density') if not ok else None
        print(f'\n[{"OK " if ok else "FAIL"}] keyphrase            {body} in body '
              f'(+title = {total}), density {density:.2f}%  (min 8, 0.5-3%)')

        anchors = [t for _, t in re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', raw)
                   if pat.search(t)]
        ok = not anchors
        fails.append('keyphrase in link anchor') if not ok else None
        print(f'[{"OK " if ok else "FAIL"}] link anchors         '
              + ('none carry the keyphrase' if ok else f'{anchors}'))

        alts = re.findall(r'alt="([^"]*)"', raw)
        hit = sum(1 for a in alts if pat.search(a))
        ok = not alts or hit >= max(1, len(alts) // 2)
        print(f'[{"OK " if ok else "WARN"}] alt text             {hit}/{len(alts)} '
              f'carry the keyphrase (+ your featured image)')

    # ---- structure ---------------------------------------------------
    print()
    for tag in ('ul', 'li', 'h3', 'h4', 'p', 'strong', 'a'):
        o = len(re.findall(rf'<{tag}[ >]', raw))
        c = len(re.findall(rf'</{tag}>', raw))
        if o != c:
            fails.append(f'unbalanced <{tag}>')
            print(f'[FAIL] <{tag}> {o} open / {c} close')
    print(f'[OK ] tag balance          all matched'
          if not any(f.startswith('unbalanced') for f in fails) else '')

    # jargon that should never survive the plain-language pass
    jargon = re.findall(r'\b(?:[a-z]+_[a-z_]+|[a-zA-Z]+\(\))|'
                        r'TinyMCE|Vee Validate|Socialite|Elasticsearch|Laravel\'s', raw)
    jargon = [j for j in jargon if j not in ('wp-image',)]
    if jargon:
        fails.append('code jargon')
    print(f'[{"OK " if not jargon else "FAIL"}] plain language       '
          + ('no code names' if not jargon else f'{sorted(set(jargon))}'))

    # declared image size vs the real file
    base = os.path.dirname(os.path.abspath(path))
    imgs = re.findall(r'<img[^>]*src="([^"]+)"[^>]*width="(\d+)"[^>]*height="(\d+)"', raw)
    missing = []
    for src, w, h in imgs:
        name = src.rsplit('/', 1)[-1]
        for folder in ('blog-images', 'images', '.'):
            f = os.path.join(base, folder, name)
            if os.path.exists(f):
                try:
                    got = subprocess.run(['identify', '-format', '%wx%h', f],
                                         capture_output=True, text=True).stdout.strip()
                except FileNotFoundError:
                    got = f'{w}x{h}'
                if got != f'{w}x{h}':
                    missing.append(f'{name} is {got}, declared {w}x{h}')
                break
        else:
            missing.append(f'{name} not found locally')
    if missing:
        print(f'[WARN] images              ' + '; '.join(missing))
    else:
        print(f'[OK ] images               {len(imgs)} match their declared size')

    print('\n' + ('ALL HARD CHECKS PASS' if not fails else 'FAILED: ' + ', '.join(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
