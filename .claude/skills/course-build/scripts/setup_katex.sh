#!/bin/sh
# Install KaTeX 0.16.9 into a cache dir and print the KATEX_DIST value for browser_check.mjs.
# Use when cdnjs is blocked (cloud sandbox): formulas then render from local files and TeX errors surface.
#   eval "$(sh setup_katex.sh /tmp/katex-cache)"   # exports KATEX_DIST
set -e
dir="${1:-${TMPDIR:-/tmp}/course-build-katex}"
if [ ! -f "$dir/node_modules/katex/dist/katex.min.js" ]; then
  mkdir -p "$dir"
  (cd "$dir" && npm init -y >/dev/null 2>&1 && npm install katex@0.16.9 >/dev/null 2>&1)
fi
echo "export KATEX_DIST=$dir/node_modules/katex/dist"
