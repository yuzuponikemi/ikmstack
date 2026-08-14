"""Build a generic brand HTML slide sample (demonstrates brand/brand.css usage).

Emits two files from one markup source:
  brand/sample.html                  full standalone doc (opens in a browser; links brand.css)
  <scratchpad>/sample_artifact.html  content-only, self-contained (inline CSS + data-URI images)
                                      for publishing as a claude.ai Artifact (CSP-safe)
Run: python .claude/skills/exp-deck/brand/build_sample.py <scratchpad_dir>
"""
import sys, base64, pathlib
import tokens as B  # sibling

HERE = pathlib.Path(__file__).parent
A = HERE / "assets"
scratch = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE


def b64(p, mime):
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


LOGO_DATA = b64(A / "logo.png", "image/png")
BG_DATA = b64(A / "background.png", "image/png")

# demo-only layout CSS (page, slide cards, title band, 2-col body, chart) — brand tokens drive color
DEMO_CSS = f"""
*{{box-sizing:border-box}}
body{{margin:0;background:#F2EEF5;font-family:"Segoe UI",Meiryo,system-ui,sans-serif;color:#{B.INK};
     -webkit-font-smoothing:antialiased}}
.wrap{{max-width:1180px;margin:0 auto;padding:40px 20px 64px}}
.lead{{color:#{B.GRAY};font-size:14px;margin:0 0 24px;line-height:1.6}}
.lead b{{color:#{B.PURPLE_HEAD}}}
.deck{{display:flex;flex-direction:column;gap:28px}}
.slide{{position:relative;aspect-ratio:16/9;background:#fff;border-radius:10px;overflow:hidden;
        box-shadow:0 6px 24px rgba(61,18,89,.16);border:1px solid #e7dcf0}}
.pad{{position:absolute;inset:0;padding:3.4% 3.6%}}
/* footer */
.ft{{position:absolute;left:0;right:0;bottom:0;height:8.5%;display:flex;align-items:center;
     justify-content:space-between;padding:0 2%;border-top:1px solid #{B.FOOTER_BG}}}
.ft img{{height:42%}}
.ft .pg{{font-size:12px;color:#{B.GRAY};font-variant-numeric:tabular-nums}}
.ft .cf{{font-size:11px;color:#{B.GRAY};letter-spacing:.04em}}
/* content header */
.h{{font-size:30px;font-weight:700;color:#{B.INK};margin:0;text-wrap:balance}}
.rule{{height:3px;background:#{B.PURPLE};width:100%;margin:10px 0 18px}}
/* body two-col */
.cols{{display:grid;grid-template-columns:1.05fr .95fr;gap:30px;align-items:start}}
grid-template-columns:1.05fr .95fr;gap:30px;align-items:start}}
ul.b{{list-style:none;margin:0;padding:0}}
ul.b li{{margin:0 0 9px;font-size:15px;line-height:1.5}}
ul.b li.head{{font-weight:700;color:#{B.PURPLE_HEAD};margin-top:4px}}
ul.b li.sub{{padding-left:1.1em;color:#{B.INK}}}
ul.b li.tradeoff{{font-weight:700;color:#{B.RED};margin-top:10px}}
ul.b li.tradeoff + li.sub{{color:#{B.RED}}}
.accent{{color:#{B.GREEN};font-weight:700}}
.src{{position:absolute;left:2%;right:2%;bottom:9.5%;font-size:11px;color:#{B.GRAY};line-height:1.4}}
/* title slide */
.title .band{{position:absolute;top:0;left:0;right:0;height:56%;
    background:linear-gradient(105deg,#{B.PURPLE_DEEP} 0%,#{B.PURPLE} 56%,#{B.PURPLE_HEAD} 100%)}}
.title .band img{{position:absolute;right:0;top:0;height:100%;width:46%;object-fit:cover;object-position:left center}}
.title .tx{{position:absolute;top:14%;left:4%;width:52%;color:#fff}}
.title h1{{font-size:34px;font-weight:700;margin:0;line-height:1.25;text-wrap:balance}}
.title .sub{{margin:14px 0 0;font-size:16px;color:#D9C6E6;line-height:1.5}}
.title .meta{{position:absolute;top:62%;left:4%;font-size:14px;color:#{B.INK}}}
.title .logo{{position:absolute;left:4%;bottom:6%;height:34px}}
/* chart */
.chart{{width:100%;height:auto}}
.cap{{text-align:center;font-size:12px;color:#{B.GRAY};font-style:italic;margin:8px 0 0}}
"""

# inline SVG bar chart (brand colors): absolute(raw) vs ratio metrics, robust CV %
CHART = f"""
<svg class="chart" viewBox="0 0 520 300" role="img" aria-label="throughput by runtime">
  <line x1="60" y1="250" x2="500" y2="250" stroke="#bbb" stroke-width="1"/>
  <line x1="60" y1="40" x2="60" y2="250" stroke="#bbb" stroke-width="1"/>
  {''.join(f'<line x1="60" y1="{250-v*42}" x2="500" y2="{250-v*42}" stroke="#eee" stroke-width="1"/>' for v in (1,2,3,4))}
  <text x="20" y="254" font-size="11" fill="#{B.GRAY}">0</text>
  <text x="8" y="{250-4*42+4}" font-size="11" fill="#{B.GRAY}">40</text>
  <text x="32" y="30" font-size="12" fill="#{B.INK}" font-weight="700">tok/s</text>
  <!-- bars: baseline(gray), 中間条件(purple), 最良(green) -->
  <g font-size="11" fill="#{B.INK}" text-anchor="middle">
    <rect x="92"  y="{250-1.2*42}" width="46" height="{1.2*42}" fill="#9a9a9a"/>
    <text x="115" y="268">baseline</text>
    <rect x="170" y="{250-1.9*42}" width="46" height="{1.9*42}" fill="#{B.PURPLE_HEAD}"/>
    <text x="193" y="268">条件 A</text>
    <rect x="248" y="{250-2.6*42}" width="46" height="{2.6*42}" fill="#{B.PURPLE}"/>
    <text x="271" y="268">条件 B</text>
    <rect x="326" y="{250-3.1*42}" width="46" height="{3.1*42}" fill="#{B.PURPLE}"/>
    <text x="349" y="268">条件 C</text>
    <rect x="404" y="{250-3.8*42}" width="46" height="{3.8*42}" fill="#{B.GREEN}"/>
    <text x="427" y="268">最良</text>
  </g>
</svg>
"""

def slides(logo, bg):
    return f"""
<div class="deck">

  <!-- 1. TITLE -->
  <section class="slide title" aria-label="表紙">
    <div class="band"><img src="{bg}" alt=""></div>
    <div class="tx">
      <h1>推論ランタイムの<br>横断ベンチマーク — 総論</h1>
      <p class="sub">同一プロンプトで何が言えて、何が言えないか — 「相対比較」という到達点と今後</p>
    </div>
    <div class="meta">E001　・　5 条件　・　データ範囲 2026-05〜2026-07</div>
    <img class="logo" src="{logo}" alt="Logo">
  </section>

  <!-- 2. CONTENT (figure + bullets + source) -->
  <section class="slide" aria-label="到達点">
    <div class="pad">
      <h2 class="h">到達点 — できるのは「相対比較」だった</h2>
      <div class="rule"></div>
      <div class="cols">
        <div>{CHART}<p class="cap">baseline 12 tok/s に対し、最良条件は 38 tok/s(同一機・同一プロンプトでの比較)。</p></div>
        <ul class="b">
          <li class="head">■ 条件を揃えれば環境差は打ち消える</li>
          <li class="sub">・ 絶対スループットは機種に依存するが、同一機での比なら安定して測れる。</li>
          <li class="head">■ 比は熱・電源状態に不感</li>
          <li class="sub">・ サーマルスロットリングや電源設定のゆらぎを除き、<span class="accent">設定の効果だけ</span>を抜き出せる。</li>
          <li class="tradeoff">■ 制約/トレードオフ: 絶対値は捨てている</li>
          <li class="sub">・ 他機種との絶対比較・SLA 判定には使えない(別系統の測定が要る)。</li>
        </ul>
      </div>
      <p class="src">データ: runs.csv(各実行のログから 1 実行 = 1 行に整理した中間データ)を 5 条件で集計し、
      baseline と各条件の tok/s を棒で比較。共通の環境要因を消すと相対精度が上がることを示す意図。(生成: scripts/bench_summary.py)</p>
    </div>
    <div class="ft"><span class="cf">Confidential</span><span class="pg">E001 ・ 2</span></div>
  </section>

  <!-- 3. DISCUSSION (full footer with logo) -->
  <section class="slide" aria-label="Discussion">
    <div class="pad">
      <h2 class="h">Discussion &amp; Future Work — 残された課題と論点</h2>
      <div class="rule"></div>
      <ul class="b">
        <li class="head">■ 未解決の課題(Future Work)</li>
        <li class="sub">・ 適用条件のしきい値は本データの経験則 → 機種・期間を増やして再校正。</li>
        <li class="sub">・ 常時モニタに載せる際のしきい値設計・誤検知許容度はこれから。</li>
        <li class="tradeoff">■ チームに問いたい論点(Discussion)</li>
        <li class="sub">・ 監視しきい値は実測床まで攻めてよいか? 運用側の誤検知許容度は?</li>
        <li class="sub">・ 絶対値のトレーサブルな評価系に投資すべきか?</li>
      </ul>
    </div>
    <div class="ft"><img src="{logo}" alt="Logo"><span class="pg">E001 ・ 3</span></div>
  </section>

</div>
"""


HEAD_NOTE = ('<p class="lead">これは <b>カスタム ブランド</b>のスライドスタイル・サンプル(HTML)。'
             '配色・字面は <b>brand/tokens.py</b> 単一ソース由来 — pptx(exp-deck)と同じトークンを使う。'
             '表紙=テーマカラーバンド+背景画像、コンテンツ=白地+テーマカラー罫線+テーマカラー見出し+<span class="accent">アクセントカラー強調</span>+'
             '<span style="color:#'+B.RED+';font-weight:700">赤の制約/トレードオフ</span>、各図に出典帯、'
             'フッターにロゴ+ページ番号。</p>')

TITLE = "ブランドスライドスタイル — サンプル"

# --- standalone full doc (links the reusable css) ---
standalone = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{TITLE}</title>
<link rel="stylesheet" href="brand.css">
<style>{DEMO_CSS}</style>
</head><body><div class="wrap">{HEAD_NOTE}{slides("assets/logo.png","assets/background.png")}</div></body></html>
"""
(HERE / "sample.html").write_text(standalone, encoding="utf-8")
print("wrote", HERE / "sample.html")

# --- content-only, self-contained (for Artifact: inline CSS + data-URI images) ---
artifact = f"""<title>{TITLE}</title>
<style>{DEMO_CSS}</style>
<div class="wrap">{HEAD_NOTE}{slides(LOGO_DATA, BG_DATA)}</div>
"""
out = scratch / "sample_artifact.html"
out.write_text(artifact, encoding="utf-8")
print("wrote", out)
