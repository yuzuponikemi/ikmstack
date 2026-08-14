#!/usr/bin/env python3
"""log_draft.py — その日の commit から日次ログの**草稿**を組む(依存なし)

日次ログ(`logs/<YYYY>/<YYYY-MM-DD>_<topic>.md`)が書かれない主因は、
「やったことを思い出す」コストではなく**白紙から書き始めるコスト**だという仮説に基づく道具
(日次ログは書かれない日が続く一方、コミットは毎日積まれている——という観測に基づく)。

このリポジトリの commit メッセージは「何が分かったか」を本文に書く文体なので、
**素材としては既に揃っている**。ここでは素材を実験 ID ごとに束ね、
AGENTS.md 規定の 4 見出しに流し込むだけを行う。

**これは生成物ではなく草稿**である(重要):

  * 二重帳簿の生成物(INDEX / policy-map / harness-map)は「手で編集しない・回せば直る」もの。
    日次ログは逆で、**一度書き出したら手で育てるもの**。再生成で上書きしない。
  * だから既存ログがある日に `--write` しても**絶対に上書きしない**(標準出力に退避する)。
  * 埋められない欄(目的・次にやること)は**捏造せず** `⟦FILL⟧` を置く。
    「わかったこと」は commit 本文からの**候補**であり、そのまま残さず自分の言葉に直す。

使い方
------
  python tools/log_draft.py                        # 今日ぶんを標準出力へ
  python tools/log_draft.py --date 2026-08-04      # 指定日
  python tools/log_draft.py --since 2026-08-03 --until 2026-08-06   # 期間まとめ
  python tools/log_draft.py --date 2026-08-04 --topic e091-pressure --write

`--write` の出力先は `logs/<YYYY>/<日付>_<topic>.md`。`--topic` 省略時は
その日いちばん動いた実験のスラッグを使う(無ければ `session`)。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_meta import load_config  # noqa: E402

SEP = "\x1e"  # レコード区切り(コミット本文に改行があるため)
FIELD = "\x1f"
FINDING_CHARS = 220  # 「わかったこと」候補の刈り込み幅(全文は git show で読む)

# 実験 ID の接頭辞はノート固有(.lab-config.json の experiment_id_prefix)。
# 件名の接頭辞から実験を拾う: exp(E097): … / harness(E097): … / E023-R003: …
_CFG = load_config(Path.cwd())
PREFIX = str(_CFG.get("experiment_id_prefix", "E"))
_P = re.escape(PREFIX)
RE_SUBJECT_ID = re.compile(rf"(?:^|\(){_P}[-_]?(\d{{1,5}})")
RE_PATH_ID = re.compile(rf"^experiments/{_P}(\d{{1,5}})_")
# 本文末尾の定型行(署名・セッションURL・生成バナー)は素材にしない
RE_TRAILER = re.compile(
    r"^(Co-Authored-By:|Claude-Session:|Signed-off-by:|https://claude\.ai/|🤖)")


class Commit:
    def __init__(self, sha, iso_date, subject, body, files):
        self.sha = sha
        self.date = iso_date
        self.subject = subject
        self.body = body
        self.files = files

    @property
    def exp_id(self) -> str | None:
        """この commit が属する実験番号。件名 → 触ったパスの順に探す。"""
        m = RE_SUBJECT_ID.search(self.subject)
        if m:
            return m.group(1)
        for f in self.files:
            m = RE_PATH_ID.match(f.replace("\\", "/"))
            if m:
                return m.group(1)
        return None

    def finding(self) -> str | None:
        """本文の最初の段落を「わかったこと」の候補として返す(定型行は除く)。"""
        para: list[str] = []
        for line in self.body.splitlines():
            if RE_TRAILER.match(line.strip()):
                break
            if not line.strip():
                if para:
                    break
                continue
            para.append(line.strip())
        if not para:
            return None
        text = " ".join(para)
        if len(text) <= 40:
            return None  # 一行の事務連絡は素材にしない
        # 草稿は一覧性が命なので刈り込む。全文は `git show <sha>` で読む前提。
        return text if len(text) <= FINDING_CHARS else text[:FINDING_CHARS].rstrip() + " …"


def collect(repo: Path, since: str, until: str) -> list[Commit]:
    """[since, until] の commit を新しい順で返す(both inclusive)。"""
    fmt = SEP + FIELD.join(["%H", "%ad", "%s", "%b"])
    out = subprocess.run(
        ["git", "log", f"--since={since} 00:00", f"--until={until} 23:59",
         "--date=short", f"--pretty=format:{fmt}", "--name-only", "--no-merges"],
        cwd=repo, capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    commits = []
    for chunk in out.split(SEP):
        if not chunk.strip():
            continue
        parts = chunk.split(FIELD)
        if len(parts) < 4:
            continue
        sha, iso, subject, rest = parts[0], parts[1], parts[2], parts[3]
        # %b のあとに --name-only のファイル一覧が続く。空行で切れる。
        body_lines, files = [], []
        seen_blank = False
        for line in rest.splitlines():
            if not line.strip():
                seen_blank = True
                body_lines.append(line)
                continue
            if seen_blank and ("/" in line or line.endswith(".md")) and " " not in line:
                files.append(line.strip())
            else:
                body_lines.append(line)
        commits.append(Commit(sha[:7], iso, subject, "\n".join(body_lines), files))
    return commits


def exp_dirs(repo: Path) -> dict[str, str]:
    """実験番号 → 実験ディレクトリ名。"""
    out = {}
    for d in (repo / "experiments").glob(f"{PREFIX}*_*"):
        m = re.match(rf"{_P}(\d{{1,5}})_", d.name)
        if m:
            out[m.group(1)] = d.name
    return out


def render(commits: list[Commit], repo: Path, title_date: str) -> tuple[list[str], str]:
    """(草稿の行, 既定 topic スラッグ) を返す。"""
    dirs = exp_dirs(repo)
    groups: dict[str | None, list[Commit]] = defaultdict(list)
    for c in commits:
        groups[c.exp_id].append(c)
    ranked = sorted(groups.items(), key=lambda kv: (kv[0] is None, -len(kv[1])))

    top = next((k for k, _ in ranked if k), None)
    slug = "session"
    if top:
        name = dirs.get(top, f"{PREFIX}{top}")
        _s = f"{PREFIX.lower()}{top}"
        slug = f"{_s}-" + "-".join(name.split("_")[1:]) if "_" in name else _s

    L = [f"# {title_date} ⟦FILL: トピック名⟧", ""]
    L += [
        "> **これは草稿**(`python tools/log_draft.py` が commit から組んだもの)。",
        "> 生成物ではないので**回して上書きしない** — このまま置かず、手で育てる。",
        f"> 素材: {len(commits)} コミット / 実験 {sum(1 for k, _ in ranked if k)} 件。",
        "",
        "## 目的",
        "",
        "⟦FILL: なぜ今日これをやったか。commit には残っていない唯一の情報がここ⟧",
        "",
        "## やったこと",
        "",
    ]
    for exp, cs in ranked:
        if exp:
            name = dirs.get(exp, "")
            head = f"### {PREFIX}-{exp}" + (f" — [`{name}`](../../experiments/{name}/)" if name else "")
        else:
            head = "### その他(実験に紐づかない作業)"
        L += [head, ""]
        for c in cs:
            L.append(f"- {c.subject} (`{c.sha}`)")
        L.append("")

    L += [
        "## わかったこと",
        "",
        "> 以下は commit 本文からの**候補**。確定した事実だけを残し、"
        "自分の言葉に直す(⟦要推敲⟧ を消す)。",
        "",
    ]
    any_finding = False
    for exp, cs in ranked:
        for c in cs:
            f = c.finding()
            if not f:
                continue
            any_finding = True
            label = f"**{PREFIX}-{exp}**" if exp else "**その他**"
            L.append(f"- {label} ⟦要推敲⟧ {f} (`{c.sha}`)")
    if not any_finding:
        L.append("⟦FILL: 本文つきの commit が無い。今日わかったことを自分で書く⟧")
    L.append("")

    L += ["## 次にやること", "",
          "⟦FILL: 正本は各実験の PLAN.md(次の計画)/ REPORT.md(次のアクション)。"
          "ここには要点だけ⟧", ""]
    for exp, _ in ranked:
        if exp and exp in dirs:
            L.append(f"- 関連: [`experiments/{dirs[exp]}/PLAN.md`](../../experiments/{dirs[exp]}/PLAN.md)")
    L.append("")
    return L, slug


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="対象日 YYYY-MM-DD(既定: 今日)")
    ap.add_argument("--since", help="期間の開始(--date と排他)")
    ap.add_argument("--until", help="期間の終了")
    ap.add_argument("--topic", help="ファイル名の topic スラッグ(既定: 最も動いた実験)")
    ap.add_argument("--write", action="store_true",
                    help="logs/ に書き出す(既存ファイルは絶対に上書きしない)")
    args = ap.parse_args(argv)

    if args.since or args.until:
        since = args.since or args.until
        until = args.until or args.since
    else:
        since = until = args.date or _date.today().isoformat()

    # install モデルでは tools/ が harness への symlink。cwd(=記録層)基準で解決する。
    repo = Path.cwd()
    commits = collect(repo, since, until)
    if not commits:
        print(f"{since}〜{until} に commit が無い(草稿は作らない)")
        return 0

    title = since if since == until else f"{since}〜{until}"
    body, slug = render(commits, repo, title)
    text = "\n".join(body)

    if not args.write:
        print(text)
        return 0

    topic = args.topic or slug
    out = repo / "logs" / since[:4] / f"{since}_{topic}.md"
    if out.exists():
        print(f"既存ログがあるので書き込まない(手で追記すること): {out}\n", file=sys.stderr)
        print(text)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"草稿を書き出した(以後は手で育てる): {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
