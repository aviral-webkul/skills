#!/usr/bin/env bash
# Convert captured PNGs to blog-ready WebP at an exact size.
#
#   ./to_webp.sh <png-dir> <out-dir> [WxH] [quality]
#   ./to_webp.sh shots ../screenshots 1120x880 85
#
# Uses "-resize WxH!" so wide grid captures (1440x1131) downscale to exactly 1120x880.
# Both are 1.2727:1, so nothing distorts.
set -euo pipefail

SRC="${1:?usage: to_webp.sh <png-dir> <out-dir> [WxH] [quality]}"
OUT="${2:?usage: to_webp.sh <png-dir> <out-dir> [WxH] [quality]}"
SIZE="${3:-1120x880}"
Q="${4:-85}"

command -v convert >/dev/null 2>&1 || { echo "ImageMagick 'convert' not found" >&2; exit 1; }
convert -list format 2>/dev/null | grep -qi webp || {
  echo "ImageMagick has no WebP delegate (check: convert -list format | grep -i webp)" >&2; exit 1; }

mkdir -p "$OUT"
shopt -s nullglob
n=0
for f in "$SRC"/*.png; do
  base="$(basename "$f" .png)"
  [[ "$base" == _* ]] && continue          # _-prefixed files are intermediates
  convert "$f" -resize "${SIZE}!" -quality "$Q" -define webp:method=6 "$OUT/$base.webp"
  n=$((n+1))
done

if [[ $n -eq 0 ]]; then echo "no PNGs found in $SRC" >&2; exit 1; fi
echo "converted $n file(s) -> $OUT"
identify "$OUT"/*.webp | awk '{print "  " $3, $1}'
