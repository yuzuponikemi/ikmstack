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

個別レポートのフロントマター(撤回の記録)
------------------------------------------
正本: docs/conventions/reporting.md「改訂・撤回の記録」

  corrects:        E059-R00X        (任意 / 覆した一次記録。複数可)
  retraction_type: stale-source     (任意 / 統制語彙。RETRACTION_TYPES)
  discovered_by:   user-sme         (任意 / self|user-sme|independent-audit)
  superseded_by:   E059-R00X        (status: superseded なら必須。逆向きリンク)

`corrects` と `superseded_by` は役割が違う: 前者は「誤りを訂正した」関係(部分訂正でも
よい)、後者は「この版はもう読むな」という置換の逆向きリンク。

使い方
------
  python tools/report_meta.py            # 全 INDEX を生成(書き換え)
  python tools/report_meta.py --check    # 検証のみ(差分/不備があれば exit 1)
  python tools/report_meta.py --selftest # 撤回ゲートの自己検査(落ちるべきときに落ちるか)
  python tools/report_meta.py <experiments dir>  # 既定: リポジトリの experiments/

不備の隔離
----------
フロントマターが不正な実験・レポートが 1 件あっても**全体を中断しない**。
影響を最小の単位に閉じ込め、残りは生成する:

  * REPORT.md が不正        → その実験の行だけ experiments/INDEX から落とす
  * reports 配下が不正      → その実験の reports/INDEX だけ生成をスキップ

スキップは `WARN:` 行で必ず通知するが、**exit code は汚さない**。1 実験の不備で
他の実験の INDEX 生成(= 他セッションの commit)まで止めないことが目的。
ただし撤回リンク・語彙の違反だけは隔離せず exit code を汚す(下記 RetractionError)。
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


# --- 撤回(retraction)の統制語彙 --------------------------------------------
# 正本: docs/conventions/reporting.md「改訂・撤回の記録」。語彙は実在の撤回からのみ
# 起こす(想像で足さない)。増設は年 1 回の見直しで行う。
RETRACTION_TYPES = {
    "stale-source",
    "own-tool-artifact",
    "absence-claim",
    "population-gating",
    "wrong-metric",
    "unexcluded-confounder",
    "premise-model",
    "scope-impact",
    "other",
}
# 「後から来たデータで結論が前進した」は撤回ではないので、値として持たない。
DISCOVERED_BY = {"self", "user-sme", "independent-audit"}

# 施行日。これより前に作られた一次記録に `superseded_by` を遡って要求しない
# (claim マーカと同じ扱い = 遡及は要求しない)。ノートごとに
# .lab-config.json の `retraction_rule_epoch` で上書きできる。
# 他の検査(語彙・リンク解決・自己参照)は新設キーを書いたときだけ発火するので
# 施行日に関係なく全件に効く。
RETRACTION_RULE_EPOCH = "0000-00-00"


class MetaError(Exception):
    pass


class RetractionError(Exception):
    """撤回リンク・語彙の違反。

    他のスキーマ不備(段階移行の名残がありうる)と違い、これらのキーは新設で
    既存の違反が構造的に存在しない。よって隔離せず **exit code を汚す**
    (= コミットを止める)。正本: docs/conventions/reporting.md「改訂・撤回の記録」。
    """


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
        "allowed_figure_roots": ["_generated", "figures"],
        "retraction_rule_epoch": RETRACTION_RULE_EPOCH,
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


def build_experiments_table(
    exp_dir: Path, config: dict
) -> tuple[list[str], list[str], list[str]]:
    """(table_lines, notes, problems) を返す。

    1 実験の不備で全実験の INDEX 生成を止めない。不正な REPORT.md はその行だけ
    表から落として problems に積み、残りの実験は生成する。
    """
    rows = []
    warnings = []
    problems = []
    jira_enabled = config.get("jira_enabled", False)

    for report in sorted(exp_dir.glob("*/REPORT.md")):
        if report.parent.name.startswith("_"):
            continue  # _template など雛形は対象外
        try:
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
        except MetaError as e:
            problems.append(f"{e}\n        → この実験を experiments/INDEX から除外して続行")
            continue

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

    return header + [r[1] for r in rows], warnings, problems


def build_reports_table(
    reports_dir: Path, config: dict
) -> tuple[list[str] | None, list[str], list[str], list[str]]:
    """(table_lines or None, notes, problems, retraction_errors)。

    未移行 / 不正なファイルがあれば None を返し、その実験の reports/INDEX だけ
    生成をスキップする(半端な表を書いてレポートを黙って落とさないため)。
    影響はこの実験 1 つに閉じ、他の実験の INDEX 生成は続行する。
    """
    report_files = sorted(
        p for p in reports_dir.glob("*.md") if p.name != "INDEX.md"
    )
    if not report_files:
        return None, [], [], []
    metas = []
    missing = []
    problems = []
    jira_enabled = config.get("jira_enabled", False)

    required_keys = ["report_id", "status", "summary"]
    if jira_enabled:
        required_keys.append("jira")

    for f in report_files:
        try:
            meta = parse_frontmatter(f)
            # フロントマター無し / 本スキーマ非準拠は「未移行」扱い。段階移行のため
            # ここでは異常終了させず未移行一覧に積む。
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
        except MetaError as e:
            problems.append(
                f"{e}\n        → この実験の reports/INDEX 生成のみスキップして続行"
            )
            continue
        metas.append((f.name, meta))

    # 撤回の検査は INDEX 生成の成否と独立に行う(表を出せない実験でも見逃さない)。
    retraction_errors = check_retractions(metas, reports_dir, config)

    if problems:
        return None, [], problems, retraction_errors
    if missing:
        warn = [
            f"フロントマター未付与のため reports/INDEX 生成スキップ: {reports_dir.parent.name}",
            *[f"    - {m}" for m in missing],
        ]
        return None, warn, [], retraction_errors

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

    return header + body, [], [], retraction_errors


def _as_ids(value) -> list[str]:
    """`corrects` / `superseded_by` の値を report_id のリストに正規化する。"""
    if not value:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = str(value).replace(",", " ").split()
    return [s.strip() for s in items if s.strip()]


def check_retractions(
    metas: list[tuple[str, dict]], reports_dir: Path, config: dict
) -> list[str]:
    """撤回リンク・語彙を検査する(同一実験内で閉じる)。

    見るのは**リンクが解決するか / 語彙が正しいか**だけ。分類が妥当かどうかは
    機械は見ない(散文の意味判定はしない)。正本: docs/conventions/reporting.md。
    """
    epoch = str(config.get("retraction_rule_epoch", RETRACTION_RULE_EPOCH))
    known = {meta["report_id"] for _, meta in metas}
    errors: list[str] = []

    def err(name: str, msg: str) -> None:
        errors.append(f"{reports_dir / name}: {msg}")

    for name, meta in metas:
        rid = meta["report_id"]
        rtype = meta.get("retraction_type")
        if rtype and rtype not in RETRACTION_TYPES:
            err(name, f"retraction_type='{rtype}' は語彙外。許容: {sorted(RETRACTION_TYPES)}")
        disc = meta.get("discovered_by")
        if disc and disc not in DISCOVERED_BY:
            err(name, f"discovered_by='{disc}' は語彙外。許容: {sorted(DISCOVERED_BY)}")

        corrects = _as_ids(meta.get("corrects"))
        superseded_by = _as_ids(meta.get("superseded_by"))

        created = str(meta.get("created") or "")
        if (
            meta["status"] == "superseded"
            and not superseded_by
            and created >= epoch  # ISO 日付は辞書順=時系列順
        ):
            err(name, "status: superseded なのに superseded_by が無い(どれに置換されたか辿れない)")
        if (rtype or disc) and not corrects:
            err(name, "retraction_type / discovered_by があるのに corrects が無い(何を訂正したか不明)")

        for key, targets in (("corrects", corrects), ("superseded_by", superseded_by)):
            for target in targets:
                if target == rid:
                    err(name, f"{key} が自分自身({rid})を指している")
                elif target not in known:
                    err(
                        name,
                        f"{key}='{target}' が同一実験内の report_id に解決しない"
                        "(実験をまたぐ訂正は散文で書く)",
                    )
    return errors


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


# --- 自己検査(撤回ゲート) --------------------------------------------------
_SELFTEST_EPOCH = "2026-08-06"
_SELFTEST_CASES = [
    # (名前, 追加フロントマター行(R002 側), 期待するエラー断片。None = 通るべき)
    ("正常な撤回", ["corrects: E999-R001", "retraction_type: stale-source",
                    "discovered_by: user-sme"], None),
    ("未リンクの superseded", [], "superseded_by が無い"),
    ("施行日前の superseded は不問(遡及しない)", [], None),
    ("解決しない id", ["corrects: E999-R404", "retraction_type: stale-source"],
     "解決しない"),
    ("語彙外の類型", ["corrects: E999-R001", "retraction_type: typo-type"], "語彙外"),
    ("類型だけでリンク無し", ["retraction_type: stale-source"], "corrects が無い"),
    ("自己参照", ["corrects: E999-R002", "retraction_type: stale-source"],
     "自分自身"),
]


def _selftest() -> int:
    """撤回ゲートが「落ちるべきときに落ちる」ことを確認する(policy_gate --selftest に倣う)。"""
    import tempfile

    config = {"jira_enabled": False, "retraction_rule_epoch": _SELFTEST_EPOCH}
    failures = []
    for name, extra, expect in _SELFTEST_CASES:
        with tempfile.TemporaryDirectory() as tmp:
            rep = Path(tmp) / "experiments" / "E999_selftest" / "reports"
            rep.mkdir(parents=True)
            # R001 = 覆された側(superseded)。ケースにより逆向きリンクを欠かせる。
            grandfathered = name.startswith("施行日前")
            old_created = "2026-01-01" if grandfathered else _SELFTEST_EPOCH
            old_link = (
                []
                if name == "未リンクの superseded" or grandfathered
                else ["superseded_by: E999-R002"]
            )
            (rep / "E999-R001_20260101_old.md").write_text(
                "---\nreport_id: E999-R001\ntype: 結果\n"
                f"status: superseded\ncreated: {old_created}\n"
                + "".join(f"{ln}\n" for ln in old_link)
                + "summary: old\n---\n", encoding="utf-8")
            # R002 = 訂正した側。
            (rep / "E999-R002_20260102_new.md").write_text(
                "---\nreport_id: E999-R002\ntype: 結果\n"
                "status: active\ncreated: 2026-08-07\n"
                + "".join(f"{ln}\n" for ln in extra)
                + "summary: new\n---\n", encoding="utf-8")

            _, _, _, errors = build_reports_table(rep, config)
            joined = " / ".join(errors)
            if expect is None and errors:
                failures.append(f"{name}: 通るべきなのに落ちた -> {joined}")
            elif expect and expect not in joined:
                failures.append(f"{name}: '{expect}' を検出できなかった -> {joined or '(エラー無し)'}")

    for f in failures:
        print(f"FAIL: {f}", file=sys.stderr)
    if failures:
        print(f"\n--selftest: {len(failures)} / {len(_SELFTEST_CASES)} 件 失敗", file=sys.stderr)
        return 1
    print(f"--selftest: 撤回ゲート {len(_SELFTEST_CASES)} 件すべて期待どおり")
    return 0


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
    ap.add_argument("--selftest", action="store_true",
                    help="撤回ゲートの自己検査(落ちるべきときに落ちるか)")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

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
    problems = []
    retraction_errors = []

    # 1) experiments/INDEX.md — 表の中身は実験ごとに skip 可。ここで致命的なのは
    #    INDEX.md 自体の構造不備(マーカ欠落)だけで、それは全実験に影響するので中断する。
    table, warns, probs = build_experiments_table(exp_dir, config)
    warnings += warns
    problems += probs
    top_index = exp_dir / "INDEX.md"
    try:
        if apply_block(top_index, "experiments-index", table, args.check):
            changed.append(top_index)
    except MetaError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # 2) 各 reports/INDEX.md — 失敗はその実験 1 つに閉じ込め、他は生成を続ける。
    for reports_dir in sorted(exp_dir.glob("*/reports")):
        ridx = reports_dir / "INDEX.md"
        if not ridx.exists():
            continue
        table, warns, probs, res = build_reports_table(reports_dir, config)
        warnings += warns
        problems += probs
        retraction_errors += res
        if table is None:
            continue  # 部分移行中 / 不備あり → 触らない
        try:
            if apply_block(ridx, "reports-index", table, args.check):
                changed.append(ridx)
        except MetaError as e:
            problems.append(f"{e}\n        → この実験の reports/INDEX のみスキップして続行")

    for w in warnings:
        print(f"NOTE: {w}")
    for p in problems:
        print(f"WARN: {p}")
    if problems:
        # 意図的に exit code は汚さない。1 件の不備で他の実験の INDEX 生成
        # (= 他セッションのコミット)を止めないことが、この分岐の目的。
        print(
            f"\n⚠ {len(problems)} 件の不備を上記のとおりスキップして続行しました。"
            "該当分は INDEX に載りません — フロントマターを直して再実行してください。"
        )

    # 撤回リンク・語彙の違反は隔離しない(新設キーなので既存違反が構造的に無い)。
    # ここだけは exit code を汚し、コミットを止める。
    if retraction_errors:
        print("\nERROR: 撤回(retraction)の記録が不正です:", file=sys.stderr)
        for e in retraction_errors:
            print(f"    {e}", file=sys.stderr)
        print("    → 正本: docs/conventions/reporting.md「改訂・撤回の記録」", file=sys.stderr)
        return 1

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

    # 3) HTML 読みビュー(派生・gitignore 済み)を追随再生成 — 失敗しても INDEX 生成は成功扱い
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import index_html

        out = index_html.generate(exp_dir)
        print(f"HTML ビュー更新: {out}")
    except Exception as e:  # HTML view must never block INDEX generation
        print(f"NOTE: INDEX.html 生成をスキップ: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
