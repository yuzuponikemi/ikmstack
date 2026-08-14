#!/usr/bin/env python3
"""check_script_encoding.py - guard field/measurement PowerShell against the
CP932 parse-crash mode (dependency-free).

Rule (AGENTS.md "スクリプト規約"): executable code should be ASCII/English.
On instrument & measurement PCs (Japanese Windows) PowerShell 5.1 reads a .ps1
using the system code page (CP932) unless the file carries a UTF-8 BOM. A .ps1
that contains non-ASCII bytes but has NO BOM therefore raises a ParseException
there and simply will not run (this has happened on a real instrument PC).

This linter enforces the safety floor for the scripts most likely to run off the
dev PC: PowerShell files under experiments/<id>/scripts/. For each such file it
requires that, IF the file contains any non-ASCII byte, it begins with a UTF-8
BOM (EF BB BF). Pure-ASCII files (the preferred form) pass trivially.

Out of scope (intentionally):
  - .py analysis/plotting scripts: Python 3 reads source as UTF-8 regardless of
    BOM, and their Japanese is often intentional (matplotlib figure labels).
  - regenerate.ps1, tools/, delivery/ etc.: dev-PC-only (PowerShell 7 / UTF-8).

Scope (repo-root relative): experiments/*/scripts/**/*.ps1

Usage:
  python tools/check_script_encoding.py            # staged files (pre-commit)
  python tools/check_script_encoding.py --check    # explicit alias of the above
  python tools/check_script_encoding.py --all      # every tracked in-scope file
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# install モデルでは tools/ が harness への symlink のことがある。__file__ を
# resolve() すると harness 側に張り付くので、cwd(=作業リポジトリ=記録層)基準で解決する。
REPO = Path.cwd()
IN_SCOPE = re.compile(r"^experiments/[^/]+/scripts/.*\.ps1$")
BOM = b"\xef\xbb\xbf"


def _git(args: list[str]) -> list[str]:
    out = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    )
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def in_scope(paths: list[str]) -> list[str]:
    return [p for p in paths if IN_SCOPE.match(p.replace("\\", "/"))]


def staged_files() -> list[str]:
    return in_scope(_git(["diff", "--cached", "--name-only", "--diff-filter=ACM"]))


def all_files() -> list[str]:
    return in_scope(_git(["ls-files", "experiments/*/scripts/*.ps1",
                          "experiments/*/scripts/**/*.ps1"]))


def first_nonascii_line(data: bytes) -> int:
    body = data[3:] if data.startswith(BOM) else data
    for i, line in enumerate(body.split(b"\n"), 1):
        if any(b > 127 for b in line):
            return i
    return 0


def check(rel: str) -> tuple[str, int] | None:
    """Return (rel, lineno) if the file violates, else None."""
    fp = REPO / rel
    if not fp.exists():
        return None
    data = fp.read_bytes()
    has_nonascii = any(b > 127 for b in (data[3:] if data.startswith(BOM) else data))
    if has_nonascii and not data.startswith(BOM):
        return (rel, first_nonascii_line(data))
    return None


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--all", action="store_true", help="check every tracked in-scope file")
    ap.add_argument("--check", action="store_true", help="alias for the default staged check")
    args = ap.parse_args(argv)

    files = all_files() if args.all else staged_files()
    violations = [v for v in (check(f) for f in files) if v]

    if violations:
        print("X field PowerShell has non-ASCII without a UTF-8 BOM "
              "(will ParseException on CP932/PS5.1):\n")
        for rel, lineno in violations:
            print(f"  {rel}:{lineno}")
        print("\n  Fix: make the file ASCII (preferred), or save it as UTF-8 with BOM.")
        print("  Scope: experiments/<id>/scripts/**/*.ps1  (see AGENTS.md スクリプト規約).")
        return 1

    scanned = len(files)
    tail = "" if args.all else " (staged)"
    print(f"OK: {scanned} in-scope field .ps1 file(s){tail} are ASCII or BOM-tagged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
