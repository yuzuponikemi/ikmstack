#!/bin/sh
# Copy the pinned third-party files a course page loads into <course_dir>/assets/, so the course
# makes no CDN requests (claude.ai Artifacts block stylesheets from anywhere but Google Fonts, which
# left formulas unstyled when KaTeX came from cdnjs).
#   sh vendor_assets.sh <course_dir> [--no-math] [--no-code]
#   -> assets/katex/      katex 0.16.9: katex.min.css, katex.min.js, auto-render.min.js, fonts/*.woff2
#   -> assets/highlight/  highlight.js 11.9.0 core (python, c, bash, yaml, ...) + verilog + tcl,
#                         and hl.js / hl.css from this skill (VS Code Light+/Dark+ colours)
# Idempotent: files already present are overwritten with the pinned versions. Needs npm (registry access).
set -e
course="$1"; shift || true
[ -n "$course" ] || { echo "usage: vendor_assets.sh <course_dir> [--no-math] [--no-code]" >&2; exit 2; }
math=1; code=1
for a in "$@"; do case "$a" in --no-math) math=0;; --no-code) code=0;; esac; done
skill="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
if [ $math = 1 ]; then
  (cd "$tmp" && npm pack katex@0.16.9 >/dev/null 2>&1 && mkdir k && tar xzf katex-0.16.9.tgz -C k)
  d="$course/assets/katex"; mkdir -p "$d/fonts"
  cp "$tmp/k/package/dist/katex.min.css" "$tmp/k/package/dist/katex.min.js" "$tmp/k/package/dist/contrib/auto-render.min.js" "$d/"
  cp "$tmp/k/package/dist/fonts/"*.woff2 "$d/fonts/"
  echo "katex 0.16.9 -> $d"
fi
if [ $code = 1 ]; then
  (cd "$tmp" && npm pack @highlightjs/cdn-assets@11.9.0 >/dev/null 2>&1 && mkdir h && tar xzf highlightjs-cdn-assets-11.9.0.tgz -C h)
  d="$course/assets/highlight"; mkdir -p "$d"
  cp "$tmp/h/package/highlight.min.js" "$tmp/h/package/languages/verilog.min.js" "$tmp/h/package/languages/tcl.min.js" "$d/"
  cp "$skill/assets/highlight/hl.js" "$skill/assets/highlight/hl.css" "$d/"
  echo "highlight.js 11.9.0 -> $d"
fi
