"""theme.py — 読みビューの CSS。ブランド配色は exp-deck/brand/tokens.py を単一ソースに流用。

パレット(紫/緑/橙/赤)はブランドトークンから、読みビュー固有の中立色(紫寄りの
グレー系)はここで定義する。ライト/ダーク両対応(prefers-color-scheme +
data-theme 上書き)。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

# --- brand tokens (single source) with safe fallback -------------------------
_FALLBACK = dict(
    PURPLE="531872", PURPLE_DEEP="3D1259", PURPLE_HEAD="6C2A87",
    GREEN="4E9D69", ORANGE="E89A51", RED="C0392B",
)


def _load_brand() -> dict:
    """exp-deck/brand/tokens.py から配色を取り込む。失敗時は _FALLBACK。"""
    root = Path(__file__).resolve().parents[2]  # repo root: tools/readview/ -> repo
    tokens_py = root / ".claude" / "skills" / "exp-deck" / "brand" / "tokens.py"
    try:
        spec = importlib.util.spec_from_file_location("_tc_brand_tokens", tokens_py)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return dict(
            PURPLE=mod.PURPLE, PURPLE_DEEP=mod.PURPLE_DEEP, PURPLE_HEAD=mod.PURPLE_HEAD,
            GREEN=mod.GREEN, ORANGE=mod.ORANGE, RED=mod.RED,
        )
    except Exception:
        return dict(_FALLBACK)


def css() -> str:
    b = _load_brand()
    h = lambda k: "#" + b[k]
    # 3つのトークン定義(ライト既定 / dark media / data-theme 明示上書き)を1関数で。
    return f"""
:root {{
  --purple:{h('PURPLE')}; --purple-deep:{h('PURPLE_DEEP')}; --purple-head:{h('PURPLE_HEAD')};
  --green:{h('GREEN')}; --amber:#C77D2E; --amber-bg:{h('ORANGE')}; --orange:{h('ORANGE')}; --red:{h('RED')};
  --ground:#FBFAFC; --surface:#FFFFFF; --surface-2:#F4F1F7;
  --ink:#2A2530; --ink-soft:#574F60; --muted:#857C90; --line:#E6E1EC; --line-2:#D7D0E0;
  --code-bg:#F5F2F8; --code-ink:#4A2E63;
  --grid:color-mix(in srgb, var(--muted) 22%, transparent);
  --font:"Segoe UI","Yu Gothic UI","Meiryo",system-ui,-apple-system,sans-serif;
  --mono:"Cascadia Code","Consolas",ui-monospace,"Menlo",monospace;
  --maxw:60rem; --radius:10px;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --ground:#15111A; --surface:#1D1824; --surface-2:#241E2D;
    --ink:#EDE8F2; --ink-soft:#C3BAD0; --muted:#9188A0; --line:#322A3D; --line-2:#3F3550;
    --code-bg:#241C30; --code-ink:#D3BEE8;
    --purple-head:#B98FD4; --green:#6FBE89; --amber:#E0A24E; --red:#E1685B; --orange:#E9A960;
  }}
}}
:root[data-theme="light"]{{--ground:#FBFAFC;--surface:#FFFFFF;--surface-2:#F4F1F7;--ink:#2A2530;--ink-soft:#574F60;--muted:#857C90;--line:#E6E1EC;--line-2:#D7D0E0;--code-bg:#F5F2F8;--code-ink:#4A2E63;--purple-head:{h('PURPLE_HEAD')};--green:{h('GREEN')};--amber:#C77D2E;--red:{h('RED')};--orange:{h('ORANGE')};}}
:root[data-theme="dark"]{{--ground:#15111A;--surface:#1D1824;--surface-2:#241E2D;--ink:#EDE8F2;--ink-soft:#C3BAD0;--muted:#9188A0;--line:#322A3D;--line-2:#3F3550;--code-bg:#241C30;--code-ink:#D3BEE8;--purple-head:#B98FD4;--green:#6FBE89;--amber:#E0A24E;--red:#E1685B;--orange:#E9A960;}}

*{{box-sizing:border-box;}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:var(--font);line-height:1.7;font-feature-settings:"palt";-webkit-font-smoothing:antialiased;}}
.wrap{{max-width:var(--maxw);margin:0 auto;padding:0 1.4rem 6rem;}}
a{{color:var(--purple-head);text-underline-offset:2px;}}

.masthead{{background:linear-gradient(108deg,var(--purple-deep) 0%,var(--purple) 58%,var(--purple-head) 100%);color:#fff;padding:2.4rem 0 2rem;}}
.masthead .wrap{{padding-bottom:0;}}
.rid{{font-family:var(--mono);font-size:.82rem;letter-spacing:.04em;color:#E7D6F2;margin:0 0 .5rem;}}
.masthead h1{{font-size:clamp(1.45rem,3.5vw,2.05rem);line-height:1.32;font-weight:700;margin:0 0 .7rem;text-wrap:balance;letter-spacing:-.005em;}}
.masthead .deck{{margin:0 0 1.1rem;font-size:.95rem;line-height:1.65;color:#EBDCF6;max-width:56rem;}}
.meta{{display:flex;flex-wrap:wrap;gap:.5rem .55rem;margin:0;list-style:none;padding:0;}}
.meta li{{font-size:.72rem;padding:.2rem .6rem;border-radius:999px;background:rgba(255,255,255,.14);color:#F3E9FA;display:inline-flex;gap:.35rem;align-items:baseline;}}
.meta li b{{color:#fff;font-weight:600;}} .meta .k{{color:#D8C2E8;text-transform:uppercase;font-size:.62rem;letter-spacing:.08em;}}
.st-active{{background:rgba(111,190,137,.28)!important;}} .st-planning{{background:rgba(233,169,96,.28)!important;}}
.st-superseded,.st-historical{{background:rgba(133,124,144,.3)!important;}}

section.doc{{margin-top:1.6rem;}}
h2{{font-size:1.24rem;font-weight:700;margin:0 0 .9rem;padding-bottom:.45rem;border-bottom:2px solid var(--purple);}}
h3{{font-size:1.02rem;font-weight:700;margin:1.5rem 0 .6rem;}}
h4{{font-size:.94rem;font-weight:700;margin:1.1rem 0 .5rem;color:var(--purple-head);}}
p{{margin:.7rem 0;}} strong{{color:var(--ink);}}
.rv-note,.muted{{color:var(--muted);}}
ul,ol{{padding-left:1.3rem;}} li{{margin:.35rem 0;}}

code{{font-family:var(--mono);font-size:.84em;background:var(--code-bg);color:var(--code-ink);padding:.08em .38em;border-radius:5px;word-break:break-word;}}
pre{{margin:.6rem 0;padding:1rem 1.1rem;background:var(--code-bg);border:1px solid var(--line);border-radius:var(--radius);overflow-x:auto;font-family:var(--mono);font-size:.82rem;line-height:1.6;color:var(--ink);}}
pre code{{background:none;padding:0;color:inherit;font-size:1em;}}

/* confidence chips */
.chip{{display:inline-flex;align-items:center;gap:.3rem;font-size:.68rem;font-weight:700;letter-spacing:.02em;padding:.1rem .5rem .12rem;border-radius:999px;white-space:nowrap;vertical-align:.06em;}}
.chip::before{{content:"";width:.5rem;height:.5rem;border-radius:50%;}}
.c-fix{{background:color-mix(in srgb,var(--green) 16%,transparent);color:var(--green);}} .c-fix::before{{background:var(--green);}}
.c-mid{{background:color-mix(in srgb,var(--amber) 18%,transparent);color:var(--amber);}} .c-mid::before{{background:var(--amber);}}
.c-warn{{background:color-mix(in srgb,var(--red) 15%,transparent);color:var(--red);}} .c-warn::before{{background:var(--red);}}
.c-hi{{background:color-mix(in srgb,var(--green) 22%,transparent);color:var(--green);}} .c-hi::before{{background:var(--green);}}

/* callouts (from blockquotes) */
blockquote{{margin:.8rem 0;border-radius:var(--radius);padding:.85rem 1.1rem;border:1px solid var(--line);border-left:4px solid var(--purple);background:var(--surface-2);color:var(--ink-soft);}}
blockquote p{{margin:.35rem 0;}} blockquote p:first-child{{margin-top:0;}} blockquote p:last-child{{margin-bottom:0;}}
blockquote.co-prem{{border-left-color:var(--purple);}} blockquote.co-term{{border-left-color:var(--green);}}
blockquote.co-warn{{border-left-color:var(--red);}} blockquote.co-note{{border-left-color:var(--amber);}}

/* tables */
.tbl-scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);margin:.7rem 0;}}
table{{border-collapse:collapse;width:100%;font-size:.85rem;min-width:34rem;font-variant-numeric:tabular-nums;}}
th,td{{text-align:left;padding:.55rem .75rem;border-top:1px solid var(--line);vertical-align:top;}}
thead th{{background:var(--surface-2);color:var(--purple-head);font-weight:700;font-size:.73rem;border-top:none;position:sticky;top:0;white-space:nowrap;}}
tbody tr:nth-child(even){{background:color-mix(in srgb,var(--surface-2) 45%,transparent);}}
td.num,th.num{{text-align:right;}}

/* math */
.math-inline{{font-family:"Cambria Math","STIX Two Math",var(--font);background:color-mix(in srgb,var(--purple) 6%,transparent);padding:.03em .3em;border-radius:5px;font-size:1.02em;}}
.math-block{{display:block;text-align:center;font-family:"Cambria Math","STIX Two Math",var(--font);background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:.8rem 1rem;margin:.7rem 0;overflow-x:auto;font-size:1.1em;}}
math{{font-family:"Cambria Math","STIX Two Math",var(--font);}}

/* figures */
.fig{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;margin:.9rem 0;}}
.fig-cap{{display:flex;gap:.55rem;align-items:baseline;padding:.6rem .9rem;border-bottom:1px solid var(--line);background:var(--surface-2);flex-wrap:wrap;}}
.fig-cap .badge{{font-size:.6rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:.12rem .5rem;border-radius:5px;background:color-mix(in srgb,var(--orange) 22%,transparent);color:var(--orange);}}
.fig-cap .t{{font-weight:600;font-size:.9rem;color:var(--ink);}}
.fig img{{display:block;width:100%;height:auto;}}
.fig .missing{{padding:1.4rem 1rem;text-align:center;color:var(--muted);font-size:.85rem;}}
.fig .src{{font-size:.68rem;color:var(--muted);padding:.45rem .9rem;border-top:1px solid var(--line);font-family:var(--mono);word-break:break-all;}}

/* details (progressive disclosure) */
details.det{{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);margin-top:.8rem;overflow:hidden;}}
details.det>summary{{cursor:pointer;padding:.8rem 1.1rem;font-weight:700;font-size:1.05rem;list-style:none;display:flex;align-items:center;gap:.6rem;color:var(--ink);}}
details.det>summary::-webkit-details-marker{{display:none;}}
details.det>summary .tw{{display:inline-block;transition:transform .18s ease;color:var(--purple-head);font-size:.8rem;}}
details.det[open]>summary .tw{{transform:rotate(90deg);}}
.det-body{{padding:0 1.1rem 1.1rem;}} .det-body>*:first-child{{margin-top:.5rem;}}
h2.open-sec{{margin-top:1.8rem;}}

/* toolbar */
.toolbar{{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--ground) 88%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:.5rem 0;}}
.toolbar .wrap{{display:flex;gap:.6rem;align-items:center;padding-bottom:0;width:100%;}}
.toolbar .tag{{font-family:var(--mono);font-size:.74rem;color:var(--muted);}} .toolbar .spacer{{flex:1;}}
/* レポート切替(前/次 + ドロップダウン + 一覧) */
.rv-switch{{display:flex;gap:.35rem;align-items:center;flex-wrap:wrap;}}
.rv-jump{{font:inherit;font-size:.78rem;max-width:min(46vw,22rem);padding:.3rem .5rem;border:1px solid var(--line-2);border-radius:7px;background:var(--surface);color:var(--ink);cursor:pointer;}}
.btn.nav-a{{padding:.3rem .6rem;font-weight:700;}}
.btn.disabled{{opacity:.4;pointer-events:none;}}
/* 実験レポート一覧ページ */
.rv-index{{list-style:none;margin:1.4rem 0 0;padding:0;display:flex;flex-direction:column;gap:.5rem;}}
.rv-index a{{display:flex;gap:.8rem;align-items:flex-start;padding:.8rem 1rem;border:1px solid var(--line);border-radius:10px;background:var(--surface);text-decoration:none;color:var(--ink);}}
.rv-index a:hover{{border-color:var(--purple);box-shadow:0 6px 20px -12px rgba(61,18,89,.5);}}
.ix-n{{flex:none;width:1.8rem;height:1.8rem;border-radius:8px;background:var(--surface-2);color:var(--purple-head);font-family:var(--mono);font-weight:700;display:grid;place-items:center;font-size:.85rem;}}
.ix-main{{display:flex;flex-direction:column;gap:.25rem;min-width:0;}}
.ix-head{{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;}}
.ix-rid{{font-family:var(--mono);font-size:.82rem;color:var(--purple-head);font-weight:700;}}
.ix-type{{font-size:.66rem;padding:.08rem .45rem;border-radius:5px;background:var(--surface-2);color:var(--muted);}}
.chip.ix-st{{background:var(--surface-2);color:var(--ink-soft);}} .chip.ix-st::before{{background:var(--muted);}}
.ix-ttl{{font-size:.92rem;color:var(--ink-soft);line-height:1.55;}}
.btn{{font:inherit;font-size:.78rem;cursor:pointer;border:1px solid var(--line-2);background:var(--surface);color:var(--ink-soft);padding:.3rem .7rem;border-radius:7px;}}
.btn:hover{{border-color:var(--purple);color:var(--purple-head);}} .btn:focus-visible{{outline:2px solid var(--purple);outline-offset:2px;}}
.foot{{margin-top:3rem;font-size:.72rem;color:var(--muted);border-top:1px solid var(--line);padding-top:1rem;}}

/* アンカー飛び先が sticky ツールバーに隠れないよう余白 */
h2[id],details[id]{{scroll-margin-top:3.4rem;}}

/* 目次(ツールバーからのドロップダウン) */
.toc{{position:absolute;top:calc(100% + 4px);left:1.4rem;width:min(32rem,calc(100vw - 2.8rem));max-height:66vh;overflow:auto;
  background:var(--surface);border:1px solid var(--line-2);border-radius:10px;box-shadow:0 14px 44px -14px rgba(61,18,89,.55);padding:.4rem;z-index:40;}}
.toc[hidden]{{display:none;}}
.toc ol{{list-style:none;margin:0;padding:0;counter-reset:toc;}}
.toc li{{margin:0;counter-increment:toc;}}
.toc a{{display:block;padding:.4rem .7rem;border-radius:7px;color:var(--ink-soft);text-decoration:none;font-size:.88rem;line-height:1.5;}}
.toc a::before{{content:counter(toc) ". ";color:var(--purple-head);font-family:var(--mono);font-size:.8em;}}
.toc a:hover{{background:var(--surface-2);color:var(--purple-head);}}
.toc a.active{{background:color-mix(in srgb,var(--purple) 12%,transparent);color:var(--purple-head);font-weight:700;box-shadow:inset 3px 0 0 var(--purple);}}

/* 画像ライトボックス(クリックで拡大) */
.fig img{{cursor:zoom-in;}}
.lb{{position:fixed;inset:0;z-index:100;background:rgba(18,12,24,.86);display:flex;align-items:center;justify-content:center;padding:2rem;cursor:zoom-out;}}
.lb[hidden]{{display:none;}}
.lb img{{max-width:100%;max-height:100%;border-radius:8px;box-shadow:0 12px 48px rgba(0,0,0,.5);cursor:zoom-out;}}

/* 先頭へ戻る */
.totop{{position:fixed;right:1.1rem;bottom:1.1rem;z-index:50;width:2.6rem;height:2.6rem;border-radius:50%;
  border:1px solid var(--line-2);background:var(--surface);color:var(--purple-head);font-size:1.1rem;cursor:pointer;
  box-shadow:0 6px 20px -8px rgba(61,18,89,.5);}}
.totop[hidden]{{display:none;}}
.totop:hover{{border-color:var(--purple);}} .totop:focus-visible{{outline:2px solid var(--purple);outline-offset:2px;}}

@media (prefers-reduced-motion: reduce){{*{{transition:none!important;}}}}
"""
