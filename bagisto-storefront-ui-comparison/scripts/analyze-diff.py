#!/usr/bin/env python3
"""
Reduce a Blade diff to the parts that can carry a UI regression.

    diff -ru <baseline>/packages/Webkul/Shop/src/Resources/views \
             <candidate>/packages/Webkul/Shop/src/Resources/views > shop-views.diff

    python3 analyze-diff.py shop-views.diff structural
    python3 analyze-diff.py shop-views.diff classes

structural  strips class="..." from both sides and prints only hunks whose markup
            changed — filters out the thousands of pure styling renames that a
            framework upgrade produces. Most of what survives is accessibility
            work (<span role=button> -> <button>, aria-*, sr-only): read it, do
            not report it.

classes     prints layout-critical class tokens removed or added per file
            (hidden, flex, block, absolute, sr-only, overflow-*, z-*). A dropped
            `hidden` is the classic way a placeholder becomes visible. Always
            cross-check a hit against the matching shimmer/skeleton file: if the
            skeleton kept `hidden` and the component lost it, it is unintended.
"""
import re
import sys

VISIBILITY = re.compile(
    r'^(hidden|block|inline|inline-block|flex|inline-flex|grid|contents|sr-only|not-sr-only'
    r'|absolute|relative|fixed|sticky|static|invisible|visible|collapse|truncate'
    r'|overflow-\w+|z-[\w.]+)$'
)


def hunks(path):
    """Yield (file, removed_lines, added_lines) for each -/+ run in a unified diff."""
    lines = open(path, errors='ignore').read().split('\n')
    current, i = None, 0

    while i < len(lines):
        line = lines[i]

        if line.startswith('+++ '):
            current = line[4:].split('\t')[0]

        is_run = ((line.startswith('-') and not line.startswith('---'))
                  or (line.startswith('+') and not line.startswith('+++')))

        if is_run:
            removed, added = [], []
            while i < len(lines) and lines[i].startswith('-') and not lines[i].startswith('---'):
                removed.append(lines[i][1:])
                i += 1
            while i < len(lines) and lines[i].startswith('+') and not lines[i].startswith('+++'):
                added.append(lines[i][1:])
                i += 1
            yield current, removed, added
            continue

        i += 1


def normalise(text):
    """Collapse whitespace and blank out class attributes so only markup remains."""
    text = re.sub(r'class="[^"]*"', 'class=""', text)
    return re.sub(r'\s+', ' ', text).strip()


def structural(path):
    for name, removed, added in hunks(path):
        if not name:
            continue

        before = [normalise(x) for x in removed if normalise(x)]
        after = [normalise(x) for x in added if normalise(x)]

        if before == after:
            continue

        print('###', name)
        for x in before:
            print(' -', x[:190])
        for x in after:
            print(' +', x[:190])
        print()


def classes(path):
    def tokens(text):
        found = set()
        for match in re.finditer(r'class="([^"]*)"', text):
            for token in match.group(1).split():
                found.add(token.replace('!', ''))  # the important marker moved sides in Tailwind v4
        return found

    for name, removed, added in hunks(path):
        if not name:
            continue

        before = tokens('\n'.join(removed))
        after = tokens('\n'.join(added))

        gone = sorted(t for t in before - after if VISIBILITY.match(t.split(':')[-1]))
        new = sorted(t for t in after - before if VISIBILITY.match(t.split(':')[-1]))

        if gone or new:
            print(name)
            print('  removed:', gone)
            print('  added  :', new)
            print()


if __name__ == '__main__':
    diff_path, mode = sys.argv[1], sys.argv[2]

    if mode == 'structural':
        structural(diff_path)
    elif mode == 'classes':
        classes(diff_path)
    else:
        sys.exit('mode must be structural or classes')
