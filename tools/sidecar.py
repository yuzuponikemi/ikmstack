#!/usr/bin/env python3
"""sidecar.py — 記録の書き先を文脈から解決する（3層運用のサイドカー経路）。

判定：
  - cwd が登録 notebook（~/.ikmstack/notebook）配下   → mode=notebook（logs/ へ）
  - それ以外（プロダクト repo など）                  → mode=sidecar
      記録は notebook 内 sidecar/<slug>/logs/ に集約する。
      プロダクト repo は一切汚さない。

slug は cwd の git remote(origin) を正規化して作る（SSH/HTTPS は同一キーに畳む）。

依存なし（標準ライブラリのみ）。使い方:
  python3 tools/sidecar.py resolve [--cwd DIR]   # JSON で mode/slug/logs_dir 等
  python3 tools/sidecar.py ensure  [--cwd DIR]   # 書き先を用意し logs_dir を print
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

STATE_NOTEBOOK = Path.home() / ".ikmstack" / "notebook"


def read_registered_notebook() -> Path | None:
    try:
        p = STATE_NOTEBOOK.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not p:
        return None
    try:
        return Path(p).resolve()
    except OSError:
        return Path(p)


def git_remote_url(cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    url = out.stdout.strip()
    return url or None


def git_toplevel(cwd: Path) -> Path | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    top = out.stdout.strip()
    return Path(top) if top else None


def slugify_remote(url: str) -> str:
    """git remote URL → `owner-repo`（SSH/HTTPS 畳み込み、小文字、安全文字のみ）。"""
    s = url.strip()
    s = re.sub(r"\.git$", "", s)
    # scp 形式 git@host:owner/repo / https://host/owner/repo / ssh://host/owner/repo
    s = re.sub(r"^[a-zA-Z0-9._-]+@", "", s)          # user@ を除去
    s = re.sub(r"^[a-zA-Z]+://", "", s)              # scheme を除去
    s = s.split(":", 1)[-1] if ":" in s and "/" not in s.split(":", 1)[0] else s
    # host を落として owner/repo（末尾2要素）に寄せる
    parts = [p for p in re.split(r"[/:]", s) if p]
    tail = parts[-2:] if len(parts) >= 2 else parts
    slug = "-".join(tail).lower()
    slug = re.sub(r"[^a-z0-9._-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "unknown"


def slug_for(cwd: Path) -> tuple[str, str | None]:
    """(slug, remote_url|None)。remote 無しは toplevel/cwd 名にフォールバック。"""
    url = git_remote_url(cwd)
    if url:
        return slugify_remote(url), url
    top = git_toplevel(cwd) or cwd
    name = re.sub(r"[^a-z0-9._-]", "-", top.name.lower()).strip("-")
    return (name or "unknown"), None


def is_inside(child: Path, parent: Path) -> bool:
    try:
        child = child.resolve()
        parent = parent.resolve()
    except OSError:
        pass
    return child == parent or parent in child.parents


def resolve(cwd: Path) -> dict:
    notebook = read_registered_notebook()
    if notebook is None:
        return {
            "error": "notebook 未登録。ikmstack で `./setup --notebook <dir>` を実行してください。",
        }
    year = str(date.today().year)
    if is_inside(cwd, notebook):
        logs_dir = notebook / "logs" / year
        return {
            "mode": "notebook",
            "notebook": str(notebook),
            "slug": None,
            "remote": None,
            "sidecar_dir": None,
            "logs_dir": str(logs_dir),
        }
    slug, remote = slug_for(cwd)
    sidecar_dir = notebook / "sidecar" / slug
    return {
        "mode": "sidecar",
        "notebook": str(notebook),
        "slug": slug,
        "remote": remote,
        "sidecar_dir": str(sidecar_dir),
        "logs_dir": str(sidecar_dir / "logs" / year),
    }


def ensure(cwd: Path) -> dict:
    """書き先ディレクトリを用意（sidecar なら README も）。logs_dir を返す。"""
    info = resolve(cwd)
    if info.get("error"):
        return info
    Path(info["logs_dir"]).mkdir(parents=True, exist_ok=True)
    if info["mode"] == "sidecar":
        readme = Path(info["sidecar_dir"]) / "README.md"
        if not readme.exists():
            remote = info["remote"] or "(git remote 無し)"
            readme.write_text(
                f"# sidecar: {info['slug']}\n\n"
                f"プロダクト repo での作業記録をサイドカー集約したもの。\n\n"
                f"- **project**: `{info['slug']}`\n"
                f"- **remote**: {remote}\n"
                f"- 記録は `logs/<YYYY>/<date>_<topic>.md`（`/lab-log` が書く）。\n"
                f"- このディレクトリは記録層(ikmnote)の一部。プロダクト repo は汚さない。\n",
                encoding="utf-8",
            )
    return info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="記録の書き先を文脈から解決する")
    ap.add_argument("command", choices=["resolve", "ensure"])
    ap.add_argument("--cwd", default=None, help="判定する作業ディレクトリ（既定: $PWD）")
    args = ap.parse_args(argv)
    cwd = Path(args.cwd) if args.cwd else Path(os.getcwd())

    info = ensure(cwd) if args.command == "ensure" else resolve(cwd)
    if info.get("error"):
        print(info["error"], file=sys.stderr)
        return 2
    if args.command == "ensure":
        print(info["logs_dir"])          # skill はこの1行を使う
    else:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
