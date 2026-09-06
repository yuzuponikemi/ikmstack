---
name: exp-artifact
description: Publish an experiment's REPORT.md as a readable, self-contained web article (an Artifact on claude.ai) and hand back the private link — extract the skeleton machine-readably (primary-record index, typed retraction ledger from frontmatter, figure inventory), turn the report's tables into validated charts, clear the pre-share gate, verify both themes and narrow widths locally, then publish. Solves "a long lab report is unreadable as markdown on GitHub"; the link opens directly in the Claude app. NOT a slide deck (that is exp-deck), NOT a local figure preview (that is regen-outputs), NOT a number re-derivation (that is report-checksum). Use when an experiment should become something a person can read ("レポートを記事にして", "読みやすい形で公開して", "Artifact にして", "記事化して", "リンクで読めるようにして", "ホームページの記事みたいにまとめて").
---

# exp-artifact — 実験を「読み物」として公開する

`REPORT.md`（作業記録）を、**リンク1本で読める自己完結の HTML 記事**に変換し、Artifact として
公開します。既定で非公開、claude.ai ホスト、Claude app からそのまま開けます。

**解く問題**: 長い実験レポートを GitHub の markdown で読むのは辛い。図が git に無いので
一次記録は素の表のまま読むことになる。`_generated/*.readview.html` は見やすいがローカル限定で、
リンクが無いので人に渡せない。

## 何をしないか（隣のスキルとの切り分け）

| したいこと | 使うもの |
|---|---|
| 他メンバーに配る編集可能な報告スライド (.pptx) | `/exp-deck` |
| 図を再生成してローカルで markdown をプレビュー | `/regen-outputs` |
| レポートの数値を独立に再計算して検算する | `/report-checksum` |
| **リンクで読める記事にして人に渡す・後から読み返す** | **本スキル** |

## Step 0: 作業ディレクトリを解決（必須）

対象の実験は**記録層（ノート）の中**にある。プロダクト repo から起動された場合も、まずノート根へ移動する:

```bash
cd "$(python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" notebook)"
```

詳細は [記録のルーティング規約](../../../docs/conventions/record-routing.md)。

## Step 1: 骨組みを機械で取り出す（一次記録を手で書き写さない）

```bash
python3 "$(cat ~/.ikmstack/install-path)/tools/exp_artifact.py" \
  skeleton experiments/E013_multi-agent-collaboration
```

メタ・一次記録の一覧・**撤回台帳**・図の在庫・ゲートの有無を JSON で返す。記事の事実部分は
すべてここから引く。**`REPORT.md` の散文を読んで台帳を組み立て直してはいけない。**

> 実際に起きた失敗: 手作業で E013 の記事を作ったとき、撤回16行を `REPORT.md` の表から
> 手で転記し、「16件のうち11件は自分で見つけた」という**どこにも無い数字**を書いた。
> フロントマターを引けば14件・全件 `self` と機械で出る。

**撤回は機械可読に記録されている。** 一次記録のフロントマターの `corrects:` /
`retraction_type:` / `discovered_by:` が台帳の入力で、`skeleton` はこれを読む。
統制語彙（`wrong-metric` / `unexcluded-confounder` ほか）は記事側でもそのまま見出しに使える。
正本: `docs/conventions/reporting.md`「改訂・撤回の記録」 <!-- policy:retraction-record@b39a00ca -->

撤回台帳は**この記事の中心装置**として扱う。実験が信じるのをやめた主張の一覧は、
たいてい結果の節より情報量が多い。訂正の連鎖（R028→R029→R030 のような）は `corrects` を
辿れば出るので、そのまま構造として見せる。

## Step 2: 図をそろえる

`skeleton` の `figures` が空で `regenerate_sh: true` なら、図はまだローカルに無い（図は git に
入らない — 正本: [figures-regen.md](../../../docs/conventions/figures-regen.md)）。先に `/regen-outputs`
を回す。Artifact は外部ホストを取得できないので、**図は data URI で埋め込む**。

図が1枚も無い実験（数値が表にしか無い）はむしろ普通で、そのときは **表を図にするのが
この記事の付加価値**になる。元の markdown にも読みビューにも無い増分はここで出る。

## Step 3: 共有前ゲートを通す（公開は「外に出す」ことである）

```bash
python3 "$(cat ~/.ikmstack/install-path)/tools/dr/dr_gate.py" experiments/<ID>/reports/claims.jsonl
```

検証は平場では行わず、**主張が外に出る直前**に、その成果物に載る判断駆動数値だけを潰す。
これを **共有前ゲート**と呼ぶ。台帳が無ければ「記事に載る数値を列挙し、出典 or 再計算で
1件ずつ潰す」でよい。潰せなかった数値は記事から落とすか「暫定」と明記する。
正本: `docs/conventions/reporting.md`「いつ検証するか — 共有前ゲート」 <!-- policy:verify-before-sharing@38a1a7de -->

**台帳全体の FAIL は、公開を止める理由にならない。** ゲートは台帳の全主張を見るが、
このゲートの対象は**記事に載る数値だけ**である。落ちた主張が記事に出てこないなら、
それは実験側の未決事項であって記事の欠陥ではない（実験がその FAIL を自分の限界として
記録しているかは確認する）。逆に、**落ちた主張を記事が引いているなら公開しない。**

Artifact は既定で非公開だが、**リンクを渡した時点で外に出る**。公開してから直すのではなく、
公開する前に通すこと。

## Step 4: 記事を設計して書く

1. **`artifact-design` スキルを読む**（必須。Artifact を書く前の義務）。図を描くなら
   **`dataviz` スキルも読む**。
2. **配色は新規に決めない。** ラボの既存ブランドを継承する — 正本は
   `.claude/skills/exp-deck/brand/tokens.py`（紫 `#531872` 系）。読みビュー
   （`tools/readview/theme.py`）も同じトークンを引いているので、記事・読みビュー・
   スライドが同じラボの見た目に揃う。
3. **図の系列色は検証器に通す。** 検証済みの2系列は
   light `#8B4AA6` + `#C77D2E` / dark `#9F6EC2` + `#C4832E`（全項目 PASS）。
   3系列以上にするなら再検証が要る（緑を足すと protan ΔE 7.1 で WARN → 直接ラベル必須）。
4. **各図に出典行を置く**（`出典 R031 §2` のように一次記録 ID を書く）。Step 6 の検査が
   これを見る。

構成・文体・アンチパターンは [exp-artifact 詳細ガイド](references/artifact_guide.md) を読むこと。

## Step 5: ローカルで見る（公開前）

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --hide-scrollbars --virtual-time-budget=8000 --window-size=1000,2400 \
  --screenshot=shot.png "file://$PWD/preview.html"
```

`preview.html` は書いた HTML を `<!doctype html><head>…</head><body>` で包んだもの
（Artifact 側は公開時に同じ骨組みを付ける）。**ライト・ダークの両方**と**狭幅**を見る。

> **headless Chrome の最小ウィンドウ幅は 500px。** `--window-size=390,…` を指定しても
> 画像が 390px に切られるだけで、レイアウトは 500px で組まれる。本文が切れて見えても
> レイアウト崩れとは限らない。真の狭幅は 380px の `<iframe>` に入れて
> `documentElement.scrollWidth` を測る（`clientWidth` と一致すれば横スクロール無し）。

## Step 6: 実験と突き合わせる（捏造引用と出典欠落の検査）

```bash
python3 "$(cat ~/.ikmstack/install-path)/tools/exp_artifact.py" \
  check experiments/<ID> article.html
```

(a) 存在しない一次記録を引いていないか (b) 各 `<figure>` が出典を持つか、を見る。
**数値が正しいかは見ない**（それは Step 3 と `/report-checksum` の役目）。見るのは
読者がその数字を辿れるかだけ。回帰テストは `exp_artifact.py selftest`。

## Step 7: 公開してリンクを記録する

Artifact ツールで公開し、返ってきた URL を**実験の側に書き戻す**（`REPORT.md` 冒頭の
リンク行）。書き戻さないと、次のセッションが同じ実験の記事を**別の URL で作り直す**。
更新は同じファイルパスで再公開すれば同じ URL に載る。

## アンチパターン

- **`REPORT.md` の散文から台帳を組み直す** → `skeleton` を使う。手写しは数字を作る。
- **図の出典行を省く** → Step 6 で落ちる。落ちなくても読者が辿れない。
- **配色を新しく決める** → ラボの見た目が実験ごとにバラつく。ブランドトークンを引く。
- **一次記録33本を全部 Artifact にする** → 記事は実験1本につき1枚。個別の一次記録は
  読みビュー（`/regen-outputs`）で足りる。読みたいものだけ都度公開する。
- **公開してから検証する** → 共有前ゲートは公開の前。

## 関連

- 記事の構成・文体・検証の詳細: [references/artifact_guide.md](references/artifact_guide.md)
- スライドで配る: `/exp-deck` ／ ローカルで図付きプレビュー: `/regen-outputs`
- 数値の独立再計算: `/report-checksum` ／ 自走性の検査: `/readability-review`
