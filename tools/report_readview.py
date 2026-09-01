#!/usr/bin/env python3
"""report_readview.py — 個別レポート(<experiment_id>-R###_*.md)の HTML 読みビュー生成.

MD を単一の正本に保ったまま、読みやすい派生 HTML を生成する。exp-deck(外部共有向け
最終スライド)とは別の「中間レポートをスッと読む」層。

やること:
  - フロントマター → マストヘッド(report_id/jira/type/status/日付) + 見出し文
  - 確度タグ (確定)/(確度中…)/(確度高)/【重要…】 → 色チップ
  - 引用(> 🔗/📝/⚠️/🚫 …) → 色分けコールアウト
  - 画像 ![](…png) → base64 data URI 自動埋め込み(相対パス解決。無ければプレースホルダ)
  - 表 → 横スクロール枠 + 数値列右寄せ + tabular-nums
  - 数式 $…$ / $$…$$ → 整形スパン(Unicode 主体の素数式に対応。真の LaTeX→MathML は v2)
  - `## 結論`(および要点/概要)以外の H2 セクションを <details> に畳んで段階開示
  - 調査3台帳(questions/sources/claims.jsonl)が隣にあれば、散文中の
    `(claim:cNNN)` / `Q<n>` / `s<nnn>` をチップ化しホバーで台帳を出す(--no-ledger で無効)

使い方:
  python3 tools/report_readview.py <report.md> [-o out.html] [--stdout] [--no-fold] [--no-ledger]
  既定の出力先: その実験の _generated/<stem>.readview.html

依存: mistune(>=3)。図生成で既にローカルは依存パッケージを使うため許容(AGENTS 三大原則は
      「図・大容量データを git に入れない」であって「依存禁止」ではない)。report_meta.py の
      フロントマターパーサを再利用する。
      システムの python3 に mistune が無い場合は `uv run --with mistune` へ自己再実行する
      (`experiments/_template` の作図スクリプトが matplotlib に対して使うのと同じ型)。
      uv も無ければ exit 2 = SKIP(呼び出し側の gen_readview.py は SKIP を失敗にしない)。
"""
from __future__ import annotations

import argparse
import base64
import html
import os
import re
import sys
from pathlib import Path

from urllib.parse import unquote

# --- mistune が無ければ uv 経由で自己再実行 ------------------------------------
try:
    import mistune
except ModuleNotFoundError:
    import os
    import shutil
    import subprocess

    if os.environ.get("_UV_REEXEC") == "1":
        print("mistune still missing after re-exec", file=sys.stderr)
        raise SystemExit(1)
    _uv = shutil.which("uv")
    if not _uv:
        print("mistune is missing and uv is not installed -- skipping the read view",
              file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(subprocess.run(
        [_uv, "run", "--quiet", "--with", "mistune>=3", "python", "-X", "utf8",
         __file__, *sys.argv[1:]],
        env={**os.environ, "_UV_REEXEC": "1"}).returncode)

# report_meta.py のフロントマターパーサを再利用(重複実装を避ける)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_meta import load_config  # noqa: E402
from report_meta import parse_frontmatter  # noqa: E402

from readview.theme import css  # noqa: E402
from readview import ledger as _ledger  # noqa: E402

_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp"}

_STATUS_CLASS = {"active": "st-active", "done": "st-active", "planning": "st-planning",
                 "superseded": "st-superseded", "historical": "st-historical"}

# セクションを畳まず開いたままにする見出し(要点系)
_OPEN_HEADINGS = ("結論", "要点", "サマリ", "概要", "tl;dr")


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def _chipify(escaped: str) -> str:
    """HTML エスケープ済みテキスト中の確度タグを色チップへ置換する。"""
    def fix(m):    return f'<span class="chip c-fix">確定</span>{_note(m.group(1))}'
    def mid(m):    return f'<span class="chip c-mid">確度中</span>{_note(m.group(1))}'
    def hi(m):     return f'<span class="chip c-hi">確度高</span>{_note(m.group(1))}'
    def warn(m):   return f'<span class="chip c-warn">{m.group(1)}</span>'

    def _note(extra: str) -> str:
        extra = extra.strip(" 　・:：")
        return f' <span class="rv-note">{extra}</span>' if extra else ""

    # 確度タグは必ず括弧付き（(確定) / (確度中・要動作確認) / (確度: 高)）という規約。
    # 括弧を必須にし、かつ「確定」の直後が区切り文字のときだけ一致させる
    # （"確定事実" のような複合語を誤ってチップ化しないため）。順序: 中/高 を先に。
    s = escaped
    s = re.sub(r'[（(]確度[:：]?\s*中([^)）]*)[)）]', mid, s)
    s = re.sub(r'[（(]確度[:：]?\s*高([^)）]*)[)）]', hi, s)
    s = re.sub(r'[（(]確定(?=[)）・、,：:§\s])([^)）]*)[)）]', fix, s)
    s = re.sub(r'【(最重要|重要[^】]*)】', warn, s)
    return s


_WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)\]\]")
# 実験 ID の接頭辞はノート固有(.lab-config.json)。FL 固定にするとウィキリンクが
# 別プレフィックスのノートで永久に解決しない(例外も出ないので気づけない)。
_PREFIX_RAW = str(load_config(Path.cwd()).get("experiment_id_prefix", "E"))
_PREFIX = re.escape(_PREFIX_RAW)
_RID_RE = re.compile(rf"^{_PREFIX}\d+-R\d+$")     # レポート参照
_EXP_RE = re.compile(rf"^{_PREFIX}\d+(_[\w-]+)?$")  # 実験参照(E### または E###_slug)


def _resolve_ref(token: str, exp_root: Path | None, out_dir: Path):
    """[[E###]] / [[E###-R###]] を、隣の読みビュー or 実験一覧への相対 href に解決。"""
    if exp_root is None:
        return None
    exps = exp_root.parent  # experiments/
    try:
        if _RID_RE.match(token):
            hits = sorted(exps.glob(f"*/reports/{token}_*.md"))
            if hits:
                return os.path.relpath(_default_out(hits[0]), out_dir).replace("\\", "/")
        elif _EXP_RE.match(token):
            pat = token if "_" in token else f"{token}_*"
            hits = sorted(exps.glob(pat))
            if hits and hits[0].is_dir():
                idx = hits[0] / "_generated" / "index.html"
                return os.path.relpath(idx, out_dir).replace("\\", "/")
    except OSError:
        return None
    return None


def _preprocess_wikilinks(md: str, exp_root: Path | None, out_dir: Path) -> str:
    """mistune に渡す前に [[X]] を [X](解決先) へ。コード(フェンス/インライン)は保護する。
    mistune は [[…]] を複数トークンに割るため、テキスト後処理でなく前処理で扱う。"""
    if exp_root is None or "[[" not in md:
        return md
    stash: list[str] = []

    def mask(m):
        stash.append(m.group(0))
        return f"\x00{len(stash) - 1}\x00"

    masked = re.sub(r"```.*?```", mask, md, flags=re.S)   # フェンスコード
    masked = re.sub(r"`[^`\n]*`", mask, masked)            # インラインコード

    def repl(m):
        token = m.group(1).strip()
        href = _resolve_ref(token, exp_root, out_dir)
        return f"[{token}]({href})" if href else m.group(0)

    masked = _WIKILINK_RE.sub(repl, masked)
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], masked)


class ReadViewRenderer(mistune.HTMLRenderer):
    """読みビュー用の HTML レンダラ。

    base_dir=画像/リンクの相対解決の基点(md のあるディレクトリ)。out_dir=この読みビューの
    出力先(<exp>/_generated)。相対 .md リンクと [[FL...]] を、隣の読みビュー(.readview.html)や
    実験一覧(index.html)へ張り替える。
    """

    def __init__(self, base_dir: Path, md_path: Path):
        super().__init__(escape=False)
        self.base_dir = base_dir
        self.md_path = md_path
        self.out_dir = _default_out(md_path).parent
        self.exp_root = _exp_root(md_path)

    # 確度チップは通常テキストにのみ適用(コードは別処理)。[[…]] は mistune 前で前処理済み。
    def text(self, text: str) -> str:
        return _chipify(_esc(text))

    # --- クロスリンク: 相対 .md → 隣の .readview.html --------------------------
    def link(self, text: str, url: str, title=None) -> str:
        ttl = f' title="{_esc(title)}"' if title else ""
        return f'<a href="{self._rewrite_md_link(url)}"{ttl}>{text}</a>'

    def _rewrite_md_link(self, url: str) -> str:
        if not url or url.startswith(("http://", "https://", "#", "mailto:")):
            return url
        raw_path, _, frag = url.partition("#")
        # mistune はリンク先を percent-encode して渡すため復号してから解決する
        path = unquote(raw_path)
        if not path.endswith(".md"):
            return url
        frag = ("#" + frag) if frag else ""
        try:
            target = (self.base_dir / path).resolve()
        except OSError:
            return url
        if target.exists():
            rel = os.path.relpath(_default_out(target), self.out_dir).replace("\\", "/")
            return rel + frag
        # 解決できなくても同一 _generated 前提で拡張子だけ張り替え(ベストエフォート)
        return re.sub(r"\.md$", ".readview.html", path) + frag

    def block_quote(self, text: str) -> str:
        cls = "co-note"
        if "🔗" in text or "前提" in text:
            cls = "co-prem"
        elif "📝" in text or "用語" in text or "要約" in text:
            cls = "co-term"
        elif "⚠️" in text or "🚫" in text or "重要" in text:
            cls = "co-warn"
        return f'<blockquote class="{cls}">{text}</blockquote>\n'

    def image(self, alt: str, url: str, title=None) -> str:
        alt_txt = _esc(alt or "")
        name = url.split("/")[-1]
        target = (self.base_dir / url).resolve()
        ext = target.suffix.lower()
        if target.exists() and ext in _MIME:
            data = base64.b64encode(target.read_bytes()).decode()
            body = f'<img alt="{alt_txt}" src="data:{_MIME[ext]};base64,{data}"/>'
        else:
            body = ('<div class="missing">図が見つかりません — '
                    '<code>regenerate.sh</code> で再生成後に再実行すると埋め込まれます</div>')
        cap = f'<span class="t">{alt_txt}</span>' if alt_txt else ""
        return (f'<div class="fig"><div class="fig-cap"><span class="badge">図</span>{cap}</div>'
                f'{body}<div class="src">src: {_esc(url)}</div></div>')

    def paragraph(self, text: str) -> str:
        # 図・引用のブロックが単独段落なら <p> で包まない(div in p を避ける)
        t = text.strip()
        if t.startswith('<div class="fig"') or t.startswith("<blockquote"):
            return text + "\n"
        return f"<p>{text}</p>\n"

    # --- table plugin: 列単位で数値列を右寄せ + 横スクロール枠 ------------------
    # 配置はセル単位でなく「列単位」で決める(数値が多数の列はヘッダも本文も右寄せ)。
    # セル単位だと同一列内で右/左が混在し読みづらくなるため、table() で後処理する。
    def table(self, text: str) -> str:
        return f'<div class="tbl-scroll"><table>{_align_columns(text)}</table></div>\n'

    def table_cell(self, text: str, align=None, head=False) -> str:
        tag = "th" if head else "td"
        # md 明示の :---: 等があれば尊重。数値列の右寄せは table() が後処理で付ける。
        a = f' style="text-align:{align}"' if align else ""
        return f"<{tag}{a}>{text}</{tag}>"

    # --- math plugin: 素数式(Unicode 主体)を整形スパンで表示 ------------------
    def inline_math(self, text: str) -> str:
        return f'<span class="math-inline">{_esc(text)}</span>'

    def block_math(self, text: str) -> str:
        return f'<div class="math-block">{_esc(text)}</div>\n'


_NUM_RE = re.compile(r"^[−\-+]?[\d,]+(\.\d+)?%?$")


def _is_num(cell_html: str) -> bool:
    """セルの表示テキスト(タグ除去)が数値なら True。"""
    txt = re.sub(r"<[^>]+>", "", cell_html).strip()
    return bool(txt) and bool(_NUM_RE.match(txt))


def _cell_text(cell_html: str) -> str:
    return re.sub(r"<[^>]+>", "", cell_html).strip()


_ALIGN_RE = re.compile(r"text-align:\s*(left|center|right)")


def _align_columns(table_inner: str, threshold: float = 0.6) -> str:
    """テーブル内 HTML を列単位で整列。

    優先順位: (1) Markdown 明示配置(`:--:`/`---:`/`:--` = mistune が付ける
    style=text-align) を最優先し、ヘッダ・本文とも同じ配置に揃える。(2) 明示が
    無い列だけ、本文が数値多数(>=threshold)なら右寄せに自動判定。これにより
    単位付き数値(例 "2.7g")で明示右寄せした列が左に化けるのを防ぎ、列内配置を統一する。
    """
    def cells_of(row: str, tag: str):
        # (attrs, inner) を返す
        return re.findall(rf"<{tag}\b([^>]*)>(.*?)</{tag}>", row, re.S)

    header = None
    body: list[list[tuple[str, str]]] = []
    for r in re.findall(r"<tr>(.*?)</tr>", table_inner, re.S):
        th = cells_of(r, "th")
        td = cells_of(r, "td")
        if th and header is None:
            header = th
        elif td:
            body.append(td)
    if header is None and not body:
        return table_inner
    ncol = max([len(header or [])] + [len(b) for b in body], default=0)
    if ncol == 0:
        return table_inner

    align: list[str | None] = [None] * ncol
    for c in range(ncol):
        cells = ([header[c]] if header and c < len(header) else []) + \
                [b[c] for b in body if c < len(b)]
        # (1) 明示配置(ヘッダ/本文いずれかにあれば採用)
        explicit = None
        for attrs, _inner in cells:
            m = _ALIGN_RE.search(attrs)
            if m:
                explicit = m.group(1)
                break
        if explicit:
            align[c] = explicit
            continue
        # (2) 自動: 本文が数値多数なら右
        bodyvals = [b[c][1] for b in body if c < len(b)]
        nonempty = [v for v in bodyvals if _cell_text(v)]
        if nonempty and sum(_is_num(v) for v in nonempty) / len(nonempty) >= threshold:
            align[c] = "right"

    def cell_html(tag: str, i: int, inner: str) -> str:
        a = align[i] if i < ncol else None
        if a == "right":
            return f'<{tag} class="num">{inner}</{tag}>'
        if a == "center":
            return f'<{tag} style="text-align:center">{inner}</{tag}>'
        return f"<{tag}>{inner}</{tag}>"

    out = ""
    if header:
        out += "<thead><tr>" + "".join(
            cell_html("th", i, inner) for i, (_a, inner) in enumerate(header)) + "</tr></thead>"
    out += "<tbody>" + "".join(
        "<tr>" + "".join(cell_html("td", i, inner) for i, (_a, inner) in enumerate(b))
        + "</tr>" for b in body) + "</tbody>"
    return out


def _process_sections(body: str, fold: bool) -> tuple[str, list[tuple[str, str]]]:
    """H2 区切りでセクションを整形し、目次(id, タイトル)も収集して返す。

    - fold=True: 要点系(結論等)は開いた見出し、それ以外は <details open>(既定で展開。
      ユーザーは「すべて畳む」で概観に切替可能)。
    - fold=False: すべて素の見出し。
    どちらも各セクションに id を振り、目次リンクの飛び先にする。
    """
    parts = re.split(r"(<h2[^>]*>.*?</h2>)", body, flags=re.S)
    out = [parts[0]]  # 最初の H2 より前(導入・コールアウト)はそのまま
    toc: list[tuple[str, str]] = []
    i, n = 1, 0
    while i < len(parts):
        h2 = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""
        inner = re.sub(r"</?h2[^>]*>", "", h2)
        plain = re.sub(r"<[^>]+>", "", inner).strip()
        n += 1
        sid = f"sec-{n}"
        toc.append((sid, plain))
        keep_open = (not fold) or any(k in plain.lower() for k in _OPEN_HEADINGS)
        if keep_open:
            out.append(f'<h2 id="{sid}" class="open-sec">{inner}</h2>{content}')
        else:
            out.append(
                f'<details id="{sid}" class="det" open><summary><span class="tw">▶</span>{inner}'
                f'</summary><div class="det-body">{content}</div></details>'
            )
        i += 2
    return "".join(out), toc


def _split_summary(summary: str, min_len: int = 16) -> tuple[str, str]:
    """要約を(見出し, deck)に分ける。先頭文が短すぎる('M2。'等)ときは次文まで束ねて
    見出しにし、残り全文を deck に回す(要約本体を取りこぼさない)。"""
    if not summary:
        return "", ""
    # 「。」で分割(区切りは各文末に残す)。空要素は除く。
    parts = [p for p in re.split(r"(?<=。)", summary) if p.strip()]
    if not parts:
        return summary, ""
    headline = ""
    i = 0
    while i < len(parts) and len(headline) < min_len:
        headline += parts[i]
        i += 1
    deck = "".join(parts[i:]).strip()
    return headline.strip(), deck


def _masthead(meta: dict) -> str:
    rid = meta.get("report_id") or meta.get("experiment_id") or ""
    typ = meta.get("type") or ""
    summary = (meta.get("summary") or "").strip()
    headline, deck = _split_summary(summary)
    if not headline:
        headline = rid
    chips = []
    for k, key in (("jira", "jira"), ("type", "type"), ("created", "created"),
                   ("data-era", "data_era")):
        v = meta.get(key)
        if v:
            v = str(v)
            if key == "data_era" and len(v) > 60:
                v = v[:57] + "…"
            chips.append(f'<li><span class="k">{k}</span><b>{_esc(v)}</b></li>')
    st = str(meta.get("status") or "")
    if st:
        chips.append(f'<li class="{_STATUS_CLASS.get(st, "")}">'
                     f'<span class="k">status</span><b>{_esc(st)}</b></li>')
    label = f"{_esc(rid)} · {_esc(typ)}レポート" if typ else _esc(rid)
    deck_html = f'<p class="deck">{_esc(deck)}</p>' if deck else ""
    return (
        f'<header class="masthead"><div class="wrap">'
        f'<p class="rid">{label}</p>'
        f'<h1>{_esc(headline)}</h1>'
        f"{deck_html}"
        f'<ul class="meta">{"".join(chips)}</ul>'
        f"</div></header>"
    )


def _strip_leading_h1(md_body: str) -> str:
    """本文冒頭の `# タイトル` はマストヘッドと重複するため除去する。"""
    lines = md_body.splitlines()
    out, removed = [], False
    for ln in lines:
        if not removed and ln.lstrip().startswith("# "):
            removed = True
            continue
        out.append(ln)
    return "\n".join(out)


def render_html(md_path: Path, fold: bool = True, siblings: list[dict] | None = None,
                use_ledger: bool = True) -> str:
    meta = parse_frontmatter(md_path) or {}
    if siblings is None:
        siblings = _sibling_reports(md_path)
    switcher = _switcher(siblings)
    raw = md_path.read_text(encoding="utf-8")
    # フロントマターを本文から除去
    body_md = raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            body_md = raw[end + 4:]
    body_md = _strip_leading_h1(body_md)
    # [[FL...]] クロスリンクは mistune 前に解決(トークン分割を避ける)
    body_md = _preprocess_wikilinks(body_md, _exp_root(md_path), _default_out(md_path).parent)

    renderer = ReadViewRenderer(base_dir=md_path.parent, md_path=md_path)
    md = mistune.create_markdown(
        renderer=renderer,
        plugins=["table", "strikethrough", "task_lists", "math", "url"],
    )
    body_html = md(body_md)
    body_html, toc = _process_sections(body_html, fold)

    # 調査3台帳が隣にあれば、台帳参照をチップ化して読みながら確かめられるようにする
    led = _ledger.load(md_path) if use_ledger else None
    if led:
        body_html = _ledger.chipify(body_html, led)
    led_css = _ledger.css() if led else ""
    led_pills = ("\n  " + _ledger.pills(led)) if led else ""
    led_panel = ("\n" + _ledger.panel()) if led else ""
    led_js = ("\n" + _ledger.script(led).strip()) if led else ""
    toc_html = "".join(
        f'<li><a href="#{sid}">{_esc(title)}</a></li>' for sid, title in toc)

    title = _esc(meta.get("report_id") or md_path.stem)
    rel = md_path.name
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title} · read-view</title>
<style>{css()}{led_css}</style>
</head>
<body>
<div class="toolbar"><div class="wrap">
  {switcher}{led_pills}
  <span class="spacer"></span>
  <button class="btn" id="rv-toc-btn" aria-expanded="false">セクション</button>
  <button class="btn" id="rv-expand">すべて展開</button>
  <button class="btn" id="rv-collapse">すべて畳む</button>
  <nav class="toc" id="rv-toc" hidden><ol>{toc_html}</ol></nav>
</div></div>
{_masthead(meta)}
<div class="wrap">
<section class="doc">
{body_html}
</section>
<p class="foot">Read-view · 元文書: <code>{_esc(rel)}</code> ·
内容は Markdown 正本を忠実にレンダリングしたもの(要約・改変なし)。正本の更新はこの HTML でなく MD 側で行う。</p>
</div>
<button class="totop" id="rv-totop" aria-label="先頭へ戻る" hidden>↑</button>{led_panel}
<div class="lb" id="rv-lb" hidden><img id="rv-lb-img" alt=""/></div>
<script>
  const $ = id => document.getElementById(id);
  const all = s => document.querySelectorAll(s);
  // 展開/畳む
  $('rv-expand') && $('rv-expand').addEventListener('click', () => all('details.det').forEach(d => d.open = true));
  $('rv-collapse') && $('rv-collapse').addEventListener('click', () => all('details.det').forEach(d => d.open = false));
  // 目次トグル
  const toc = $('rv-toc'), tocBtn = $('rv-toc-btn');
  if (tocBtn) tocBtn.addEventListener('click', e => {{
    e.stopPropagation();
    const show = toc.hidden; toc.hidden = !show; tocBtn.setAttribute('aria-expanded', show);
  }});
  document.addEventListener('click', e => {{ if (toc && !toc.hidden && !toc.contains(e.target) && e.target !== tocBtn) toc.hidden = true; }});
  // 目次リンク: 畳まれた details を開いてから移動
  toc && toc.addEventListener('click', e => {{
    const a = e.target.closest('a'); if (!a) return;
    const el = document.querySelector(a.getAttribute('href'));
    if (el && el.tagName === 'DETAILS') el.open = true;
    toc.hidden = true;
  }});
  // 画像ライトボックス(クリックで拡大)
  const lb = $('rv-lb'), lbImg = $('rv-lb-img');
  all('.fig img').forEach(img => img.addEventListener('click', () => {{ lbImg.src = img.src; lb.hidden = false; }}));
  lb && lb.addEventListener('click', () => {{ lb.hidden = true; lbImg.src = ''; }});
  document.addEventListener('keydown', e => {{ if (e.key === 'Escape' && lb && !lb.hidden) {{ lb.hidden = true; lbImg.src = ''; }} }});
  // レポート切替(ドロップダウン)
  $('rv-jump') && $('rv-jump').addEventListener('change', e => {{ location.href = e.target.value; }});
  // 目次スクロール追従(現在のセクションをハイライト)
  const tocLinks = new Map([...document.querySelectorAll('.toc a')].map(a => [a.getAttribute('href').slice(1), a]));
  const secEls = [...document.querySelectorAll('h2[id], details[id]')];
  if (tocLinks.size && secEls.length && 'IntersectionObserver' in window) {{
    let activeId = null;
    const setActive = id => {{
      if (id === activeId) return; activeId = id;
      tocLinks.forEach(a => a.classList.remove('active'));
      const a = tocLinks.get(id); if (a) a.classList.add('active');
    }};
    const io = new IntersectionObserver(entries => {{
      const vis = entries.filter(e => e.isIntersecting)
                         .sort((x, y) => x.boundingClientRect.top - y.boundingClientRect.top);
      if (vis.length) setActive(vis[0].target.id);
    }}, {{rootMargin: '-8% 0px -80% 0px', threshold: 0}});
    secEls.forEach(s => io.observe(s));
  }}
  // 先頭へ戻る
  const totop = $('rv-totop');
  if (totop) {{
    addEventListener('scroll', () => {{ totop.hidden = scrollY < 600; }}, {{passive: true}});
    totop.addEventListener('click', () => scrollTo({{top: 0, behavior: 'smooth'}}));
  }}
</script>{led_js}
</body>
</html>
"""


def _exp_root(md_path: Path) -> Path | None:
    """レポート MD からその実験ルート(reports/ の親、または REPORT.md の親)を推定。"""
    if md_path.parent.name == "reports":
        return md_path.parent.parent
    if (md_path.parent / "reports").exists() or (md_path.parent / "REPORT.md").exists():
        return md_path.parent
    return None


def _default_out(md_path: Path) -> Path:
    """実験ルート配下 _generated/ に出力。実験外なら隣に .readview.html。"""
    root = _exp_root(md_path)
    if root is not None:
        return root / "_generated" / f"{md_path.stem}.readview.html"
    return md_path.with_suffix(".readview.html")


def _collect_reports(exp_dir: Path) -> list[Path]:
    """実験ディレクトリ配下のレンダリング対象 MD を集める。

    対象 = REPORT.md + reports/<prefix>###-R###_*.md。**接頭辞は .lab-config.json 由来**
    (`experiment_id_prefix`)。ここをリテラルで固定すると、接頭辞が違うノートでは
    一次記録が 1 件も拾われず、しかも「0 failed」と出るため**空振りが成功に見える**
    (E003/E004 で繰り返し踏んだ欠陥の型)。保険として、接頭辞に一致しない
    `*-R###_*.md` も拾う。
    """
    targets: list[Path] = []
    report = exp_dir / "REPORT.md"
    if report.exists():
        targets.append(report)
    reports_dir = exp_dir / "reports"
    if reports_dir.is_dir():
        found = set(reports_dir.glob(f"{_PREFIX_RAW}*-R*_*.md"))
        found |= {p for p in reports_dir.glob("*-R*_*.md")
                  if not p.name.startswith(("_", "."))}
        targets += sorted(found)
    return targets


def _nav_info(md_path: Path) -> dict:
    """レポート切替ナビ・一覧ページ用のメタ(1件分)。"""
    m = parse_frontmatter(md_path) or {}
    is_report = md_path.name == "REPORT.md"
    rid = m.get("report_id") or ("総括(REPORT)" if is_report else md_path.stem)
    typ = m.get("type") or ("総括" if is_report else "")
    headline, _deck = _split_summary((m.get("summary") or "").strip())
    return {
        "stem": md_path.stem, "href": f"{md_path.stem}.readview.html",
        "rid": rid, "type": typ, "title": headline or rid,
        "status": str(m.get("status") or ""),
    }


def _sibling_reports(md_path: Path) -> list[dict]:
    """同一実験内の全レポートを順序付きで返す(REPORT → R001, R002 …)。current 印付き。"""
    root = _exp_root(md_path)
    if root is None:
        return []
    sibs = [_nav_info(p) for p in _collect_reports(root)]
    for s in sibs:
        s["current"] = (s["stem"] == md_path.stem)
    return sibs


def _switcher(siblings: list[dict]) -> str:
    """ツールバー用のレポート切替(前/次 + ドロップダウン + 一覧リンク)。"""
    if len(siblings) <= 1:
        return ""
    idx = next((i for i, s in enumerate(siblings) if s.get("current")), 0)
    total = len(siblings)
    opts = "".join(
        f'<option value="{s["href"]}"{" selected" if s.get("current") else ""}>'
        f'{i + 1}. {_esc(s["rid"])}</option>'
        for i, s in enumerate(siblings))
    prev_h = siblings[idx - 1]["href"] if idx > 0 else ""
    next_h = siblings[idx + 1]["href"] if idx < total - 1 else ""
    prev = (f'<a class="btn nav-a" href="{prev_h}" title="前のレポート">‹</a>' if prev_h
            else '<span class="btn nav-a disabled">‹</span>')
    nxt = (f'<a class="btn nav-a" href="{next_h}" title="次のレポート">›</a>' if next_h
           else '<span class="btn nav-a disabled">›</span>')
    return (
        '<span class="rv-switch">'
        '<a class="btn" href="index.html" title="この実験のレポート一覧">☰ 一覧</a>'
        f'{prev}<select class="rv-jump" id="rv-jump" '
        f'title="レポート切替 ({idx + 1}/{total})">{opts}</select>{nxt}'
        '</span>'
    )


def _index_html(exp_dir: Path, siblings: list[dict]) -> str:
    """実験の _generated/index.html(レポート一覧ページ)。"""
    m = parse_frontmatter(exp_dir / "REPORT.md") or {}
    exp_id = _esc(m.get("experiment_id") or exp_dir.name)
    jira = _esc(str(m.get("jira") or ""))
    status = str(m.get("status") or "")
    summ = _esc((m.get("summary") or "").strip())
    items = ""
    for i, s in enumerate(siblings):
        stchip = (f'<span class="chip ix-st">{_esc(s["status"])}</span>'
                  if s["status"] else "")
        badge = f'<span class="ix-type">{_esc(s["type"])}</span>' if s["type"] else ""
        items += (
            f'<li><a href="{s["href"]}">'
            f'<span class="ix-n">{i + 1}</span>'
            f'<span class="ix-main"><span class="ix-head">'
            f'<span class="ix-rid">{_esc(s["rid"])}</span>{badge}{stchip}</span>'
            f'<span class="ix-ttl">{_esc(s["title"])}</span></span></a></li>'
        )
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{exp_id} · reports</title>
<style>{css()}</style>
</head>
<body>
<header class="masthead"><div class="wrap">
<p class="rid">{exp_id}{(" · " + jira) if jira else ""}</p>
<h1>この実験のレポート一覧（{len(siblings)}件）</h1>
{f'<p class="deck">{summ}</p>' if summ else ""}
</div></header>
<div class="wrap">
<ol class="rv-index">{items}</ol>
<p class="foot">Read-view · 各レポートの HTML 読みビュー。正本は各 <code>.md</code>。</p>
</div>
</body>
</html>
"""


def _render_batch(exp_dir: Path, fold: bool, use_ledger: bool = True) -> int:
    targets = _collect_reports(exp_dir)
    if not targets:
        print(f"no reports under {exp_dir} (REPORT.md / reports/FL*-R*_*.md)", file=sys.stderr)
        return 1
    out_dir = exp_dir / "_generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    # 兄弟レポート一覧を一度だけ構築し、各レンダリングへ渡す(再スキャンを避ける)
    base = [_nav_info(p) for p in targets]
    n_ok, n_fail = 0, 0
    for md in targets:
        try:
            sibs = [{**s, "current": (s["stem"] == md.stem)} for s in base]
            out = out_dir / f"{md.stem}.readview.html"
            out.write_text(render_html(md, fold=fold, siblings=sibs, use_ledger=use_ledger),
                           encoding="utf-8")
            n_ok += 1
        except Exception as e:  # 1件の失敗で全体を止めない
            print(f"  FAIL {md.name}: {e}", file=sys.stderr)
            n_fail += 1
    # 実験のレポート一覧ページ
    try:
        (out_dir / "index.html").write_text(_index_html(exp_dir, base), encoding="utf-8")
    except Exception as e:
        print(f"  FAIL index.html: {e}", file=sys.stderr)
    print(f"read-view: {n_ok} generated (+index), {n_fail} failed -> {out_dir}")
    return 0 if n_fail == 0 else 1


def main(argv=None) -> int:
    # Windows コンソール(cp1252)で日本語パス出力が落ちるのを防ぐ
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description="レポート MD の HTML 読みビュー生成。MD ファイル単体、または実験"
        "ディレクトリ(REPORT.md + reports/FL*-R*_*.md を一括)を受ける。")
    ap.add_argument("md", type=Path, help="対象の <実験ID>-R###_*.md、または実験ディレクトリ")
    ap.add_argument("-o", "--out", type=Path, help="出力 HTML パス(単体時のみ)")
    ap.add_argument("--stdout", action="store_true", help="標準出力へ(単体時のみ)")
    ap.add_argument("--no-fold", action="store_true", help="セクションを畳まない")
    ap.add_argument("--no-ledger", action="store_true",
                    help="調査台帳(questions/sources/claims.jsonl)の重ね表示を無効化")
    args = ap.parse_args(argv)

    if not args.md.exists():
        print(f"error: not found: {args.md}", file=sys.stderr)
        return 2
    # ディレクトリなら一括モード
    if args.md.is_dir():
        return _render_batch(args.md, fold=not args.no_fold,
                             use_ledger=not args.no_ledger)
    html_out = render_html(args.md, fold=not args.no_fold,
                           use_ledger=not args.no_ledger)
    if args.stdout:
        sys.stdout.write(html_out)
        return 0
    out = args.out or _default_out(args.md)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_out, encoding="utf-8")
    print(f"wrote {out}  ({len(html_out)//1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
