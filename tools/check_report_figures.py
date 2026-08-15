#!/usr/bin/env python3
"""check_report_figures.py — レポートの図リンクが「再生成出力先」を指すか検証(依存なし)

三大原則#1 の運用を強制する静的リンタ。図そのものは git に入れず、各実験の
`regenerate.sh` が gitignored の出力ディレクトリに再生成する。レポートの図リンクは
**その出力先だけ**を指していなければ、誰かが clone + regen してもプレビューで画像が
出ない。

このリンタは データを必要としない(ファイルの実在は見ない)。図リンクの相対パスを
解決し、実験ルートから見た先頭セグメントが許容出力ルートのどれかであることだけを見る。

検査対象
--------
  experiments/<id>/REPORT.md
  experiments/<id>/reports/**/*.md        (archive 含む)

図リンク = markdown 画像/リンクのうち拡張子が下記のローカルパス(http(s)/anchor は対象外):
  .png .jpg .jpeg .gif .svg .webp
"""
from __future__ import annotations

import argparse
import re
import sys
import json
from pathlib import PurePosixPath
from pathlib import Path

# デフォルトで許容される出力ルート
ALLOWED_ROOTS = {"figures", "_generated", "loadeval_cli"}

# 既知の未対応実験の警告リスト
BACKLOG = set()

FIG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def load_config(workspace_root: Path) -> dict:
    config_file = workspace_root / ".lab-config.json"
    defaults = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                defaults.update(user_config)
        except Exception as e:
            print(f"Warning: Failed to load config in check_report_figures: {e}", file=sys.stderr)
    return defaults


def iter_report_md(exp: Path):
    top = exp / "REPORT.md"
    if top.exists():
        yield top
    reports = exp / "reports"
    if reports.is_dir():
        yield from sorted(reports.rglob("*.md"))


def figure_targets(md_path: Path):
    out = []
    for lineno, line in enumerate(md_path.read_text(encoding="utf-8").splitlines(), 1):
        for m in LINK_RE.finditer(line):
            target = m.group(1).strip()
            target = target.split()[0] if target else target
            if not target or target.startswith(("http://", "https://", "#", "<")):
                continue
            clean = target.split("#", 1)[0].split("?", 1)[0]
            if PurePosixPath(clean.replace("\\", "/")).suffix.lower() in FIG_EXT:
                out.append((clean, lineno))
    return out


def check_experiment(exp: Path, allowed_roots: set[str]):
    violations = []
    for md in iter_report_md(exp):
        for target, lineno in figure_targets(md):
            resolved = (md.parent / target).resolve()
            try:
                rel = resolved.relative_to(exp.resolve())
            except ValueError:
                violations.append(
                    (md, lineno, target, "実験ディレクトリの外を指している")
                )
                continue
            first = rel.parts[0] if rel.parts else ""
            if first not in allowed_roots:
                violations.append(
                    (
                        md,
                        lineno,
                        target,
                        f"出力先 {sorted(allowed_roots)} の外(解決先: {rel.as_posix()})",
                    )
                )
    return violations


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("experiments", nargs="?", help="experiments/ ディレクトリ(既定: リポジトリ内)")
    ap.add_argument("--check", action="store_true", help="検証のみ(違反があれば exit 1)")
    args = ap.parse_args(argv)

    if args.experiments:
        exp_dir = Path(args.experiments)
    else:
        # install モデルでは tools/ が harness への symlink のことがある。__file__ を
        # resolve() すると harness 側に張り付くので、cwd(=作業リポジトリ)基準で解決する。
        exp_dir = Path.cwd() / "experiments"
    if not exp_dir.is_dir():
        print(f"experiments ディレクトリが見つからない: {exp_dir}", file=sys.stderr)
        return 2

    # Load configuration
    workspace_root = exp_dir.parent
    config = load_config(workspace_root)
    allowed_roots = set(config.get("allowed_figure_roots", ALLOWED_ROOTS))

    blocking = []
    backlog = []
    for exp in sorted(exp_dir.glob("*/")):
        if exp.name.startswith("_") or exp.name.startswith("."):
            continue
        (backlog if exp.name in BACKLOG else blocking).extend(check_experiment(exp, allowed_roots))

    if backlog:
        print(f"NOTE: バックログ実験の図リンク違反 {len(backlog)} 件(警告のみ・要是正):")
        for md, lineno, target, _reason in backlog:
            print(f"    {md}:{lineno}  ![..]({target})")
        print()

    if blocking:
        print("✗ 図リンクが再生成出力先を指していません(clone + regen で画像が出ません):\n")
        for md, lineno, target, reason in blocking:
            print(f"  {md}:{lineno}")
            print(f"      ![..]({target})  → {reason}")
        print(
            f"\n計 {len(blocking)} 件。図リンクは "
            f"{sorted(allowed_roots)} 配下(.gitignore 済の再生成出力先)を指すこと。"
        )
        return 1

    print("✓ 全レポートの図リンクが再生成出力先を指しています(バックログ実験を除く)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
