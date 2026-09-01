"""ledger.py — 読みビューに調査3台帳(questions/sources/claims)を重ねる層。

読み手が散文の `(claim:cNNN)` を見たときに「その数値は何を出典に、どういう逐語引用で
支えられているのか」を、別ファイルを開かずに確かめられるようにする。台帳を機械可読に
しておいた見返りをそのまま読書体験に変換するのがこのモジュールの役目。

やること:
  - 散文中の `(claim:cNNN)` / `Q<n>` / `s<nnn>` を色チップに変換
    （色は主張の stance = 下位問いの作業仮説に対する立場。緑=supports/赤=refutes/黄=neutral）
  - チップにマウスオーバー(またはフォーカス)で右のパネルに台帳の中身を表示。クリックで固定
  - ツールバーにゲート状態のピル(決着数・採用/棄却・独立検証の進捗)

台帳が無ければ何もしない(従来どおりの出力)。report_readview.py 側は
`load()` が None を返したら素通りする。

正本のスキーマ: tools/dr/research_schema.md(questions/sources) と
tools/dr/claims_schema.md(claims)。
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

LEDGER_FILES = ("questions.jsonl", "sources.jsonl", "claims.jsonl")


# ------------------------------------------------------------------ load
def _read_jsonl(p: Path) -> list[dict]:
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue          # 壊れた行で読みビュー全体を落とさない
    return rows


def load(md_path: Path) -> dict | None:
    """レポートの隣(または実験の reports/)から3台帳を読む。無ければ None。"""
    for d in (md_path.parent, md_path.parent / "reports"):
        if all((d / f).exists() for f in LEDGER_FILES):
            q = _read_jsonl(d / "questions.jsonl")
            s = _read_jsonl(d / "sources.jsonl")
            c = _read_jsonl(d / "claims.jsonl")
            if not c and not q:
                return None
            return {
                "questions": {r["question_id"]: r for r in q if "question_id" in r},
                "sources": {r["source_id"]: r for r in s if "source_id" in r},
                "claims": {r["claim_id"]: r for r in c if "claim_id" in r},
            }
    return None


# ------------------------------------------------------------------ chips
_CODE_OPEN = re.compile(r"<code\b", re.I)
_CODE_CLOSE = re.compile(r"</code>", re.I)


def chipify(body_html: str, led: dict) -> str:
    """本文 HTML 中の台帳参照をチップへ。タグ属性と <code> の中身は触らない。"""
    claims, questions, sources = led["claims"], led["questions"], led["sources"]

    def claim_chip(cid: str) -> str:
        st = (claims[cid].get("stance") or "neutral")
        return (f'<span class="lchip lc-{html.escape(st)}" data-lk="claim" '
                f'data-li="{cid}" tabindex="0" role="button">{cid}</span>')

    # 1) `(claim:cNNN)` は多くが `<code>` に包まれている。包み込みごと差し替える。
    body_html = re.sub(
        r"<code>\(claim:(c\d+)\)</code>",
        lambda m: claim_chip(m.group(1)) if m.group(1) in claims else m.group(0),
        body_html)
    body_html = re.sub(
        r"\(claim:(c\d+)\)",
        lambda m: claim_chip(m.group(1)) if m.group(1) in claims else m.group(0),
        body_html)

    # 2) Q<n> / s<nnn> はタグの外・<code> の外のテキストだけを対象にする。
    def q_sub(m):
        qid = m.group(0)
        if qid not in questions:
            return qid
        return (f'<span class="lchip lc-q" data-lk="question" data-li="{qid}" '
                f'tabindex="0" role="button">{qid}</span>')

    def s_sub(m):
        sid = m.group(1)
        if sid not in sources:
            return m.group(0)
        return (f'<span class="lchip lc-s" data-lk="source" data-li="{sid}" '
                f'tabindex="0" role="button">{sid}</span>')

    parts = re.split(r"(<[^>]+>)", body_html)
    depth = 0
    for i, part in enumerate(parts):
        if i % 2:                                  # タグそのもの
            if _CODE_OPEN.match(part):
                depth += 1
            elif _CODE_CLOSE.match(part):
                depth = max(0, depth - 1)
            continue
        if depth:                                  # <code> の中は素通し
            continue
        part = re.sub(r"\bQ[1-9][0-9]?\b", q_sub, part)
        parts[i] = re.sub(r"\b(s\d{3})\b", s_sub, part)
    return "".join(parts)


# ------------------------------------------------------------------ pills
def pills(led: dict) -> str:
    """ツールバー用のゲート状態ピル。数えるのは台帳であって散文ではない。"""
    q = list(led["questions"].values())
    s = list(led["sources"].values())
    c = list(led["claims"].values())
    closed = sum(1 for r in q if r.get("status") == "closed")
    openq = sum(1 for r in q if r.get("status") in ("open", "abandoned"))
    adopted = sum(1 for r in s if r.get("decision") == "adopted")
    rejected = sum(1 for r in s if r.get("decision") == "rejected")
    dd = sum(1 for r in c if r.get("risk") == "decision_driving")
    ver = sum(1 for r in c
              if (r.get("verification") or {}).get("status") == "verified"
              and r.get("risk") == "decision_driving")

    def p(text, kind=""):
        return f'<span class="lpill {kind}">{html.escape(text)}</span>'

    out = [p(f"下位問い {closed}/{len(q)} 決着", "ok" if q and not openq else "warn")]
    out.append(p(f"出典 {adopted}採用/{rejected}棄却"))
    out.append(p(f"主張 {len(c)}（判断駆動 {dd}）"))
    if dd:
        out.append(p(f"独立検証 {ver}/{dd}", "ok" if ver == dd else "ng"))
    return "".join(out)


# ------------------------------------------------------------------ css
def css() -> str:
    return """
.lchip{display:inline-block;font-family:var(--mono);font-size:.72em;line-height:1.5;
  padding:.04em .4em;border-radius:6px;cursor:pointer;background:var(--surface-2);
  border:1px solid var(--line);vertical-align:.08em;white-space:nowrap;
  transition:background .12s,border-color .12s;}
.lchip:hover,.lchip:focus{outline:none;border-color:currentColor;background:transparent;}
.lchip.lc-supports{color:var(--green);}
.lchip.lc-refutes{color:var(--red);}
.lchip.lc-neutral{color:var(--amber);}
.lchip.lc-q{color:var(--purple-head);}
.lchip.lc-s{color:var(--muted);}
.lchip.pinned{box-shadow:0 0 0 2px color-mix(in srgb,currentColor 32%,transparent);}
.lpill{font-size:.7rem;padding:.14rem .5rem;border-radius:999px;border:1px solid var(--line);
  background:var(--surface-2);color:var(--muted);white-space:nowrap;}
.lpill.ok{color:var(--green);border-color:color-mix(in srgb,var(--green) 42%,var(--line));}
.lpill.ng{color:var(--red);border-color:color-mix(in srgb,var(--red) 42%,var(--line));}
.lpill.warn{color:var(--amber);border-color:color-mix(in srgb,var(--amber) 42%,var(--line));}
#lv-panel{position:fixed;right:1rem;top:4.2rem;width:min(27rem,42vw);z-index:40;
  max-height:calc(100vh - 5.6rem);overflow-y:auto;background:var(--surface);
  border:1px solid var(--line-2);border-radius:12px;padding:.9rem 1rem 1.1rem;
  box-shadow:0 2px 4px rgba(0,0,0,.06),0 16px 40px rgba(0,0,0,.14);
  font-size:.86rem;line-height:1.7;}
#lv-panel[hidden]{display:none;}
@media (max-width:1180px){
  #lv-panel{right:0;left:0;top:auto;bottom:0;width:auto;max-height:56vh;
    border-radius:12px 12px 0 0;border-left:none;border-right:none;border-bottom:none;}
}
.lv-h{font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.09em;
  display:flex;align-items:center;gap:.5rem;}
.lv-id{font-family:var(--mono);font-size:1.02rem;font-weight:700;color:var(--ink);margin:.15rem 0 0;}
.lv-b{display:flex;gap:.3rem;flex-wrap:wrap;margin:.55rem 0 .3rem;}
.lv-b span{font-size:.66rem;padding:.1rem .45rem;border-radius:999px;
  border:1px solid var(--line);color:var(--muted);}
.lv-b .supports{color:var(--green);} .lv-b .refutes{color:var(--red);}
.lv-b .neutral{color:var(--amber);} .lv-b .driving{color:var(--purple-head);}
.lv-b .verified{color:var(--green);} .lv-b .unverified{color:var(--red);}
.lv-k{font-size:.66rem;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;
  margin:.8rem 0 .12rem;}
.lv-v{font-size:.85rem;line-height:1.7;color:var(--ink);}
.lv-q{font-family:var(--mono);font-size:.78rem;line-height:1.62;background:var(--code-bg);
  color:var(--code-ink);border-left:3px solid var(--line-2);padding:.55rem .7rem;
  border-radius:0 6px 6px 0;max-height:15rem;overflow:auto;white-space:pre-wrap;
  word-break:break-word;}
.lv-x{margin-left:auto;font:inherit;font-size:.72rem;border:1px solid var(--line);
  background:var(--surface-2);color:var(--muted);border-radius:6px;padding:.08rem .45rem;
  cursor:pointer;}
"""


# ------------------------------------------------------------------ panel + js
def panel() -> str:
    return '<div id="lv-panel" hidden></div>'


def script(led: dict) -> str:
    data = json.dumps(led, ensure_ascii=False).replace("</", "<\\/")
    return """
<script>
(function(){
  const LED = __DATA__;
  const panel = document.getElementById('lv-panel');
  if (!panel) return;
  let pinned = null;
  const esc = s => { const d=document.createElement('div'); d.textContent = s==null?'':String(s); return d.innerHTML; };
  const row = (k,v) => v ? '<div class="lv-k">'+esc(k)+'</div><div class="lv-v">'+v+'</div>' : '';
  const head = (label,id) => '<div class="lv-h">'+esc(label)+
      '<button class="lv-x" data-lvclose>閉じる</button></div><div class="lv-id">'+esc(id)+'</div>';

  function claimView(id){
    const c = LED.claims[id]; if(!c) return '';
    const s = LED.sources[c.source_id];
    const ver = (c.verification && c.verification.status) || 'unverified';
    const src = s
      ? esc(s.title) + '<br><span class="lv-k" style="margin:0">' + esc(s.publisher||'') +
        ' ・ tier=' + esc(s.tier||'') + '</span><br><a href="' + esc(c.source_url||s.url||'') +
        '" target="_blank" rel="noopener">出典を開く</a>' +
        (s.snapshot ? '<br><span class="lv-k" style="margin:0">snapshot: ' + esc(s.snapshot) + '</span>' : '')
      : esc(c.source_url||'');
    return head('主張', id) +
      '<div class="lv-b"><span class="'+esc(c.stance||'neutral')+'">'+esc(c.stance||'neutral')+'</span>'+
      '<span class="'+(c.risk==='decision_driving'?'driving':'')+'">'+esc(c.risk||'')+'</span>'+
      '<span class="'+esc(ver)+'">'+esc(ver)+'</span>'+
      (c.question_id?'<span>'+esc(c.question_id)+'</span>':'')+'</div>'+
      row('主体 / 属性', esc(c.subject)+' — '+esc(c.attribute)) +
      row('値', esc(c.value_raw)) +
      row('逐語引用', '<div class="lv-q">'+esc(c.verbatim_quote)+'</div>') +
      row('出典', src) +
      row('取得日', esc(c.source_accessed)) +
      row('実体の注記', c.entity_check ? esc(c.entity_check.entity_note) : '') +
      row('検証の注記', c.verification ? esc(c.verification.verdict_note) : '');
  }
  function questionView(id){
    const q = LED.questions[id]; if(!q) return '';
    return head('下位問い', id) +
      '<div class="lv-b"><span class="'+(q.status==='closed'?'verified':'')+'">'+esc(q.status)+'</span>'+
      (q.confidence?'<span>確度 '+esc(q.confidence)+'</span>':'')+
      (q.refutation_searched?'<span class="supports">反証探索済</span>':'')+'</div>'+
      row('問い', esc(q.question)) +
      row('決着条件', esc(q.closing_condition)) +
      row('答え', esc(q.answer)) +
      row('注記', esc(q.note));
  }
  function sourceView(id){
    const s = LED.sources[id]; if(!s) return '';
    return head('出典', id) +
      '<div class="lv-b"><span class="'+(s.decision==='adopted'?'supports':'refutes')+'">'+esc(s.decision)+'</span>'+
      '<span>tier='+esc(s.tier)+'</span>'+
      (s.derived_from?'<span class="refutes">孫引き元 '+esc(s.derived_from)+'</span>':'')+'</div>'+
      row('タイトル', esc(s.title)) +
      row('発行元', esc(s.publisher)) +
      row('どう見つけたか', esc(s.found_via)) +
      row('棄却理由', esc(s.decision_reason)) +
      row('URL', '<a href="'+esc(s.url)+'" target="_blank" rel="noopener">'+esc(s.url)+'</a>') +
      row('スナップショット', esc(s.snapshot)) +
      row('注記', esc(s.note));
  }
  const view = (k,i) => k==='claim'?claimView(i):k==='question'?questionView(i):sourceView(i);
  function show(k,i){ const h = view(k,i); if(!h) return; panel.innerHTML = h; panel.hidden = false; panel.scrollTop = 0; }
  function close(){ pinned = null; panel.hidden = true;
    document.querySelectorAll('.lchip.pinned').forEach(e => e.classList.remove('pinned')); }

  document.querySelectorAll('.lchip').forEach(el => {
    const k = el.dataset.lk, i = el.dataset.li;
    el.addEventListener('mouseenter', () => { if(!pinned) show(k,i); });
    el.addEventListener('focus', () => { if(!pinned) show(k,i); });
    el.addEventListener('mouseleave', () => { if(!pinned) panel.hidden = true; });
    el.addEventListener('click', e => {
      e.preventDefault();
      document.querySelectorAll('.lchip.pinned').forEach(x => x.classList.remove('pinned'));
      if (pinned === el) { close(); } else { pinned = el; el.classList.add('pinned'); show(k,i); }
    });
    el.addEventListener('keydown', e => { if(e.key==='Enter'||e.key===' '){ e.preventDefault(); el.click(); } });
  });
  panel.addEventListener('mouseenter', () => { panel.hidden = false; });
  panel.addEventListener('mouseleave', () => { if(!pinned) panel.hidden = true; });
  panel.addEventListener('click', e => { if (e.target.closest('[data-lvclose]')) close(); });
  document.addEventListener('keydown', e => { if(e.key==='Escape' && !panel.hidden) close(); });
})();
</script>
""".replace("__DATA__", data)
