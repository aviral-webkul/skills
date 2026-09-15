#!/usr/bin/env python3
"""
Compare a baseline/candidate screenshot pair.

    python3 compare.py pixdiff <shots-dir> <page> <viewport>
    python3 compare.py sbs     <shots-dir> <page> <viewport> [y0 y1]
    python3 compare.py zoom    <shots-dir> <page> <viewport> <x0> <y0> <x1> <y1> [scale]

Run `pixdiff` on every page first: it turns a long eyeball exercise into a short
list of regions worth looking at, and proves equivalence where nothing changed.

Files are read as <page>__<viewport>__baseline.png / __candidate.png, matching
the naming capture.js writes.
"""
import os
import sys

from PIL import Image, ImageChops

THRESHOLD = 25
MAX_WIDTH = 2200
SEPARATOR = (255, 0, 255)


def load(shots, page, viewport):
    def one(side):
        p = os.path.join(shots, f'{page}__{viewport}__{side}.png')
        if not os.path.exists(p):
            sys.exit(f'missing: {p}')
        return Image.open(p).convert('RGB')

    return one('baseline'), one('candidate')


def out_path(shots, name):
    return os.path.join(os.path.dirname(os.path.abspath(shots)) or '.', name)


def pixdiff(shots, page, viewport):
    """Report whether anything differs, and in which horizontal bands."""
    a, b = load(shots, page, viewport)
    print('sizes  ', a.size, b.size)

    w, h = min(a.width, b.width), min(a.height, b.height)
    a, b = a.crop((0, 0, w, h)), b.crop((0, 0, w, h))

    diff = ImageChops.difference(a, b).convert('L')
    bbox = diff.point(lambda p: 255 if p > THRESHOLD else 0).getbbox()
    print('bbox   ', bbox)

    # Bands group the differing rows so a long page reduces to a few regions to
    # look at. They sample every third column and need several hits per row, so
    # a narrow change (a stray character, a small icon) shows in the bbox but
    # not here -- the bbox, not the bands, decides whether anything differs.
    px = diff.load()
    rows = [y for y in range(h) if sum(1 for x in range(0, w, 3) if px[x, y] > THRESHOLD) > 2]

    bands = []
    for y in rows:
        if bands and y - bands[-1][1] <= 6:
            bands[-1][1] = y
        else:
            bands.append([y, y])

    print('bands  ', bands[:40])

    if bbox is None:
        print('=> identical over the overlapping area '
              '(a small height delta is usually debug-bar body padding)')
    elif not bands:
        x0, y0, x1, y1 = bbox
        print(f'=> one narrow difference only, {x1 - x0}x{y1 - y0}px at ({x0}, {y0}) '
              f'-- too small for a band; zoom it')


def sbs(shots, page, viewport, y0=0, y1=0):
    """Baseline left, candidate right, separated by a magenta gutter."""
    a, b = load(shots, page, viewport)

    if y1:
        a = a.crop((0, y0, a.width, min(y1, a.height)))
        b = b.crop((0, y0, b.width, min(y1, b.height)))

    gap = 20
    canvas = Image.new('RGB', (a.width + b.width + gap, max(a.height, b.height)), SEPARATOR)
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width + gap, 0))

    if canvas.width > MAX_WIDTH:
        canvas = canvas.resize((MAX_WIDTH, int(canvas.height * MAX_WIDTH / canvas.width)))

    path = out_path(shots, f'sbs_{page}_{viewport}_{y0}_{y1}.png')
    canvas.save(path)
    print(path, canvas.size)


def zoom(shots, page, viewport, x0, y0, x1, y1, scale=2.0):
    """Baseline above, candidate below, magnified — for reading small details."""
    a, b = load(shots, page, viewport)
    a = a.crop((x0, y0, x1, y1))
    b = b.crop((x0, y0, x1, y1))

    size = (int(a.width * scale), int(a.height * scale))
    a, b = a.resize(size, Image.LANCZOS), b.resize(size, Image.LANCZOS)

    canvas = Image.new('RGB', (a.width, a.height * 2 + 16), SEPARATOR)
    canvas.paste(a, (0, 0))
    canvas.paste(b, (0, a.height + 16))

    path = out_path(shots, f'zoom_{page}_{viewport}_{x0}_{y0}.png')
    canvas.save(path)
    print(path, canvas.size)


if __name__ == '__main__':
    mode, shots, page, viewport = sys.argv[1:5]
    rest = [float(x) for x in sys.argv[5:]]

    if mode == 'pixdiff':
        pixdiff(shots, page, viewport)
    elif mode == 'sbs':
        sbs(shots, page, viewport, *[int(x) for x in rest])
    elif mode == 'zoom':
        zoom(shots, page, viewport, *[int(x) for x in rest[:4]], *(rest[4:5] or [2.0]))
    else:
        sys.exit('mode must be pixdiff, sbs or zoom')
