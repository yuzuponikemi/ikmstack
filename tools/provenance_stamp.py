#!/usr/bin/env python3
"""provenance_stamp.py -- burn provenance into a figure so it travels with it.

Motivation
----------
AGENTS.md 3-principle #1 keeps figures OUT of git and reproduces them from
"raw data (Drive) + script (git) + commit SHA (MANIFEST)". That chain lives in
MANIFEST.md / DECISIONS.md / the lab log -- i.e. AWAY from the figure. Once a
PNG is pasted into a deck, a Slack thread, or a reviewer's inbox it loses every
link back to how it was made.

This helper does what Claude Science does for its artifacts: it stamps the
provenance directly onto the figure as a small footer, so a lone image still
answers "which script? which data era? which commit?". It does NOT replace the
MANIFEST chain -- it mirrors a compact pointer to it onto the pixels.

Footer text (compact, one line):

    <script>  |  data: <data_era>  |  <repo>@<sha>  |  generated <date>

Any field can be omitted; empty fields drop out (no dangling separators).

Design constraints
------------------
* English only (AGENTS.md script rule: measurement/instrument PCs run CP932
  consoles; Japanese in executable code corrupts / raises ParseException).
* matplotlib is imported lazily inside stamp()/savefig_stamped() so this module
  can be imported (and --selftest run) on a box without matplotlib.
* git SHA / date lookups are best-effort and never raise: a missing git or a
  non-repo directory yields "nogit" / today's date rather than a crash.

Use from an experiment plotting script
--------------------------------------
    import sys, pathlib
    # experiments/<experiment_id>/scripts/foo.py -> repo_root/tools
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools"))
    from provenance_stamp import savefig_stamped

    savefig_stamped(fig, OUT / "theta_scan.png", data_era="2026-06 tube set A", dpi=110)

or stamp then save yourself:

    from provenance_stamp import stamp
    stamp(fig, data_era="2026-06 tube set A")
    fig.savefig(OUT / "theta_scan.png", dpi=110)

CLI
---
    python tools/provenance_stamp.py --selftest      # verify text assembly (no matplotlib)
    python tools/provenance_stamp.py --text [--data-era ...] [--script ...]   # print footer only
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

# Force UTF-8 so any stray non-ASCII (e.g. a data_era a caller passes) does not
# crash on a cp1252/cp932 console. Best effort; harmless where unsupported.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - older/odd streams
        pass

SEP = "  |  "


def git_short_sha(start: Path | None = None) -> str:
    """Best-effort short commit SHA of the repo containing `start` (or cwd).

    Returns "nogit" if git is absent, the path is not a work tree, or the call
    times out. Appends "-dirty" when the work tree has uncommitted changes, so a
    figure stamped from a modified checkout is visibly not reproducible-as-is.
    """
    cwd = str((start or Path.cwd()))
    try:
        sha = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if sha.returncode != 0:
            return "nogit"
        rev = sha.stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", cwd, "-c", "core.quotepath=false", "status", "--porcelain"],
            capture_output=True, text=True, encoding="utf-8", timeout=5,
        )
        if dirty.returncode == 0 and dirty.stdout.strip():
            rev += "-dirty"
        return rev
    except (OSError, subprocess.SubprocessError):
        return "nogit"


def repo_name(start: Path | None = None) -> str:
    """Best-effort repo directory name (toplevel), else 'repo'."""
    cwd = str((start or Path.cwd()))
    try:
        top = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if top.returncode == 0 and top.stdout.strip():
            return Path(top.stdout.strip()).name
    except (OSError, subprocess.SubprocessError):
        pass
    return "repo"


def provenance_text(
    *,
    script: str | None = None,
    data_era: str | None = None,
    sha: str | None = None,
    repo: str | None = None,
    generated: str | bool | None = None,
    extra: str | None = None,
    start: Path | None = None,
) -> str:
    """Assemble the one-line footer. Pure string assembly (no matplotlib).

    Defaults are auto-filled from the environment:
      script    -> basename of sys.argv[0]
      sha/repo  -> git lookup rooted at `start` (or the script's dir, or cwd)
      generated -> today's ISO date; pass generated=False to omit the date

    Pass generated="" or generated=False to drop the date; pass an explicit
    string to pin it (useful for deterministic tests).
    """
    if start is None:
        argv0 = sys.argv[0] if sys.argv and sys.argv[0] else ""
        start = Path(argv0).resolve().parent if argv0 else Path.cwd()

    if script is None:
        argv0 = sys.argv[0] if sys.argv and sys.argv[0] else ""
        script = Path(argv0).name or "?"

    if sha is None:
        sha = git_short_sha(start)
    if repo is None:
        repo = repo_name(start)

    if generated is None:
        generated = date.today().isoformat()
    elif generated is False:
        generated = ""

    parts: list[str] = [script]
    if data_era:
        parts.append(f"data: {data_era}")
    if sha:
        parts.append(f"{repo}@{sha}")
    if generated:
        parts.append(f"generated {generated}")
    if extra:
        parts.append(extra)
    return SEP.join(p for p in parts if p)


def stamp(fig, *, loc: str = "bottom-right", fontsize: int = 6,
          color: str = "0.5", text: str | None = None, **kwargs):
    """Add the provenance footer to a matplotlib Figure and return the text obj.

    `text` overrides the auto-assembled string. Extra kwargs go to
    provenance_text() (script=, data_era=, sha=, repo=, generated=, extra=).
    `loc` is one of bottom-right / bottom-left / bottom-center.
    """
    body = text if text is not None else provenance_text(**kwargs)
    if loc == "bottom-left":
        x, ha = 0.005, "left"
    elif loc == "bottom-center":
        x, ha = 0.5, "center"
    else:  # bottom-right (default)
        x, ha = 0.995, "right"
    # y just above the bottom edge in figure fraction; matplotlib clips nothing
    # here because text lives in figure coords, not axes coords.
    return fig.text(x, 0.004, body, ha=ha, va="bottom",
                    fontsize=fontsize, color=color, alpha=0.9)


def savefig_stamped(fig, path, *, loc: str = "bottom-right", fontsize: int = 6,
                    color: str = "0.5", text: str | None = None,
                    stamp_kwargs: dict | None = None, **savefig_kwargs):
    """Stamp `fig` then save it. Extra kwargs pass through to fig.savefig().

    Provenance fields go via stamp_kwargs={"data_era": ..., ...}; savefig
    options (dpi=, bbox_inches=, ...) are the remaining kwargs.
    """
    stamp(fig, loc=loc, fontsize=fontsize, color=color, text=text,
          **(stamp_kwargs or {}))
    fig.savefig(path, **savefig_kwargs)
    return path


# --- selftest -----------------------------------------------------------------

def _selftest() -> int:
    """Verify text assembly without needing matplotlib. Returns 0 on pass."""
    cases = []

    def check(name, got, want):
        ok = got == want
        cases.append((name, ok, got, want))
        return ok

    # sha/date pinned so the assembly is deterministic.
    check(
        "all fields",
        provenance_text(script="foo.py", data_era="2026-06 set A",
                        sha="abc1234", repo="Ikemi-lab", generated="2026-07-16"),
        "foo.py  |  data: 2026-06 set A  |  Ikemi-lab@abc1234  |  generated 2026-07-16",
    )
    check(
        "no data_era, no date",
        provenance_text(script="foo.py", data_era=None, sha="abc1234",
                        repo="Ikemi-lab", generated=False),
        "foo.py  |  Ikemi-lab@abc1234",
    )
    check(
        "script only",
        provenance_text(script="foo.py", sha="", repo="", generated=False),
        "foo.py",
    )
    check(
        "extra appended",
        provenance_text(script="foo.py", sha="", generated=False,
                        extra="n=42"),
        "foo.py  |  n=42",
    )
    check(
        "dirty sha kept verbatim",
        provenance_text(script="s.py", sha="deadbee-dirty", repo="R",
                        generated=False),
        "s.py  |  R@deadbee-dirty",
    )

    failed = [c for c in cases if not c[1]]
    for name, ok, got, want in cases:
        mark = "ok  " if ok else "FAIL"
        print(f"  [{mark}] {name}")
        if not ok:
            print(f"        got : {got!r}")
            print(f"        want: {want!r}")
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true",
                    help="run built-in text-assembly tests (no matplotlib)")
    ap.add_argument("--text", action="store_true",
                    help="print the assembled footer text and exit")
    ap.add_argument("--script", default=None)
    ap.add_argument("--data-era", default=None)
    ap.add_argument("--sha", default=None)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--no-date", action="store_true", help="omit the generated date")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    if args.text:
        print(provenance_text(
            script=args.script, data_era=args.data_era, sha=args.sha,
            repo=args.repo, generated=(False if args.no_date else None)))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
