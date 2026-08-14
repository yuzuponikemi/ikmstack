#!/usr/bin/env python3
"""Policy drift gate: keep harness policy copies in sync with canonicals.

The harness source (AGENTS.md, README.md, .claude/skills/*/SKILL.md,
docs/conventions/*.md) restates the same rules in several places. This gate
enforces the double-entry discipline for those restatements:

    machine truth : docs/conventions/policy-registry.json (hand-edited)
    human view    : docs/conventions/policy-map.md        (generated, --write-map)
    gate          : this script                            (pre-commit step 4)

Each registry rule names ONE canonical location, its operational key_lines,
and the registered copies. Copies carry a pin comment in the markdown:

    <!-- policy:<rule-id>@<digest8> -->

where digest8 = sha256("\\n".join(key_lines))[:8]. Changing a rule's operational
content changes the digest, which makes every copy's pin stale -> the gate
lists them all until each copy is reviewed and re-pinned (forced propagation).
Prose-only rewording keeps the digest unchanged -> no false positives.

Checks:
    C1 canonical : canonical file exists and contains every key_line
    C2 copy-ref  : every registered copy carries a pin for the rule
    C3 no-rogue  : key_lines appear nowhere on the surface outside
                   canonical/copies/allow (unregistered restatement)
    C4 pin-fresh : every pin's digest matches the registry
    C5 view-sync : policy-map.md generated section matches the registry

Matching strips ALL whitespace from haystack and needles, so wrapped lines and
Japanese text match regardless of layout. key_lines must therefore be
operational strings (commands, paths, fixed phrases) -- never prose.

Opt-in / safe-by-construction: if the registry file does not exist the gate is
a no-op (rc 0). Default mode additionally skips unless a STAGED file is on the
surface (or is the registry/map), so ordinary experiment commits pay nothing.

Usage:
    python tools/policy_gate.py               # staged-scoped check (pre-commit)
    python tools/policy_gate.py --all         # full check regardless of staging
    python tools/policy_gate.py --write-map   # regenerate policy-map.md
    python tools/policy_gate.py --digest <id> # print a rule's current digest8
    python tools/policy_gate.py --selftest    # verify C1..C5 detect synthetic drift
    python tools/policy_gate.py --verbose     # per-rule detail even on PASS

Exit codes: 0 = PASS (or nothing to gate) / 1 = FAIL / 2 = usage/config error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Force UTF-8 so Japanese output does not crash on Windows consoles (cp1252).
# Same gotcha as tools/dr/dr_gate_precommit.py.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - older/odd streams: best effort
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_REL = "docs/conventions/policy-registry.json"
MAP_REL = "docs/conventions/policy-map.md"
MAP_MARK_START = "<!-- gen:policy-map:start -->"
MAP_MARK_END = "<!-- gen:policy-map:end -->"
PIN_RE_TMPL = r"policy:{rid}@([0-9a-f]{{8}})"

MAP_PREAMBLE = """# ポリシーマップ(1ルール=1正本)

ハーネスの規約がどこを正本とし、どのファイルが写し(ピン付き)かの対応表。

> **この表は手で編集しない。** 正本は [policy-registry.json](policy-registry.json)、
> 表は `python tools/policy_gate.py --write-map` が生成する(マーカ間のみ書き換わる)。
> 同期は pre-commit の policy_gate が検証する。

"""


def _norm(text: str) -> str:
    """Strip ALL whitespace. Wrapped/indented restatements match regardless of layout."""
    return re.sub(r"\s+", "", text)


def _digest8(rule: dict) -> str:
    joined = "\n".join(rule.get("key_lines", []))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:8]


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"[config] cannot read {path}: {exc}")
        return None


def _load_registry(root: Path) -> dict | None:
    """None = not opted in (no registry). Raises SystemExit(2) on broken JSON."""
    reg_path = root / REGISTRY_REL
    if not reg_path.is_file():
        return None
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"[config] {REGISTRY_REL} is not valid JSON: {exc}")
        raise SystemExit(2) from exc
    if not isinstance(reg.get("rules"), list) or not isinstance(reg.get("surface"), list):
        print(f"[config] {REGISTRY_REL} must have 'surface' (list) and 'rules' (list)")
        raise SystemExit(2)
    return reg


def _surface_files(root: Path, patterns: list[str]) -> list[Path]:
    files: dict[str, Path] = {}
    for pat in patterns:
        for p in sorted(root.glob(pat)):
            if p.is_file():
                files[p.as_posix()] = p
    return list(files.values())


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


class Finding:
    def __init__(self, check: str, rule_id: str, message: str):
        self.check = check
        self.rule_id = rule_id
        self.message = message

    def __str__(self) -> str:
        return f"  [{self.check}] {self.rule_id}: {self.message}"


def run_checks(root: Path, reg: dict, verbose: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    surface = _surface_files(root, reg["surface"])
    texts: dict[str, str] = {}
    norms: dict[str, str] = {}
    for p in surface:
        t = _read(p)
        if t is None:
            continue
        rel = _rel(root, p)
        texts[rel] = t
        norms[rel] = _norm(t)

    for rule in reg["rules"]:
        rid = rule.get("id", "<no-id>")
        digest = _digest8(rule)
        keys = rule.get("key_lines", [])
        canon_rel = rule.get("canonical", {}).get("file", "")
        copy_rels = [c.get("file", "") for c in rule.get("copies", [])]
        allow_rels = set(rule.get("allow", []))
        pin_re = re.compile(PIN_RE_TMPL.format(rid=re.escape(rid)))

        # C1: canonical exists and contains every key_line
        canon_text = texts.get(canon_rel)
        if canon_text is None:
            canon_path = root / canon_rel
            canon_text = _read(canon_path)  # canonical may sit outside surface globs
            if canon_text is not None:
                norms[canon_rel] = _norm(canon_text)
        if canon_text is None:
            findings.append(Finding("C1", rid, f"canonical file missing: {canon_rel}"))
        else:
            canon_norm = norms[canon_rel]
            for key in keys:
                if _norm(key) not in canon_norm:
                    findings.append(Finding(
                        "C1", rid,
                        f"canonical {canon_rel} lacks key line: {key!r}"))

        # C2 + C4: every copy exists, carries the pin, and the pin is fresh
        for copy_rel in copy_rels:
            copy_text = texts.get(copy_rel)
            if copy_text is None:
                findings.append(Finding("C2", rid, f"copy file missing/off-surface: {copy_rel}"))
                continue
            pins = pin_re.findall(copy_text)
            if not pins:
                findings.append(Finding(
                    "C2", rid,
                    f"{copy_rel} has no pin <!-- policy:{rid}@{digest} -->"))
                continue
            for got in pins:
                if got != digest:
                    findings.append(Finding(
                        "C4", rid,
                        f"{copy_rel} pin stale: @{got} (registry says @{digest}) "
                        f"-- review the copy text, then update the pin"))

        # C3: key_lines must not appear outside canonical/copies/allow.
        # The generated map is structurally exempt: it quotes key strings by
        # construction and C5 already verifies it against the registry.
        exempt = {canon_rel, *copy_rels, *allow_rels, MAP_REL}
        for rel, ntext in norms.items():
            if rel in exempt:
                continue
            for key in keys:
                if _norm(key) in ntext:
                    findings.append(Finding(
                        "C3", rid,
                        f"unregistered restatement in {rel} (contains {key!r}) "
                        f"-- register as copy+pin, or move the text, or add to 'allow'"))
                    break

    # C5: generated map section matches the registry
    map_text = _read(root / MAP_REL)
    expected = render_map_section(reg)
    if map_text is None:
        findings.append(Finding("C5", "policy-map", f"{MAP_REL} missing -- run --write-map"))
    else:
        current = _extract_section(map_text)
        if current is None:
            findings.append(Finding(
                "C5", "policy-map",
                f"{MAP_REL} lacks gen markers {MAP_MARK_START} .. {MAP_MARK_END}"))
        elif current.strip() != expected.strip():
            findings.append(Finding(
                "C5", "policy-map",
                f"{MAP_REL} out of date -- run --write-map"))

    if verbose:
        print(f"surface: {len(norms)} files, rules: {len(reg['rules'])}")
    return findings


def _extract_section(map_text: str) -> str | None:
    try:
        start = map_text.index(MAP_MARK_START) + len(MAP_MARK_START)
        end = map_text.index(MAP_MARK_END)
    except ValueError:
        return None
    return map_text[start:end]


def render_map_section(reg: dict) -> str:
    lines = [
        "",
        "| rule id | ルール | 正本 | 写し(ピン付き) | digest |",
        "|---|---|---|---|---|",
    ]
    for rule in reg["rules"]:
        canon = rule.get("canonical", {})
        anchor = canon.get("anchor")
        canon_s = canon.get("file", "?") + (f"「{anchor}」" if anchor else "")
        copies = "<br>".join(c.get("file", "?") for c in rule.get("copies", [])) or "—"
        enforced = rule.get("enforced_by")
        title = rule.get("title", "")
        if enforced:
            title += f"(実行時強制: {enforced})"
        lines.append(
            f"| `{rule.get('id', '?')}` | {title} | {canon_s} | {copies} | `@{_digest8(rule)}` |")
    lines.append("")
    return "\n".join(lines)


def write_map(root: Path, reg: dict) -> Path:
    map_path = root / MAP_REL
    section = MAP_MARK_START + "\n" + render_map_section(reg) + "\n" + MAP_MARK_END
    old = _read(map_path)
    if old is not None and MAP_MARK_START in old and MAP_MARK_END in old:
        pre = old[: old.index(MAP_MARK_START)]
        post = old[old.index(MAP_MARK_END) + len(MAP_MARK_END):]
        new = pre + section + post
    else:
        new = MAP_PREAMBLE + section + "\n"
    # Path.write_text() gained `newline` in 3.10; setup-runbook §0 promises 3.9+.
    with map_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(new)
    return map_path


def _staged_paths(root: Path) -> list[str] | None:
    """Staged repo-relative paths, or None if git is unavailable."""
    proc = subprocess.run(
        # -c core.quotepath=false: git otherwise escapes non-ASCII paths, and this
        # repo has many Japanese report filenames. encoding="utf-8" must go with it:
        # text=True alone decodes with the locale codepage and raw UTF-8 then fails.
        ["git", "-c", "core.quotepath=false", "diff", "--cached", "--name-only"],
        cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        return None
    return [ln.strip().replace("\\", "/") for ln in proc.stdout.splitlines() if ln.strip()]


def _staged_touches_surface(root: Path, reg: dict) -> bool:
    staged = _staged_paths(root)
    if staged is None:
        return True  # no git info -> be safe, run the check
    surface_rels = {_rel(root, p) for p in _surface_files(root, reg["surface"])}
    surface_rels.update({REGISTRY_REL, MAP_REL})
    return any(s in surface_rels for s in staged)


# ---------------------------------------------------------------- selftest --

def _selftest() -> int:
    """Build a synthetic mini-harness in a tempdir and verify each check fires."""
    failures: list[str] = []

    def expect(name: str, findings: list[Finding], *checks: str) -> None:
        got = sorted({f.check for f in findings})
        want = sorted(checks)
        if got != want:
            failures.append(f"{name}: expected {want}, got {got} "
                            f"({[str(f) for f in findings]})")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "docs/conventions").mkdir(parents=True)
        reg = {
            "version": 1,
            "surface": ["canon.md", "copy.md", "rogue.md"],
            "rules": [{
                "id": "test-rule",
                "title": "test",
                "canonical": {"file": "canon.md"},
                "key_lines": ["python tools/foo.py --bar"],
                "copies": [{"file": "copy.md"}],
            }],
        }
        digest = _digest8(reg["rules"][0])

        def reset(canon: str | None = None, copy: str | None = None,
                  rogue: str = "unrelated text") -> None:
            (root / "canon.md").write_text(
                canon if canon is not None
                else "Rule: run\n  python tools/foo.py\n  --bar\nend.",  # wrapped on purpose
                encoding="utf-8")
            (root / "copy.md").write_text(
                copy if copy is not None
                else f"run `python tools/foo.py --bar`\n<!-- policy:test-rule@{digest} -->\n",
                encoding="utf-8")
            (root / "rogue.md").write_text(rogue, encoding="utf-8")
            write_map(root, reg)

        reset()
        expect("clean baseline", run_checks(root, reg))

        reset(canon="the command was removed entirely")
        expect("C1 canonical lost key line", run_checks(root, reg), "C1")

        reset(copy="run `python tools/foo.py --bar` (pin forgotten)")
        expect("C2 copy without pin", run_checks(root, reg), "C2")

        reset(rogue="someone pasted python tools/foo.py --bar here")
        expect("C3 unregistered restatement", run_checks(root, reg), "C3")

        reset(copy=f"run `python tools/foo.py --bar`\n<!-- policy:test-rule@00000000 -->\n")
        expect("C4 stale pin", run_checks(root, reg), "C4")

        reset()
        map_path = root / MAP_REL
        map_path.write_text(
            map_path.read_text(encoding="utf-8").replace("@" + digest, "@deadbeef"),
            encoding="utf-8")
        expect("C5 stale map", run_checks(root, reg), "C5")

        # allow-list: rogue text is exempted
        reg_allow = json.loads(json.dumps(reg))
        reg_allow["rules"][0]["allow"] = ["rogue.md"]
        reset(rogue="allowed mention: python tools/foo.py --bar")
        write_map(root, reg_allow)
        expect("allow-list exemption", run_checks(root, reg_allow))

    if failures:
        print("[selftest] FAIL")
        for f in failures:
            print("  - " + f)
        return 1
    print("[selftest] PASS: C1..C5 + allow-list all behave as designed")
    return 0


# -------------------------------------------------------------------- main --

def main() -> int:
    ap = argparse.ArgumentParser(description="Policy drift gate")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true",
                      help="full check regardless of git staging")
    mode.add_argument("--write-map", action="store_true",
                      help=f"regenerate {MAP_REL} from the registry")
    mode.add_argument("--digest", metavar="RULE_ID",
                      help="print a rule's current digest8 (for updating pins)")
    mode.add_argument("--selftest", action="store_true",
                      help="verify the checks against synthetic drift fixtures")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    reg = _load_registry(REPO_ROOT)
    if reg is None:
        # Opt-in marker (the registry itself) is absent -> nothing to gate.
        if args.verbose:
            print(f"[skip] {REGISTRY_REL} not found (gate not opted in)")
        return 0

    if args.digest:
        for rule in reg["rules"]:
            if rule.get("id") == args.digest:
                print(_digest8(rule))
                return 0
        print(f"[config] no rule with id {args.digest!r} in {REGISTRY_REL}")
        return 2

    if args.write_map:
        path = write_map(REPO_ROOT, reg)
        print(f"wrote {path}")
        return 0

    if not args.all and not _staged_touches_surface(REPO_ROOT, reg):
        # Ordinary commit that doesn't touch the harness surface: zero cost.
        return 0

    findings = run_checks(REPO_ROOT, reg, verbose=args.verbose)
    if not findings:
        print("policy gate: PASS (registry, copies and map are in sync)")
        return 0

    print("policy gate: FAIL — harness policy drift detected")
    for f in findings:
        print(f)
    print()
    print("fix guide:")
    print("  C1: restore the key line in the canonical, or update key_lines in the registry")
    print("  C2: add the pin  <!-- policy:<id>@<digest> -->  to the copy"
          " (digest: python tools/policy_gate.py --digest <id>)")
    print("  C3: register the file as a copy (with pin), move the text to the canonical,"
          " or add it to the rule's 'allow' list")
    print("  C4: review the copy against the canonical, then update the pin digest")
    print("  C5: python tools/policy_gate.py --write-map")
    return 1


if __name__ == "__main__":
    sys.exit(main())
