#!/usr/bin/env python3
"""Per-experiment opt-in lightweight dr-audit gate.

Wires the deterministic dr tools (tools/dr/) into a *per-experiment opt-in* gate that
runs on commit (or manually). An experiment opts in by dropping a `.dr-gate`
marker file into its directory. Only experiments that carry the marker AND have
staged changes are gated -- so this is safe-by-construction: repos/experiments
without the marker are never touched (respects the decision to avoid a
global Stop hook; see tools/dr/README.md).

Lightweight subset (NOT the full /dr-audit skill):
    validate_ledger  -> schema of claims.jsonl
    numeric_compare  -> deterministic recompute of derived values
    ledger_to_prose  -> prose<->ledger tracking (only if the marker names a prose file)

The full audit (dr-verifier web re-fetch + dr_gate acceptance gate requiring
decision_driving all-verified) stays in the /dr-audit skill; it needs the web /
an agent and is not deterministic enough for a commit hook.

Marker format (`experiments/FL###_*/.dr-gate`), all keys optional:
    # comment lines start with '#'
    ledger: reports/claims.jsonl     # relative to the experiment dir; this is the default
    prose:  reports/E001-R001_...md  # relative; enables ledger_to_prose_check
    reltol: 0.02                     # relative tolerance for numeric_compare
                                     # (default 2%)
An empty marker means "use reports/claims.jsonl, no prose check, reltol 2%".

Usage:
    python tools/dr/dr_gate_precommit.py                # gate marked experiments among STAGED files
    python tools/dr/dr_gate_precommit.py --all          # gate every marked experiment
    python tools/dr/dr_gate_precommit.py --experiment experiments/E001_...  # gate one dir (testing)
    python tools/dr/dr_gate_precommit.py --ledger <path> [--prose <path>]     # gate an explicit ledger (testing)

Exit codes: 0 = PASS (or nothing to gate) / 1 = FAIL / 2 = usage/config error.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# Force UTF-8 so Japanese/emoji output from the child tools does not crash on
# Windows consoles (cp1252). Without this the tools raise
# UnicodeEncodeError and the gate would produce false failures.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - older/odd streams: best effort
        pass

TOOLS_DIR = Path(__file__).resolve().parent
# install モデルでは tools/ が harness への symlink のことがある。__file__ を
# resolve() すると harness 側に張り付くので、cwd(=作業リポジトリ=記録層)基準で解決する。
REPO_ROOT = Path.cwd()
MARKER_NAME = ".dr-gate"
DEFAULT_LEDGER = "reports/claims.jsonl"
EXP_RE = re.compile(r"(experiments/FL[^/]+)/")


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _run_tool(script: str, *args: str) -> tuple[int, str]:
    """Run one dr tool as a subprocess, reusing its CLI. Returns (rc, combined_output)."""
    cmd = [sys.executable, str(TOOLS_DIR / script), *args]
    proc = subprocess.run(
        cmd, cwd=str(REPO_ROOT), env=_child_env(),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _parse_marker(marker: Path) -> dict[str, str]:
    """Parse a `.dr-gate` marker into {ledger, prose, reltol}. Empty -> defaults."""
    cfg: dict[str, str] = {}
    try:
        text = marker.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        text = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip().lower(), val.split("#", 1)[0].strip()
        if key in ("ledger", "prose", "reltol") and val:
            cfg[key] = val
    return cfg


def _staged_experiments() -> list[Path]:
    """Experiment dirs (abs) that have staged changes. [] if git unavailable."""
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        return []
    dirs: dict[str, Path] = {}
    for rel in proc.stdout.splitlines():
        rel = rel.strip().replace("\\", "/")
        m = EXP_RE.search(rel)
        if m:
            d = m.group(1)
            dirs[d] = (REPO_ROOT / d)
    return list(dirs.values())


def _all_marked_experiments() -> list[Path]:
    exp_root = REPO_ROOT / "experiments"
    if not exp_root.is_dir():
        return []
    return sorted(p.parent for p in exp_root.glob("FL*/" + MARKER_NAME))


class GateResult:
    def __init__(self, label: str):
        self.label = label
        self.steps: list[tuple[str, bool, str]] = []  # (name, ok, output)

    @property
    def ok(self) -> bool:
        return all(ok for _, ok, _ in self.steps)


def gate_ledger(label: str, ledger: Path, prose: Path | None, reltol: str | None = None) -> GateResult:
    """Run the lightweight subset against one ledger. Reuses the existing CLIs."""
    res = GateResult(label)

    if not ledger.is_file():
        res.steps.append(("config", False, f"ledger not found: {ledger}"))
        return res

    if reltol is not None:
        try:
            float(reltol)
        except ValueError:
            res.steps.append(("config", False, f"reltol is not a number: {reltol!r}"))
            return res

    rc, out = _run_tool("validate_ledger.py", str(ledger))
    res.steps.append(("validate_ledger", rc == 0, out))
    if rc != 0:
        return res  # schema errors: downstream tools bail with rc=2 anyway

    nc_args = [str(ledger)] + (["--reltol", reltol] if reltol is not None else [])
    rc, out = _run_tool("numeric_compare.py", *nc_args)
    res.steps.append(("numeric_compare", rc == 0, out))

    if prose is not None:
        if not prose.is_file():
            res.steps.append(("ledger_to_prose_check", False, f"prose not found: {prose}"))
        else:
            rc, out = _run_tool("ledger_to_prose_check.py", str(prose), str(ledger))
            res.steps.append(("ledger_to_prose_check", rc == 0, out))
    return res


def gate_experiment(exp_dir: Path) -> GateResult | None:
    """Gate one experiment IF it carries a .dr-gate marker. None = not opted in."""
    marker = exp_dir / MARKER_NAME
    if not marker.is_file():
        return None
    cfg = _parse_marker(marker)
    ledger = exp_dir / cfg.get("ledger", DEFAULT_LEDGER)
    prose = (exp_dir / cfg["prose"]) if "prose" in cfg else None
    return gate_ledger(exp_dir.name, ledger, prose, cfg.get("reltol"))


def _print_result(res: GateResult, verbose: bool) -> None:
    tag = "[PASS]" if res.ok else "[FAIL]"
    print(f"\n{tag} {res.label}")
    for name, ok, out in res.steps:
        print(f"  {'ok ' if ok else 'FAIL'} :: {name}")
        if not ok or verbose:
            for ln in out.strip().splitlines():
                print(f"        {ln}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-experiment opt-in lightweight dr-audit gate")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="gate every experiment that has a .dr-gate marker")
    mode.add_argument("--experiment", help="gate this one experiment dir (must contain a marker)")
    mode.add_argument("--ledger", help="gate an explicit ledger path (testing; bypasses marker)")
    ap.add_argument("--prose", help="prose md to pair with --ledger")
    ap.add_argument("--verbose", action="store_true", help="print tool output even on PASS")
    args = ap.parse_args()

    results: list[GateResult] = []

    if args.ledger:
        prose = Path(args.prose) if args.prose else None
        results.append(gate_ledger(Path(args.ledger).name, Path(args.ledger), prose))
    elif args.experiment:
        exp = (REPO_ROOT / args.experiment) if not Path(args.experiment).is_absolute() else Path(args.experiment)
        r = gate_experiment(exp)
        if r is None:
            print(f"[skip] {exp} has no {MARKER_NAME} marker (not opted in). Nothing to gate.")
            return 0
        results.append(r)
    else:
        exps = _all_marked_experiments() if args.all else [
            d for d in _staged_experiments() if (d / MARKER_NAME).is_file()
        ]
        for exp in exps:
            r = gate_experiment(exp)
            if r is not None:
                results.append(r)

    if not results:
        # No opted-in experiment in scope -> nothing to do. This is the common
        # case for ordinary commits and must never block them.
        return 0

    print("# dr-audit lightweight gate — validate + numeric_compare + prose_check")
    failed = False
    for res in results:
        _print_result(res, args.verbose)
        failed = failed or not res.ok

    print("\n=== gate:", "[FAIL] blocked" if failed else "[PASS] all opted-in ledgers clean", "===")
    if failed:
        print("Run `python tools/dr/dr_gate_precommit.py --all --verbose` locally, fix, then re-commit.")
        print("(To bypass once: git commit --no-verify.)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
