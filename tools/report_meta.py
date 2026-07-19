#!/usr/bin/env python3
"""report_meta.py — experiment / report metadata からの INDEX 生成・検証(依存なし)

レポートの YAML フロントマターを唯一の正本(single source of truth)として扱い、
ステータス・要約の二重持ち(report 本体と INDEX)を解消する。

扱う2階層:

  experiments/INDEX.md           ← 各 experiments/<id>/REPORT.md のフロントマターから生成
  experiments/<id>/reports/INDEX.md ← その配下 reports/[ID]_*.md のフロントマターから生成

INDEX の表は次のマーカ間だけを書き換える(凡例・散文は手編集のまま残る):

  <!-- gen:experiments-index:start -->
  ...table...
  <!-- gen:experiments-index:end -->

  <!-- gen:reports-index:start -->
  ...table...
  <!-- gen:reports-index:end -->

使い方
------
  python tools/report_meta.py            # 全 INDEX を生成(書き換え)
  python tools/report_meta.py --check    # 検証のみ(差分/不備があれば exit 1)
  python tools/report_meta.py <experiments dir>  # 既定: リポジトリの experiments/
"""
from __future__ import annotations

import argparse
import sys
import json
import re
from pathlib import Path

# --- ステータス トークン → バッジ -------------------------------------------
EXPERIMENT_STATUS = {
    "planning": "📋",
    "active": "🔄",
    "done": "✅",
    "paused": "⚪",
}
REPORT_STATUS = {
    "active": "🟢",
    "superseded": "🟡",
    "historical": "⚪",
    "planning": "📋",
}


class MetaError(Exception):
    pass


# --- コンフィグロード --------------------------------------------------------
def load_config(workspace_root: Path) -> dict:
    config_file = workspace_root / ".lab-config.json"
    defaults = {
        "experiment_id_pattern": r"^(E|FL)\d+_[a-z0-9-]+$",
        "experiment_id_prefix": "E",
        "jira_enabled": False,
        "jira_base_url": "https://atlassian.net/browse/",
        "jira_project_key": "PROJ",
        "google_drive_root": "",
        "allowed_figure_roots": ["_generated", "figures"]
    }
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                defaults.update(user_config)
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}", file=sys.stderr)
    return defaults


# --- 最小フロントマター パーサ ----------------------------------------------
def parse_frontmatter(path: Path) -> dict | None:
    """ファイル先頭の `---` ブロックを dict で返す。無ければ None。"""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    # 終端 `---` を探す
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise MetaError(f"{path}: フロントマターの終端 '---' が無い")

    data: dict = {}
    i = 1
    cur_key = None
    while i < end:
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line.startswith((" ", "\t")) and line.lstrip().startswith("- "):
            if cur_key is None:
                raise MetaError(f"{path}:{i+1}: リスト要素にキーが無い: {line!r}")
            data.setdefault(cur_key, [])
            if not isinstance(data[cur_key], list):
                raise MetaError(f"{path}:{i+1}: {cur_key} がスカラとリストで混在")
            data[cur_key].append(line.lstrip()[2:].strip())
            i += 1
            continue
        if ":" not in line:
            raise MetaError(f"{path}:{i+1}: 'key: value' 形式でない: {line!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # 行末インラインコメントを除去(YAML 準拠: '#' の前は空白必須)。テンプレは
        # `status: planning  # planning | active | ...` のような注釈付きで配布されるため、
        # これを剥がして値だけを得る。クオート値は対象外(値中の '#' を残したい時はクオート)。
        if value[:1] not in ('"', "'"):
            if value.startswith("#"):
                value = ""
            else:
                _ci = value.find(" #")
                if _ci != -1:
                    value = value[:_ci].rstrip()
        cur_key = key
        if value == "":
            data[key] = None
        else:
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                data[key] = [v.strip() for v in inner.split(",")] if inner else []
            else:
                data[key] = value
        i += 1
    return data


def require(meta: dict, keys: list[str], path: Path) -> None:
    missing = [k for k in keys if not meta.get(k)]
    if missing:
        raise MetaError(f"{path}: 必須フロントマター欠落: {', '.join(missing)}")


# --- 表の組み立て ------------------------------------------------------------
def fmt_period(meta: dict) -> str:
    start = meta.get("period_start") or ""
    end = meta.get("period_end") or ""
    if start and end:
        return f"{start}〜{end}"
    if start:
        return f"{start}〜"
    return ""


def build_experiments_table(exp_dir: Path, config: dict) -> tuple[list[str], list[str]]:
    """(table_lines, warnings) を返す。"""
    rows = []
    warnings = []
    jira_enabled = config.get("jira_enabled", False)

    for report in sorted(exp_dir.glob("*/REPORT.md")):
        if report.parent.name.startswith("_"):
            continue  # _template など雛形は対象外
        meta = parse_frontmatter(report)
        if meta is None:
            warnings.append(f"フロントマター無し(experiments/INDEX 未反映): {report}")
            continue

        required_keys = ["experiment_id", "status", "summary"]
        if jira_enabled:
            required_keys.append("jira")
        require(meta, required_keys, report)

        status = meta["status"]
        if status not in EXPERIMENT_STATUS:
            raise MetaError(
                f"{report}: status='{status}' は不正。許容: {list(EXPERIMENT_STATUS)}"
            )
        eid = meta["experiment_id"]
        if eid != report.parent.name:
            raise MetaError(
                f"{report}: experiment_id='{eid}' がディレクトリ名 '{report.parent.name}' と不一致"
            )

        eid_pattern = config.get("experiment_id_pattern", r"^(E|FL)\d+_[a-z0-9-]+$")
        if not re.match(eid_pattern, eid):
            raise MetaError(
                f"{report}: experiment_id='{eid}' が設定されたパターン '{eid_pattern}' と不一致"
            )

        badge = EXPERIMENT_STATUS[status]

        if jira_enabled:
            jira = meta.get("jira", "")
            jira_base = config.get("jira_base_url", "https://atlassian.net/browse/")
            jira_link = f"[{jira}]({jira_base}{jira})" if jira else ""
            rows.append(
                (
                    jira or eid,
                    f"| [`{eid}`]({eid}/) | {jira_link} | {fmt_period(meta)} | {badge} | {meta['summary']} |",
                )
            )
        else:
            rows.append(
                (
                    eid,
                    f"| [`{eid}`]({eid}/) | {fmt_period(meta)} | {badge} | {meta['summary']} |",
                )
            )

    # ソート
    prefix = config.get("experiment_id_prefix", "E")
    if jira_enabled:
        rows.sort(key=lambda r: _jira_num(r[0]))
    else:
        rows.sort(key=lambda r: _exp_num(r[0], prefix))

    if jira_enabled:
        header = ["| 実験ID(ディレクトリ) | JIRA | 期間 | 状態 | 1 行要約 |", "|---|---|---|---|---|"]
    else:
        header = ["| 実験ID(ディレクトリ) | 期間 | 状態 | 1 行要約 |", "|---|---|---|---|"]

    return header + [r[1] for r in rows], warnings


def build_reports_table(reports_dir: Path, config: dict) -> tuple[list[str] | None, list[str]]:
    """(table_lines or None, warnings)。未移行ファイルがあれば None(生成スキップ)。"""
    report_files = sorted(
        p for p in reports_dir.glob("*.md") if p.name != "INDEX.md"
    )
    if not report_files:
        return None, []
    metas = []
    missing = []
    jira_enabled = config.get("jira_enabled", False)

    required_keys = ["report_id", "status", "summary"]
    if jira_enabled:
        required_keys.append("jira")

    for f in report_files:
        meta = parse_frontmatter(f)
        if meta is None or any(not meta.get(k) for k in required_keys):
            missing.append(f.name)
            continue
        if meta["status"] not in REPORT_STATUS:
            raise MetaError(
                f"{f}: status='{meta['status']}' は不正。許容: {list(REPORT_STATUS)}"
            )
        rid = meta["report_id"]
        if not f.name.startswith(rid):
            raise MetaError(f"{f}: report_id='{rid}' がファイル名先頭と不一致")
        metas.append((f.name, meta))

    if missing:
        warn = [
            f"フロントマター未付与のため reports/INDEX 生成スキップ: {reports_dir.parent.name}",
            *[f"    - {m}" for m in missing],
        ]
        return None, warn

    metas.sort(key=lambda x: _report_num(x[1]["report_id"]))

    if jira_enabled:
        header = ["| ファイル | JIRA | 状態 | 内容(1 行) |", "|---|---|---|---|"]
        body = []
        for name, meta in metas:
            jira = meta.get("jira", "")
            jira_base = config.get("jira_base_url", "https://atlassian.net/browse/")
            jira_link = f"[{jira}]({jira_base}{jira})" if jira else ""
            body.append(
                f"| [`{name}`]({name}) | {jira_link} | {REPORT_STATUS[meta['status']]} | {meta['summary']} |"
            )
    else:
        header = ["| ファイル | 状態 | 内容(1 行) |", "|---|---|---|"]
        body = [
            f"| [`{name}`]({name}) | {REPORT_STATUS[meta['status']]} | {meta['summary']} |"
            for name, meta in metas
        ]

    return header + body, []


def _jira_num(jira: str) -> int:
    digits = "".join(c for c in jira if c.isdigit())
    return int(digits) if digits else 0


def _exp_num(eid: str, prefix: str) -> int:
    m = re.match(r"^" + re.escape(prefix) + r"(\d+)", eid)
    if m:
        return int(m.group(1))
    digits = "".join(c for c in eid.split("_")[0] if c.isdigit())
    return int(digits) if digits else 0


def _report_num(rid: str) -> int:
    if "-R" in rid:
        tail = rid.split("-R", 1)[1]
        digits = "".join(c for c in tail if c.isdigit())
        return int(digits) if digits else 0
    return 0


# --- マーカ間の差し替え ------------------------------------------------------
def apply_block(index_path: Path, marker: str, table: list[str], check: bool) -> bool:
    """マーカ間を table で置換。check=True なら書かずに一致判定。"""
    start = f"<!-- gen:{marker}:start -->"
    end = f"<!-- gen:{marker}:end -->"
    text = index_path.read_text(encoding="utf-8")
    if start not in text or end not in text:
        raise MetaError(
            f"{index_path}: マーカ {start} / {end} が無い(手で1度だけ追加が必要)"
        )
    pre, rest = text.split(start, 1)
    _, post = rest.split(end, 1)
    new_block = start + "\n" + "\n".join(table) + "\n" + end
    new_text = pre + new_block + post
    if new_text == text:
        return False
    if not check:
        index_path.write_text(new_text, encoding="utf-8")
    return True


# --- ドライバ ----------------------------------------------------------------
def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("experiments", nargs="?", help="experiments/ ディレクトリ(既定: リポジトリ内)")
    ap.add_argument("--check", action="store_true", help="検証のみ。差分/不備があれば exit 1")
    args = ap.parse_args(argv)

    if args.experiments:
        exp_dir = Path(args.experiments)
    else:
        # install モデルでは tools/ が harness(ikmstack)への symlink のことがある。
        # __file__ を resolve() すると harness 側に張り付くので、cwd(=作業リポジトリ
        # =記録層)基準で experiments/ を解決する。skill/フックは repo ルートで走る。
        exp_dir = Path.cwd() / "experiments"
    if not exp_dir.is_dir():
        print(f"experiments ディレクトリが見つからない: {exp_dir}", file=sys.stderr)
        return 2

    # Load configuration
    workspace_root = exp_dir.parent
    config = load_config(workspace_root)

    changed = []
    warnings = []
    try:
        # 1) experiments/INDEX.md
        table, warns = build_experiments_table(exp_dir, config)
        warnings += warns
        top_index = exp_dir / "INDEX.md"
        if apply_block(top_index, "experiments-index", table, args.check):
            changed.append(top_index)

        # 2) 各 reports/INDEX.md
        for reports_dir in sorted(exp_dir.glob("*/reports")):
            ridx = reports_dir / "INDEX.md"
            if not ridx.exists():
                continue
            table, warns = build_reports_table(reports_dir, config)
            warnings += warns
            if table is None:
                continue
            if apply_block(ridx, "reports-index", table, args.check):
                changed.append(ridx)
    except MetaError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    for w in warnings:
        print(f"NOTE: {w}")

    if args.check:
        if changed:
            print("\n--check: 以下の INDEX がフロントマターと不一致(再生成が必要):")
            for c in changed:
                print(f"    {c}")
            return 1
        print("--check: 全 INDEX がフロントマターと一致")
        return 0

    if changed:
        print(f"更新: {len(changed)} 件")
        for c in changed:
            print(f"    {c}")
    else:
        print("変更なし(全 INDEX は最新)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
