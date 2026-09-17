#!/usr/bin/env python3
"""Repaint the version text on a Bagisto release banner.

Reuses the previous release's banner and changes only the number in the pill,
keeping the artwork and the exact pixel size.

    # 1. find the text: prints the glyph columns and the rows they occupy
    python3 banner.py --src banner2410.png --inspect

    # 2. repaint, using the runs printed above
    python3 banner.py --src banner2410.png --out banner2411.png \
        --text-rows 560,716 --pill-rows 556,720 \
        --keep 344,861 --repeat 794,861 --gap 23 --shift 27

--keep    the span of glyphs carried over unchanged, e.g. "v2.4.1"
--repeat  the span of one glyph to stamp again, e.g. the "1" in "2.4.1"
--gap     ink gap between the repeated glyph and the one before it
--shift   move the whole string right, to re-centre a narrower number

Two details matter, and skipping either is visible in the result:

  * The pill holds a diagonal gradient. The background under the old text is
    rebuilt per row by interpolating between clean pixels on both sides, so it
    stays seamless instead of showing a flat patch.
  * A WebP source rings around high-contrast glyph edges. Coverage further than
    two pixels from solid ink is dropped, or the new text sits in a mottled box.

Needs Pillow. Convert to and from WebP with ImageMagick around this script.
"""

import argparse
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit('needs Pillow: pip install --user Pillow')


def pair(s):
    a, b = s.split(',')
    return int(a), int(b)


def find_pill(px, size):
    """Locate the coloured pill the version text sits in.

    The scan has to stay inside it: the artwork around the pill is near-white,
    and white background reads exactly like white glyph ink.
    """
    w, h = size
    y0, y1 = int(h * 0.45), int(h * 0.92)
    best = None
    for y in range(y0, y1, 4):
        runs, start = [], None
        for x in range(int(w * 0.08), int(w * 0.75)):
            r, g, b = px[x, y]
            solid = b > 140 and (b - r) > 70
            if solid and start is None:
                start = x
            elif not solid and start is not None:
                runs.append((start, x - 1))
                start = None
        if start is not None:
            runs.append((start, int(w * 0.75)))
        for a, b_ in runs:
            if best is None or (b_ - a) > (best[1] - best[0]):
                best = (a, b_)
    return best


def inspect(px, size, args):
    """Print the rows the text occupies and each glyph's column span."""
    w, h = size
    if args.scan_cols:
        x0, x1 = args.scan_cols
    else:
        pill = find_pill(px, size)
        if not pill:
            sys.exit('could not find the pill; pass --scan-cols and --scan-rows')
        x0, x1 = pill[0] + 25, pill[1] - 25
    y0, y1 = args.scan_rows or (int(h * 0.60), int(h * 0.82))

    rmin, rmax, cols = 10 ** 9, -1, []
    for x in range(x0, x1):
        hit = False
        for y in range(y0, y1):
            r, g, b = px[x, y]
            if r > 235 and g > 235 and b > 235:
                hit = True
                rmin, rmax = min(rmin, y), max(rmax, y)
        cols.append(hit)

    runs, start = [], None
    for i, on in enumerate(cols):
        x = x0 + i
        if on and start is None:
            start = x
        if not on and start is not None:
            runs.append((start, x - 1))
            start = None
    if start is not None:
        runs.append((start, x1 - 1))

    print(f'image          : {w}x{h}')
    print(f'searched       : cols {x0}-{x1}, rows {y0}-{y1}')
    if rmax < 0 or not runs:
        sys.exit('no glyphs found; widen --scan-rows / --scan-cols')
    print(f'text rows      : {rmin}-{rmax}')
    print(f'glyph runs     : {runs}')
    gaps = [runs[i + 1][0] - runs[i][1] for i in range(len(runs) - 1)]
    print(f'glyph widths   : {[b - a + 1 for a, b in runs]}')
    print(f'ink gaps       : {gaps}')
    print()
    print(f'suggested flags:')
    print(f'  --text-rows {rmin - 10},{rmax + 12}')
    print(f'  --pill-rows {rmin - 14},{rmax + 16}')
    print(f'  --keep {runs[0][0] - 5},{runs[-2][1] + 5}   '
          f'# every glyph except the last')
    print(f'  --repeat <one glyph span, e.g. {runs[-2][0] - 5},{runs[-2][1] + 5}>')
    print(f'  --gap {gaps[-1] if gaps else 23}   '
          f'# gap before the old last glyph; a narrow repeat (a "1") needs less')
    last_w = runs[-1][1] - runs[-1][0] + 1
    print(f'  --shift <half the width you remove; the last glyph is {last_w}px wide>')


def repaint(im, px, args):
    tx0, tx1 = args.text_cols
    ty0, ty1 = args.pill_rows
    la0, la1 = args.left_anchor
    ra0, ra1 = args.right_anchor
    gy0, gy1 = args.text_rows

    def avg(x0, x1, y):
        n = x1 - x0
        return tuple(sum(px[x, y][c] for x in range(x0, x1)) / n for c in range(3))

    def smooth(x0, x1, y):
        rows = [yy for yy in range(y - 4, y + 5)]
        vals = [avg(x0, x1, yy) for yy in rows]
        return tuple(sum(v[c] for v in vals) / len(vals) for c in range(3))

    # background of the text band: exact per row, linear across
    bg_rows = {}
    xl, xr = (la0 + la1) / 2, (ra0 + ra1) / 2
    for y in range(ty0, ty1):
        lo, hi = smooth(la0, la1, y), smooth(ra0, ra1, y)
        bg_rows[y] = [tuple(lo[c] + (hi[c] - lo[c]) * (x - xl) / (xr - xl) for c in range(3))
                      for x in range(tx0, tx1)]

    def bg(x, y):
        return bg_rows[y][x - tx0]

    def alpha(x, y):
        p, g = px[x, y], bg(x, y)
        best = 0.0
        for c in range(3):
            d = 255 - g[c]
            if d > 12:
                best = max(best, (p[c] - g[c]) / d)
        return min(1.0, max(0.0, best))

    def ink(sx0, sx1):
        """Glyph coverage with the source codec's ringing halo removed."""
        a = {(x, y): alpha(x, y) for y in range(gy0, gy1) for x in range(sx0, sx1)}
        near = set()
        for x, y in (k for k, v in a.items() if v >= 0.55):
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    near.add((x + dx, y + dy))
        return {k: v for k, v in a.items() if k in near and v > 0.004}

    out = im.copy()
    op = out.load()
    for y in range(ty0, ty1):
        for x in range(tx0, tx1):
            op[x, y] = tuple(min(255, max(0, int(round(v)))) for v in bg(x, y))

    stamps = [(args.keep, args.shift)]
    if args.repeat:
        rs0, rs1 = args.repeat
        # ink end of the kept string, plus the gap, plus the overall shift
        stamps.append((args.repeat, args.keep[1] - 5 + args.gap - rs0 + args.shift))

    for (sx0, sx1), off in stamps:
        for (x, y), a in ink(sx0, sx1).items():
            tx = x + off
            if not (tx0 <= tx < tx1):
                continue
            g = bg(tx, y)
            op[tx, y] = tuple(min(255, max(0, int(round(g[c] + (255 - g[c]) * a))))
                              for c in range(3))
    return out


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--src', required=True)
    p.add_argument('--out')
    p.add_argument('--inspect', action='store_true')
    p.add_argument('--scan-cols', type=pair)
    p.add_argument('--scan-rows', type=pair)
    p.add_argument('--text-rows', type=pair, help='rows the glyph ink spans, with margin')
    p.add_argument('--pill-rows', type=pair, help='rows to repaint, wider than --text-rows')
    p.add_argument('--text-cols', type=pair, help='cols to repaint (default: around --keep)')
    p.add_argument('--left-anchor', type=pair, help='clean pill cols left of the text')
    p.add_argument('--right-anchor', type=pair, help='clean pill cols right of the text')
    p.add_argument('--keep', type=pair, required=False)
    p.add_argument('--repeat', type=pair)
    p.add_argument('--gap', type=int, default=23)
    p.add_argument('--shift', type=int, default=0)
    p.add_argument('-h', '--help', action='store_true')
    args = p.parse_args()

    if args.help:
        print(__doc__)
        return 0

    im = Image.open(args.src).convert('RGB')
    px = im.load()

    if args.inspect:
        inspect(px, im.size, args)
        return 0

    for need in ('out', 'text_rows', 'pill_rows', 'keep'):
        if not getattr(args, need):
            sys.exit(f'--{need.replace("_", "-")} is required; run --inspect first')

    if not args.text_cols:
        args.text_cols = (args.keep[0] - 10, args.keep[1] + 160)
    if not args.left_anchor:
        args.left_anchor = (args.text_cols[0] - 25, args.text_cols[0] - 2)
    if not args.right_anchor:
        args.right_anchor = (args.text_cols[1] + 2, args.text_cols[1] + 25)

    repaint(im, px, args).save(args.out)
    print(f'wrote {args.out} at {im.size[0]}x{im.size[1]}')
    print('now: compare it against the original before using it')
    return 0


if __name__ == '__main__':
    sys.exit(main())
