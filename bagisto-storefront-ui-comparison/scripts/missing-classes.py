#!/usr/bin/env python3
"""
Find utility classes written in Blade that the theme's compiled CSS does not define.

    python3 missing-classes.py <views-dir> '<built-css-glob>'

    python3 missing-classes.py \
      "$CANDIDATE/packages/Webkul/Shop/src/Resources/views" \
      "$CANDIDATE/public/themes/shop/default/build/assets/*.css"

Run it against the BASELINE too and report only what is newly missing — some
misses pre-date the change and are not regressions.

Why this matters: a class that generates no rule fails silently. Nothing errors,
the element simply falls back to whatever a component class gives it, and no
Blade diff shows it. Tailwind v4 only generates spacing utilities for multiples
of 0.25, so an automated `px-[74.5px]` -> `px-18.625` conversion emits nothing
at all. Values like w-37.543, h-9.375 and px-12.7 are always bugs.

Tokens ending in a quote are Vue object-syntax fragments picked up by the naive
scan; they appear on both sides and can be ignored.
"""
import glob
import os
import re
import sys

# Utilities whose absence changes layout. Colour and typography utilities are
# excluded: they are far noisier and rarely converted to invalid values.
UTILITY = re.compile(
    r'^((max-)?(sm|md|lg|xl|2xl|rtl|ltr|hover|focus|group-hover|peer-checked|peer-focus'
    r'|focus-visible|first|last|odd|even|after|before|group-focus|peer-focus-visible):)*'
    r'(w|h|min-w|min-h|max-w|max-h|p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr'
    r'|gap|gap-x|gap-y|top|bottom|left|right|inset|text|leading|tracking'
    r'|rounded|border|z|size|basis|translate-x|translate-y)-[0-9]'
)

SAFE = re.compile(r"[A-Za-z0-9:\-./\[\]%!#()_,'\"*+]+")


def blade_classes(views_dir):
    found = set()

    for root, _, files in os.walk(views_dir):
        for name in files:
            if not name.endswith('.blade.php'):
                continue

            text = open(os.path.join(root, name), errors='ignore').read()

            for match in re.finditer(r'class="([^"]*)"', text):
                value = re.sub(r'\{\{.*?\}\}', ' ', match.group(1), flags=re.S)
                value = re.sub(r'\{!!.*?!!\}', ' ', value, flags=re.S)

                for token in value.split():
                    if SAFE.fullmatch(token):
                        found.add(token)

    return found


def css_selector(token):
    """The CSS-escaped form of a class name: every non-word character is backslashed."""
    return '.' + ''.join(c if (c.isalnum() or c in '-_') else '\\' + c for c in token)


if __name__ == '__main__':
    views_dir, css_glob = sys.argv[1], sys.argv[2]

    paths = glob.glob(css_glob)
    if not paths:
        sys.exit(f'no CSS matched: {css_glob} — build the theme first (npm run build)')

    # Read every matching file: a theme usually ships more than one bundle and
    # checking only the first produces a page of false positives.
    css = ''.join(open(p, errors='ignore').read() for p in paths)

    tokens = blade_classes(views_dir)
    missing = [t for t in sorted(tokens) if UTILITY.match(t) and css_selector(t) not in css]

    print(f'{len(tokens)} class tokens scanned across {len(paths)} CSS file(s); {len(missing)} generate no rule')
    for token in missing:
        print(' ', token)
