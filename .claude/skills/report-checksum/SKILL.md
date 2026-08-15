---
name: report-checksum
description: Build a per-report verification ("検算") notebook that independently re-derives a report's numbers AND the computation behind every figure it shows, then delivers it as a side-by-side (report ｜ verification) 2-pane scrollable HTML for human review. One report = one verification notebook. Use when asked to 検算する / 独立再計算で確かめる / 図の計算過程を検証 / double-programming a report / "この結果を検算して" / "レポートの数値と図を裏取りして".
---

# report-checksum — レポート単位の検算(独立再計算＋図の計算過程)

レポート1本が主張する数値と、**そのレポートが載せる各図を作るまでの計算過程**を、
パイプラインとは独立に計算し直して突き合わせる(＝検算)ノートブックを作る authoring スキル。
成果物は**本命レポートと検算を左右2ペインで並べたレビュー用 HTML**。

## 芯となる原則

- **1レポート1検算(per-report)**。実験単位ではない。主張の単位はレポートで、
  1実験は複数レポート(R001/R002…)を産み各々別のデータ取り扱いをする。対象は必ず1本の
  `E###-R###`。レポート1本の実験なら per-report は per-experiment に自然一致する。
  <!-- policy:report-naming-numbering@eb565f44 -->
- **カバレッジ = 数値表 + 図の計算過程を全部**。§結論の数値だけでなく、レポートが載せる
  **各図がエンコードする統計**(箱ひげの四分位・装置別/月次/群別の中央値やバンド・ソート順)を
  図ごとに独立再計算し、**図PNGと並べて**確認する。読者が最も気にするのは図の計算過程。
- **役割分担(偽の二択を避ける)**: パイプライン出力=被検査対象(subject)、ノートブック=
  独立再計算+突合。「pipeline を import するか書き直すか」ではない。import できるとは限らない
  (関数化されていない main() 集約が普通)ので、黒箱サブプロセス実行 or 出力CSV読み+ソース表示で足りる。
  黒箱実行は skeleton の `run_script()` を使う(**`encoding="utf-8"` 必須** — nbconvert カーネルは
  `-X utf8` なしで cp1252 デコードし `±`→`Â±` 化けが突合を黙って壊す。直実行では通るので気づきにくい)。

## 検算の2型(1レポート内に同居してよい)

- **型 i: 独立再計算 + 値突合**(集約・派生値・図の統計)。同じ生/中間データから別ルートで
  計算し、パイプライン出力(統計CSV・図が描く値)と突合。tolerance 超えが人間のレビュー対象。
  算法選択(パーセンタイル法・std自由度・重み付け)を**両方計算して並べ**、どちらが一致するかで暴く。
- **型 ii: 境界検査 + 件数突合**(独立な第二計算法が作れない一本道変換)。「出力を生むはずの
  入力があるのに出力が出ているか」= silent drop 検出。入口件数・状態別行数・スキーマ列の有無を突合。

## 担保する / 担保しない(スコープ — 偽の安心を防ぐ)

検算は**入力→出力の写像(計算)の正しさ**を締めるが、**入力と前提の正しさは担保しない**。
「全ゲート PASS=緑」を「レポート全体が正しい」と読ませないこと。side-by-side とまとめで
スコープを常に見えるようにする。

- **担保する**: ①算術・アルゴリズムの忠実性(式の取り違え・転記ミス・ラベル違いが無い)
  ②隠れた算法選択の可視化(percentile 法・std 自由度・センチネルのスコープ・重み付け・被覆係数)
  ③内部整合と境界(件数突合=silent drop 検出・単位・スライス取り違え)④多ルート一致で共有バグの確率を下げる。
- **担保しない**: ①**入力の真正性**(誤校正・誤ラベル・誤った定数 → 正しく計算された誤答を承認してしまう)
  ②**モデル/前提の妥当性**(線形性・現地の実測値・経験則の合否基準)③**独立性は不完全**(パイプラインの
  ソースを読んで検算を書く=アンカリング残余。方法をわざと変えて緩和するが完全な独立ではない)
  ④**出典の実在**(→ `dr-audit`)⑤**網羅性**(確かめた主張だけ。未チェックは未検証)。
- **前提は必ずレポート側に**: 検算はレポートの不確かさ章を**置き換えず補完する**。前提・限界・要確認は
  レポート本文に書き、検算はそれと整合する形で「計算は正しい/前提は外」を明示する。
- **再現性は入力ピン留めが前提**: 入力が固定されていないと検算は「今のデータと整合」しか言えない。
  data-era ドリフトは assert で縛らず情報提示に留める(§2 の作法)。
  正本: `docs/conventions/reporting.md`「データ由来の数値は入力をピン留めする」
  <!-- policy:report-input-pinning@b32fc5e6 -->

## 媒体・置き場・命名(固定)

- **正本 = jupytext percent `.py`**。`python file.py` で assert がそのまま exit code になる
  (検算ゲート化=pass 0/fail 1)。差分が git で読める。`.ipynb`/`.html` は使い捨て。
- **置き場 = 対象レポートの実験配下 `verification/`**、命名 `verify_<E###-R###>_<slug>.py`
  (レポートIDが主キー)。`verification/.gitignore` に `*.ipynb *.html __pycache__/` を置く
  (テンプレ: `templates/verification.gitignore`)。
- **成果物 = side-by-side review-view HTML**(既定)。単体で出さず本命レポートの readview HTML と
  2ペインで並べる。`templates/build_review_view.py` が shell を生成(iframe 2枚+ドラッグ幅調整、
  元HTML2本を使い回すので二重管理なし)。VSCode に同期並置機能は無いのでブラウザで開く。

## 表描画

- pandas 表は `print(df.to_string())` の `<pre>` だと崩れる。**Styler + `display()` で HTML table**
  にする(数値右寄せ・等幅・乖離セルは赤)。`display()` はカーネル実行時HTML/`python file.py` 時は
  無害な repr(ゲートは assert なので描画非依存)。ヘルパ `show(df, caption=, highlight=)` を
  スケルトンに用意(`templates/verify_skeleton.py`)。

## 手順

1. **対象レポート1本を決める**(`E###-R###`)。そのレポートが載せる**図と数値主張**を列挙する。
2. **被検査対象を同定**: レポートを生む pipeline スクリプト(抽出/集計/作図)と、その出力
   (中間CSV・統計CSV・図PNG)。各図の計算(グルーピング・フィルタ・パーセンタイル法)をソースで読む。
3. **整合した pipeline 出力を用意**(検算の前提): pipeline を1回回して中間CSV・統計CSV・図を
   **同一ランに揃える**(例: `python -X utf8 scripts/analyze.py` → `python scripts/plot.py`)。
   追跡CSVと gitignore 中間物の era がずれると型 i の件数突合が(正しく)落ちる。§1 の assert に
   「まず pipeline を回せ」を明記しておく。
4. **スケルトンから検算 .py を書く**: `templates/verify_skeleton.py` をコピーし、①入力サニティ
   ②data-era ドリフト(情報提供・非ゲート)③数値表の突合(型 i)④**図ごと**の計算過程検算
   (図PNG埋込+独立再計算表+不変条件 assert)⑤境界/件数突合(型 ii)⑥pipeline ソース表示 を埋める。
   捏造しない: 見つからない罠は degrade して正直に報告(例=生ログに無ければ「サンプルには無い」)。
5. **実行して HTML 化**:
   ```
   python -m jupytext --to ipynb verify_<id>.py -o verify_<id>.ipynb
   python -m nbconvert --to notebook --execute --inplace verify_<id>.ipynb
   python -m nbconvert --to html verify_<id>.ipynb
   ```
   (図PNGは `display(Image(...))` で出力に base64 埋込され、HTMLが自己完結する。)
6. **side-by-side を組む**(既定の成果物):
   ```
   python <skill>/templates/build_review_view.py \
     --report <exp>/_generated/<E###-R###>_*.readview.html \
     --verify <exp>/verification/verify_<id>.html \
     --out    <exp>/verification/review_<E###-R###>_side-by-side.html
   ```
   readview HTML が無ければ `python3 tools/report_readview.py <exp>/reports/<report>.md` で先に作る。
7. **開いて確認**: `! open <exp>/verification/review_<E###-R###>_side-by-side.html`(ブラウザ)。

## いつ使わない

- レポートに数値・図の主張が無い(方針/設計だけ)→ 検算対象が無い。
- エージェント生成レポートの出典・逐語引用の裏取り → `dr-audit`(出典再取得照合)が担当。
- 自走性(用語が単体で読めるか)→ `readability-review`。検算は算法・データ取り扱いの正しさが対象。

## 関連

- **図・HTML・中間物は git に入れない**(三大原則#1)。正本 `.py` だけコミット、
  `.ipynb`/`.html`/readview/shell は gitignore の使い捨て。正本: `docs/conventions/figures-regen.md`
- Notebook 規約: 検算 `.ipynb` はコミットしない(gitignore)ので出力クリア義務は自明に満たす。
  もし .ipynb をコミットする運用に変える場合はセル出力を必ずクリア。
  正本: `docs/conventions/repository-rules.md`「Notebook 規約」
