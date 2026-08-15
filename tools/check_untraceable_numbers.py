#!/usr/bin/env python3
"""check_untraceable_numbers.py -- flag empirical numbers that carry no provenance anchor.

Motivation
----------
AI-assisted science fails in three characteristic ways: bad citations,
UNTRACEABLE NUMBERS, and figures that do not match their code. The harness
already covers figures-vs-code (tools/check_report_figures.py) and value
correctness for opted-in experiments (tools/dr/*, the .dr-gate marker). What was
missing is the cheapest tier of the "untraceable numbers" check.

This linter is that cheapest tier. It does NOT verify that a number is CORRECT
(that is numeric_compare / the dr-audit ledger's job -- a different function,
kept separate per AGENTS.md "1 機能 = 1 権威"). It only asks: does each empirical
number in a report sit near a PROVENANCE ANCHOR -- a link, a primary-record id
(<experiment_id>-R###), a figure/script path, a source label, or a data-era mention?
A number with no nearby anchor is one a reader cannot trace, so it is flagged.

Safe-by-construction (same discipline as the dr gate)
-----------------------------------------------------
Purely opt-in. An experiment is checked ONLY if it carries a `.numbers-gate`
marker file. Experiments without the marker are never touched -- so adding this
tool cannot break anyone's commit. You opt in when your REPORT is written to
satisfy the linter, not before.

Marker format (`experiments/<experiment_id>/.numbers-gate`), all keys optional:
    # comment lines start with '#'
    scope: report      # 'report' (default, REPORT.md only) | 'reports' (REPORT.md + reports/**.md)
    files: a.md, b.md  # explicit files (relative to the experiment dir); overrides scope
An empty marker means: check REPORT.md only.

Suppression
-----------
A paragraph is exempt if it contains an inline HTML comment:
    <!-- numbers-ok -->                 or   <!-- numbers-ok: reason -->
Use it for numbers that are genuinely self-evident / definitional and need no
source (say so in the reason).

What counts as an "empirical number" (conservative, to avoid false positives)
-----------------------------------------------------------------------------
Flagged: decimals (3.14), percentages (2%), unit-bearing quantities (110 dpi,
5 ms, 3.3 V, 20x), scientific notation (1.2e-3).
NOT flagged: bare integers (counts like "8 tubes" are usually contextual), dates
(2026-07-16), ids (E059, R001, #40), lowercase-v versions (v1.2). Numbers inside
`inline code` are treated as verbatim config and skipped.

Anchors (any one in the same paragraph makes the number traceable)
------------------------------------------------------------------
markdown link/image `](`, primary-record id `<PREFIX>\\d+-R\\d+`, a figure output
dir (from .lab-config.json allowed_figure_roots) or image file, a script/code path (.py .sh
or a backticked path), a source label (出典/根拠/source/ref/cf/via/URL), a
data-era mention (data_era/data:/era/期間), a footnote/citation marker ([^ or [@).

Prose is anchored strictly (same paragraph). A markdown table is structured data
whose provenance sits in its caption/intro, so a table ALSO passes if any anchor
appeared earlier in the same section (section = between two headings). This
matches how reports cite a figure/script once, then show its tabular data below.

Usage
-----
    python tools/check_untraceable_numbers.py            # staged marked experiments (pre-commit)
    python tools/check_untraceable_numbers.py --all      # every marked experiment
    python tools/check_untraceable_numbers.py --experiment experiments/<experiment_id>
    python tools/check_untraceable_numbers.py --file path/to/REPORT.md   # ad hoc one file
    python tools/check_untraceable_numbers.py --selftest # built-in fixtures (no repo needed)

Exit codes: 0 = PASS (or nothing to check) / 1 = violations found / 2 = usage/config error.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import report_meta  # noqa: E402  (load_config を共用)

# install モデルでは tools/ が harness への symlink のことがある。__file__ を
# resolve() すると harness 側に張り付くので、cwd(=作業リポジトリ=記録層)基準で解決する。
REPO_ROOT = Path.cwd()
MARKER = ".numbers-gate"

# --- number detection ---------------------------------------------------------
# Units we treat as marking an empirical quantity. Ordered longest-first inside
# the alternation so e.g. "ms" wins before "m".
_UNITS = (
    r"ns|µs|us|ms|s|Hz|kHz|MHz|GHz|nm|µm|um|mm|cm|km|m|kV|mV|µV|uV|V|mA|µA|uA|A|"
    r"mL|µL|uL|L|°C|degC|dB|dpi|px|fps|rpm|bar|kPa|MPa|Pa|mW|kW|W|Ω|ohm|mg|kg|g|x|×"
)
NUM_PATTERNS = [
    re.compile(r"(?<![\w.])\d+(?:\.\d+)?[eE][-+]?\d+(?![\w.])"),          # sci notation
    re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s*%"),                            # percentage
    re.compile(rf"(?<![\w.])\d+(?:\.\d+)?\s*(?:{_UNITS})(?![\w])"),        # unit-bearing
    re.compile(r"(?<![\w.])\d+\.\d+(?![\w.])"),                            # bare decimal
]
# Exclusions applied to a matched span's surrounding text.
DATE_RE = re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}")
VERSION_RE = re.compile(r"\bv\d+\.\d+")

INLINE_CODE_RE = re.compile(r"`[^`]*`")
FRONTMATTER_RE = re.compile(r"^---\s*$")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
SUPPRESS_RE = re.compile(r"<!--\s*numbers-ok(?::[^>]*)?\s*-->")

# The experiment-id prefix and the figure output roots are notebook-specific
# (.lab-config.json), so the anchor alternation is built at import time.
_CFG = report_meta.load_config(REPO_ROOT)
_PREFIX = re.escape(str(_CFG.get("experiment_id_prefix", "E")))
_FIG_ROOTS = "|".join(
    re.escape(r.rstrip("/")) + "/"
    for r in _CFG.get("allowed_figure_roots", ["_generated", "figures"])
)

ANCHOR_RE = re.compile(
    r"\]\("                              # markdown link/image target
    # The id prefix is matched case-SENSITIVELY (inline (?-i:…)) even though the
    # rest of this alternation is case-insensitive: a one-letter prefix like "E"
    # would otherwise swallow the exponent in "1.2e-3".
    rf"|(?<![A-Za-z0-9])(?-i:{_PREFIX})\d+-R\d+"   # primary-record id (this notebook)
    rf"|(?<![A-Za-z0-9])(?-i:{_PREFIX})-\d+"       # hyphenated cross-record/ticket reference
    rf"|{_FIG_ROOTS}"                     # figure output roots (.lab-config.json)
    r"|\.(?:png|jpg|jpeg|gif|svg|webp)\b"
    # a source/data file path (any common language or data extension) is a pointer
    r"|\.(?:py|ps1|cs|cpp|hpp|[ch]|ino|ts|tsx|js|java|go|rs|sql|md|"
    r"csv|tsv|json|ya?ml|log|ini|xlsx?|txt)\b"
    r"|\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b"  # git commit SHA
    r"|https?://"
    r"|\[\^|\[@"                          # footnote / pandoc citation
    r"|出典|根拠|期間"
    r"|\bsource\b|\bref\b|\bref:|\bcf\.|\bvia\b"
    r"|data_era|data:|\bera\b",
    re.IGNORECASE,
)


def find_numbers(text_no_code: str) -> list[str]:
    """Return matched empirical-number substrings, minus dates/versions."""
    hits: list[str] = []
    # Blank out dates and versions so their digits cannot match number patterns.
    masked = VERSION_RE.sub(lambda m: " " * len(m.group()), text_no_code)
    masked = DATE_RE.sub(lambda m: " " * len(m.group()), masked)
    for pat in NUM_PATTERNS:
        for m in pat.finditer(masked):
            hits.append(m.group().strip())
    return hits


def _is_table(para: str) -> bool:
    """True if the paragraph is a markdown table (>=2 lines starting with '|')."""
    pipe_lines = sum(1 for ln in para.splitlines()
                     if ln.strip() and ln.lstrip().startswith("|"))
    return pipe_lines >= 2


def iter_paragraphs(md_text: str):
    """Yield (start_lineno, text, is_heading) for prose paragraphs and headings.

    Skips YAML frontmatter and fenced code blocks. Heading lines are emitted with
    is_heading=True so the caller can reset section state; prose/table paragraphs
    are emitted with is_heading=False. A paragraph is a maximal run of non-blank,
    non-skipped lines.
    """
    lines = md_text.splitlines()
    i = 0
    n = len(lines)
    # frontmatter
    if lines and FRONTMATTER_RE.match(lines[0]):
        i = 1
        while i < n and not FRONTMATTER_RE.match(lines[i]):
            i += 1
        i += 1  # past closing ---
    in_fence = False
    buf: list[str] = []
    buf_start = 0
    while i < n:
        line = lines[i]
        if FENCE_RE.match(line):
            in_fence = not in_fence
            if buf:
                yield buf_start, "\n".join(buf), False
                buf = []
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        if HEADING_RE.match(line):
            if buf:
                yield buf_start, "\n".join(buf), False
                buf = []
            yield i + 1, line, True
            i += 1
            continue
        if line.strip() == "":
            if buf:
                yield buf_start, "\n".join(buf), False
                buf = []
        else:
            if not buf:
                buf_start = i + 1  # 1-indexed
            buf.append(line)
        i += 1
    if buf:
        yield buf_start, "\n".join(buf), False


def check_text(md_text: str):
    """Return list of violations: (lineno, number, paragraph_first_line).

    Prose paragraphs are anchored strictly (an anchor must be in the same
    paragraph). A markdown table is structured data whose provenance is
    conventionally stated in its caption/intro, so a table also passes if any
    anchor appeared earlier in the same section (reset at each heading).
    """
    violations = []
    section_anchor = False
    for lineno, para, is_heading in iter_paragraphs(md_text):
        # a heading starts a new section; it may itself carry an anchor
        if is_heading:
            section_anchor = bool(ANCHOR_RE.search(para))
            continue
        has_anchor = bool(ANCHOR_RE.search(para))
        if has_anchor:
            section_anchor = True
        if SUPPRESS_RE.search(para):
            continue
        # numbers are detected on prose with inline code removed...
        prose = INLINE_CODE_RE.sub(" ", para)
        numbers = find_numbers(prose)
        if not numbers:
            continue
        # ...but anchors may live in inline code (a backticked path), so check raw.
        if has_anchor:
            continue
        # a table inherits its section's caption/intro anchor
        if _is_table(para) and section_anchor:
            continue
        first = para.strip().splitlines()[0].strip()
        # de-dup numbers within the paragraph, keep order
        seen = set()
        uniq = [x for x in numbers if not (x in seen or seen.add(x))]
        violations.append((lineno, ", ".join(uniq), first))
    return violations


def check_file(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"  ! cannot read {path}: {e}", file=sys.stderr)
        return []
    return check_text(text)


# --- marker + scope -----------------------------------------------------------

def parse_marker(marker_path: Path) -> dict:
    cfg = {"scope": "report", "files": None}
    try:
        for raw in marker_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, val = line.split(":", 1)
            key, val = key.strip().lower(), val.strip()
            if key == "scope" and val in ("report", "reports"):
                cfg["scope"] = val
            elif key == "files" and val:
                cfg["files"] = [f.strip() for f in val.split(",") if f.strip()]
    except OSError:
        pass
    return cfg


def files_for_experiment(exp: Path) -> list[Path]:
    cfg = parse_marker(exp / MARKER)
    if cfg["files"]:
        return [exp / f for f in cfg["files"]]
    out = []
    top = exp / "REPORT.md"
    if top.exists():
        out.append(top)
    if cfg["scope"] == "reports":
        reports = exp / "reports"
        if reports.is_dir():
            out.extend(sorted(reports.rglob("*.md")))
    return out


def marked_experiments(experiments_dir: Path) -> list[Path]:
    return [e for e in sorted(experiments_dir.glob("*/"))
            if (e / MARKER).exists() and not e.name.startswith(("_", "."))]


def staged_paths() -> list[Path]:
    try:
        r = subprocess.run(
            # -c core.quotepath=false: git otherwise escapes non-ASCII paths, and this
            # repo is full of Japanese report filenames. encoding="utf-8" must go with
            # it: text=True alone decodes with the locale codepage (cp1252 here) and
            # raw UTF-8 paths then fail to decode, leaving stdout as None.
            ["git", "-C", str(REPO_ROOT), "-c", "core.quotepath=false",
             "diff", "--cached", "--name-only"],
            capture_output=True, text=True, encoding="utf-8", timeout=10)
        if r.returncode != 0:
            return []
        return [REPO_ROOT / line for line in r.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError):
        return []


def report_violations(scope_label: str, per_file) -> int:
    total = 0
    for path, violations in per_file:
        if not violations:
            continue
        total += len(violations)
        rel = path.relative_to(REPO_ROOT) if path.is_absolute() and str(path).startswith(str(REPO_ROOT)) else path
        for lineno, numbers, first in violations:
            print(f"  {rel}:{lineno}")
            print(f"      numbers with no provenance anchor: {numbers}")
            print(f"      paragraph: {first[:100]}")
    if total:
        print(f"\n[FAIL] {total} untraceable number(s) in {scope_label}.")
        print("       Anchor each with a source: a link, an <id>-R### id, a figure/script")
        print("       path, a 出典/source label, or a data-era. Definitional numbers that")
        print("       truly need no source: add  <!-- numbers-ok: reason -->  to the paragraph.")
        return 1
    print(f"[OK] no untraceable numbers in {scope_label}.")
    return 0


# --- selftest -----------------------------------------------------------------

def _selftest() -> int:
    passing = [
        # anchored by link
        "The clamp closes in 5 ms, see [R001](reports/E070-R001_x.md).",
        # anchored by primary-record id
        "Throughput rose 12% (E059-R003).",
        # anchored by a hyphenated cross-record/ticket reference
        "E-058 で 76 回（7.1%）と出た。",
        # anchored by a non-python source-code path
        "起動シーケンス `Sequence/Boot/Init.cs` でエラーは 1.4% と稀。",
        # anchored by a git commit SHA
        "実機能コミットは 7746e4e1c、収束は 2.46 秒。",
        # anchored by figure path
        "See `_generated/plots/theta.png`: RMSE 0.42 over the sweep.",
        # anchored by script path
        "Computed by scripts/analyze.py; mean drift 3.3 V.",
        # anchored by source label
        "定格は 20x（出典: データシート）。",
        # inline-code number is verbatim config, not empirical prose
        "Set `reltol: 0.02` in the marker.",
        # bare integer / date / id are not flagged
        "We ran 8 tubes on 2026-07-16 for E044, version v1.2.",
        # suppressed
        "Confidence is 100%. <!-- numbers-ok: definitional upper bound -->",
        # number in fenced code is skipped
        "```\nvalue = 3.14\n```",
        # table whose section carries an anchor earlier (caption cites a figure)
        "## Results\nSee ![hist](figures/timing.png).\n\n"
        "| bin | share |\n|---|---|\n| <=1min | 87.3% |\n| 1-5min | 5.1% |",
        # table whose section carries an anchor via a script path
        "## Sweep\nComputed by `scripts/probe.py`.\n\n"
        "| dv | AUC |\n|---|---|\n| 0% | 0.995 |\n| 1% | 0.988 |",
    ]
    failing = [
        "Throughput improved by 12% after the change.",         # % no anchor
        "The clamp closes in 5 ms under load.",                  # unit no anchor
        "RMSE was 0.42 across the run.",                          # decimal no anchor
        "Signal was 1.2e-3 at baseline.",                        # sci notation no anchor
        # table with no anchor anywhere in its section stays flagged
        "## Raw\n| bin | share |\n|---|---|\n| <=1min | 87.3% |\n| 1-5min | 5.1% |",
        # a later section's anchor must NOT rescue an earlier unanchored table
        "## A\n| x | y |\n|---|---|\n| 1.5 | 2.5 |\n\n## B\nsee scripts/x.py",
    ]
    ok = True
    print("expect PASS (0 violations):")
    for t in passing:
        v = check_text(t)
        mark = "ok  " if not v else "FAIL"
        if v:
            ok = False
        print(f"  [{mark}] {t[:60]!r}  -> {v}")
    print("\nexpect FAIL (>=1 violation):")
    for t in failing:
        v = check_text(t)
        mark = "ok  " if v else "FAIL"
        if not v:
            ok = False
        print(f"  [{mark}] {t[:60]!r}  -> {[n for _, n, _ in v]}")
    print("\nSELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="check every marked experiment")
    g.add_argument("--experiment", help="check one experiment dir")
    g.add_argument("--file", help="check one markdown file (ad hoc)")
    g.add_argument("--selftest", action="store_true", help="run built-in fixtures")
    ap.add_argument("experiments", nargs="?",
                    help="experiments/ dir (default: repo experiments/)")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.file:
        p = Path(args.file)
        if not p.is_file():
            print(f"file not found: {p}", file=sys.stderr)
            return 2
        return report_violations(str(p), [(p, check_file(p))])

    exp_dir = Path(args.experiments) if args.experiments else REPO_ROOT / "experiments"
    if not exp_dir.is_dir():
        print(f"experiments dir not found: {exp_dir}", file=sys.stderr)
        return 2

    if args.experiment:
        exp = Path(args.experiment)
        if not (exp / MARKER).exists():
            print(f"[skip] {exp} has no {MARKER} marker (opt-in only).")
            return 0
        per_file = [(f, check_file(f)) for f in files_for_experiment(exp)]
        return report_violations(exp.name, per_file)

    experiments = marked_experiments(exp_dir)
    if not args.all:
        # pre-commit mode: restrict to experiments with staged changes.
        staged = staged_paths()
        staged_exps = set()
        for sp in staged:
            try:
                rel = sp.resolve().relative_to((exp_dir).resolve())
            except ValueError:
                continue
            if rel.parts:
                staged_exps.add(rel.parts[0])
        experiments = [e for e in experiments if e.name in staged_exps]

    if not experiments:
        print("[OK] no marked experiments to check"
              + ("" if args.all else " among staged changes") + ".")
        return 0

    rc = 0
    for exp in experiments:
        per_file = [(f, check_file(f)) for f in files_for_experiment(exp)]
        rc |= report_violations(exp.name, per_file)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
