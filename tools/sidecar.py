#!/usr/bin/env python3
"""sidecar.py — 記録の書き先を文脈から解決する（3層運用のサイドカー経路）。

## 解決の2軸

**scope（記録の種類）** — 何を書くかで行き先が変わる:
  - `log`(既定)  … 日次ログ。セッション/リポジトリに紐づく記録
  - `experiment` … 実験一式（experiments/E###_*）。**常にノート根**に作る。
      実験は本質的に cross-repo（MANIFEST に複数 repo の SHA を書く）なので
      sidecar/<slug>/ に閉じ込めない。関与 repo は MANIFEST 側で表現する。

**mode（今どこにいるか）** — cwd がどの層かの分類:
  - cwd が登録 notebook 配下  → mode=notebook（ログは <nb>/logs/ へ）
  - それ以外（プロダクト repo）→ mode=sidecar（ログは <nb>/sidecar/<slug>/logs/ へ）
      プロダクト repo は一切汚さない。slug は git remote(origin) を正規化して作る
      （SSH/HTTPS は同一キーに畳む）。

## 複数 notebook

`~/.ikmstack/notebooks` に配線済み notebook を1行1パスで保持する（wire 順）。
`~/.ikmstack/notebook` は **既定 notebook**（最後に wire したもの）。解決順は:

  1. `--notebook <path>` / 環境変数 `IKMSTACK_NOTEBOOK`（パス or basename）
  2. cwd を含む登録 notebook（入れ子なら最も深いもの）→ mode=notebook
  3. 既定 notebook → mode=sidecar

依存なし（標準ライブラリのみ）。使い方:
  python3 tools/sidecar.py ensure                  # 書き先 logs ディレクトリを用意し print
  python3 tools/sidecar.py ensure --scope experiment  # ノート根を用意し print（skill は cd する）
  python3 tools/sidecar.py notebook                # 解決した notebook 根だけを print
  python3 tools/sidecar.py resolve [--scope ...]   # JSON で全項目
  python3 tools/sidecar.py recent [--limit N]      # この repo の過去記録を新しい順に提示
  python3 tools/sidecar.py list                    # 登録 notebook 一覧（既定に * 印）
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

STATE_DIR = Path.home() / ".ikmstack"
STATE_NOTEBOOK = STATE_DIR / "notebook"        # 既定 notebook（単数・後方互換）
STATE_NOTEBOOKS = STATE_DIR / "notebooks"      # 登録一覧（複数対応）

SCOPES = ("log", "experiment")


def _resolved(p: str | Path) -> Path:
    try:
        return Path(p).resolve()
    except OSError:
        return Path(p)


def read_default_notebook() -> Path | None:
    """既定 notebook（sidecar の集約先）。"""
    try:
        p = STATE_NOTEBOOK.read_text(encoding="utf-8").strip()
    except OSError:
        p = ""
    if p:
        return _resolved(p)
    # 単数ファイルが無ければ一覧の先頭にフォールバック
    nbs = read_notebooks()
    return nbs[0] if nbs else None


def read_notebooks() -> list[Path]:
    """登録済み notebook の一覧（wire 順、重複除去、既定も必ず含む）。"""
    out: list[Path] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            return
        p = _resolved(raw)
        if str(p) not in seen:
            seen.add(str(p))
            out.append(p)

    try:
        for line in STATE_NOTEBOOKS.read_text(encoding="utf-8").splitlines():
            add(line)
    except OSError:
        pass
    try:
        add(STATE_NOTEBOOK.read_text(encoding="utf-8"))
    except OSError:
        pass
    return out


def register_notebook(nb: Path) -> None:
    """notebook を一覧に追加し、既定にする（setup から呼ばれる想定）。"""
    nb = _resolved(nb)
    nbs = [p for p in read_notebooks() if p != nb]
    nbs.append(nb)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_NOTEBOOKS.write_text("".join(f"{p}\n" for p in nbs), encoding="utf-8")
    STATE_NOTEBOOK.write_text(f"{nb}\n", encoding="utf-8")


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
    child, parent = _resolved(child), _resolved(parent)
    return child == parent or parent in child.parents


def pick_notebook(cwd: Path, override: str | None = None) -> tuple[Path | None, str]:
    """(notebook, mode)。mode は cwd 基準の分類（notebook/sidecar）。"""
    notebooks = read_notebooks()
    override = override or os.environ.get("IKMSTACK_NOTEBOOK") or None
    if override:
        cand = _resolved(override)
        match = next(
            (p for p in notebooks if p == cand or p.name == override),
            cand if cand.is_dir() else None,
        )
        if match is None:
            return None, "sidecar"
        return match, ("notebook" if is_inside(cwd, match) else "sidecar")

    # cwd を含む登録 notebook（入れ子なら最も深いものを採る）
    containing = [p for p in notebooks if is_inside(cwd, p)]
    if containing:
        return max(containing, key=lambda p: len(str(p))), "notebook"
    return read_default_notebook(), "sidecar"


def resolve(cwd: Path, scope: str = "log", override: str | None = None) -> dict:
    if scope not in SCOPES:
        return {"error": f"未知の scope: {scope}（{'/'.join(SCOPES)} のいずれか）"}
    notebook, mode = pick_notebook(cwd, override)
    if notebook is None:
        return {
            "error": "notebook 未登録。ikmstack で `./setup --notebook <dir>` を実行してください。",
        }
    if not notebook.is_dir():
        return {
            "error": f"登録された notebook が見つかりません: {notebook}"
                     "（`./setup --notebook <dir>` で配線し直してください）",
        }

    year = str(date.today().year)
    slug, remote, sidecar_dir = None, None, None
    if mode == "sidecar":
        slug, remote = slug_for(cwd)
        sidecar_dir = notebook / "sidecar" / slug
        logs_dir = sidecar_dir / "logs" / year
    else:
        logs_dir = notebook / "logs" / year

    experiments_dir = notebook / "experiments"
    info = {
        "mode": mode,
        "scope": scope,
        "notebook": str(notebook),
        "notebooks": [str(p) for p in read_notebooks()],
        "slug": slug,
        "remote": remote,
        "sidecar_dir": str(sidecar_dir) if sidecar_dir else None,
        "logs_dir": str(logs_dir),
        "experiments_dir": str(experiments_dir),
        # skill が cd する場所。相対の tools/ ・ experiments/ はここから解決する
        "workdir": str(notebook),
    }
    # scope ごとの最終的な書き先
    info["target_dir"] = str(logs_dir) if scope == "log" else str(experiments_dir)
    return info


def ensure(cwd: Path, scope: str = "log", override: str | None = None) -> dict:
    """書き先ディレクトリを用意（sidecar なら README も）。"""
    info = resolve(cwd, scope, override)
    if info.get("error"):
        return info
    Path(info["target_dir"]).mkdir(parents=True, exist_ok=True)
    if info["mode"] == "sidecar" and info["sidecar_dir"]:
        Path(info["sidecar_dir"]).mkdir(parents=True, exist_ok=True)
        readme = Path(info["sidecar_dir"]) / "README.md"
        if not readme.exists():
            remote = info["remote"] or "(git remote 無し)"
            readme.write_text(
                f"# sidecar: {info['slug']}\n\n"
                f"プロダクト repo での作業記録をサイドカー集約したもの。\n\n"
                f"- **project**: `{info['slug']}`\n"
                f"- **remote**: {remote}\n"
                f"- 記録は `logs/<YYYY>/<date>_<topic>.md`（`/lab-log` が書く）。\n"
                f"- このディレクトリは記録層の一部。プロダクト repo は汚さない。\n"
                f"- 実験一式（`experiments/E###_*`）はここではなく**ノート根**に作る\n"
                f"  （実験は cross-repo。関与 repo は MANIFEST.md に書く）。\n",
                encoding="utf-8",
            )
    return info


def recent(cwd: Path, limit: int = 10, override: str | None = None) -> dict:
    """この文脈に紐づく過去の記録を新しい順に返す（resurfacing）。"""
    info = resolve(cwd, "log", override)
    if info.get("error"):
        return info
    root = Path(info["sidecar_dir"]) if info["mode"] == "sidecar" else Path(info["notebook"])
    logs_root = root / "logs"
    files = sorted(
        (p for p in logs_root.glob("*/*.md") if p.is_file()),
        key=lambda p: p.name,
        reverse=True,
    )
    info["logs_root"] = str(logs_root)
    info["recent"] = [
        {"path": str(p), "name": p.name, "date": p.name[:10]}
        for p in files[:limit]
    ]
    info["total"] = len(files)
    # 実験は常にノート根。関連の拾い方は mode で変える。
    #   sidecar  … その repo に言及する実験（MANIFEST 本文を slug で照合）
    #   notebook … 直近に触った実験（notebook 内には slug が無いため照合できない。
    #              ここを空で返すと、実験が実在する唯一の場所で resurfacing が死ぬ）
    exp_root = Path(info["experiments_dir"])
    prefix = _experiment_prefix(Path(info["notebook"]))
    manifests = sorted(exp_root.glob(f"{prefix}*/MANIFEST.md"))
    exps: list[str] = []
    if info["slug"]:
        needle = info["slug"].split("-")[-1]
        for man in manifests:
            try:
                text = man.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if needle in text:
                exps.append(man.parent.name)
        exps.sort()
    else:
        by_mtime = sorted(manifests, key=lambda p: _exp_mtime(p.parent), reverse=True)
        exps = [p.parent.name for p in by_mtime[:limit]]
    info["related_experiments"] = exps
    return info


def _experiment_prefix(notebook: Path) -> str:
    """実験ディレクトリの接頭辞を .lab-config.json から読む（既定 "E"）。

    ここをリテラルで固定すると、接頭辞の違うノートで実験が 1 件も拾われず、
    しかも「関連なし」と静かに出るだけなので気づけない。
    """
    try:
        cfg = json.loads((notebook / ".lab-config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "E"
    return str(cfg.get("experiment_id_prefix") or "E")


def _exp_mtime(exp_dir: Path) -> float:
    """実験の「最後に触った時刻」。**md ファイルだけ**を見る（全走査はしない）。

    ディレクトリ自身の mtime は使わない。`_generated/` を作り直しただけで親ディレクトリの
    mtime が進むので、「図を再生成した」が「実験を進めた」と同じ重みになり、
    本当に作業した実験が押し出される（実測で踏んだ）。
    """
    times = []
    for pat in ("*.md", "reports/*.md"):
        for p in exp_dir.glob(pat):
            try:
                times.append(p.stat().st_mtime)
            except OSError:
                continue
    if times:
        return max(times)
    try:
        return exp_dir.stat().st_mtime
    except OSError:
        return 0.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="記録の書き先を文脈から解決する")
    ap.add_argument("command", choices=["resolve", "ensure", "notebook", "recent", "list"])
    ap.add_argument("--cwd", default=None, help="判定する作業ディレクトリ（既定: $PWD）")
    ap.add_argument("--scope", default="log", choices=SCOPES,
                    help="記録の種類（log=日次ログ / experiment=実験一式。既定: log）")
    ap.add_argument("--notebook", default=None,
                    help="使う notebook を明示（パス or 登録名。既定: 環境変数 IKMSTACK_NOTEBOOK → 自動判定）")
    ap.add_argument("--limit", type=int, default=10, help="recent の件数（既定: 10）")
    args = ap.parse_args(argv)
    cwd = Path(args.cwd) if args.cwd else Path(os.getcwd())

    if args.command == "list":
        nbs = read_notebooks()
        if not nbs:
            print("notebook 未登録。ikmstack で `./setup --notebook <dir>` を実行してください。",
                  file=sys.stderr)
            return 2
        default = read_default_notebook()
        for p in nbs:
            mark = "*" if p == default else " "
            state = "" if p.is_dir() else "  ✗ 存在しない"
            print(f"{mark} {p}{state}")
        return 0

    if args.command == "recent":
        info = recent(cwd, args.limit, args.notebook)
    elif args.command == "ensure":
        info = ensure(cwd, args.scope, args.notebook)
    else:
        info = resolve(cwd, args.scope, args.notebook)

    if info.get("error"):
        print(info["error"], file=sys.stderr)
        return 2

    if args.command == "ensure":
        print(info["target_dir"])        # skill はこの1行を使う
    elif args.command == "notebook":
        print(info["notebook"])
    else:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
