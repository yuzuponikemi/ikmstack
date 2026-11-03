---
name: course-build
description: 任意の知識体系(自分たちの装置・システム・資格試験・学問分野)を、単元ごとの章別 HTML 学習ページ(各章にインタラクティブ図 3〜5 個・題材の数値での計算例・確認問題 8 問以上)と入口ページからなる学習コースに仕立てる。企画相談(章立て・取り込む材料・方向性を依頼者と決める)→ 一次資料ダイジェスト → 章仕様と記法の関門 → 章の並行執筆と自己検査 → 独立レビュー(数理・記法・目視)の順で品質を担保する。Use when "学習教材を作って", "〇〇の勉強ページを作りたい", "単元ごとの学習ページ", "インタラクティブな図解で学べる資料", "コースを作って", "資格試験の教材", "build a study course", "interactive learning pages".
---

# course-build — 章別インタラクティブ学習コースの作成

装置の光学教材と統計の教材を作った経験から、分野に依存しない骨格と
**プロファイル**(分野ごとの差し替え枠)に分けたもの。品質を生んだのは光学の知識ではなく次の 3 点:
一次資料を先にダイジェストに落とす / 章仕様を「満たさなければ未完成」の関門にする / 執筆者と別のレビュアーが数値を再計算する。
最初の版はこれを欠いて、「1 章 1.2 KB の要約」で完成扱いになった。

- 対話で教える(1 問ずつ質問する)だけなら `anthropic-skills:learn`。本スキルは**教材を作る**。完成後の演習は learn に渡す。
- PR の解説資料は `pr-review-doc`、報告スライドは `exp-deck`。

## 資材(このスキル内)

| パス | 役割 |
|---|---|
| `references/chapter-spec.md` | 章執筆仕様(必須構成・証拠の規律・自己検査・図の品質基準)。正本 |
| `references/profiles/exam-cert.md` | 資格試験・公開知識向けの差し替え枠(著作権の規律を含む) |
| `references/profiles/own-materials.md` | 一般知識(または装置・システム)を**自分たちの資料**(実データ・レポート・仕様書・論文の図)に紐づけて学ぶ枠 |
| `references/brief-template.md` | 企画書 `COURSE-BRIEF.md` の雛形(手順 0 でユーザーと合意する内容) |
| `references/writer-brief.md` / `reviewer-brief.md` | 執筆・査読エージェントへの共通指示の雛形(章固有の指示だけを足して渡す) |
| `assets/` | `course.css` / `course.js`(設定駆動)/ `_template.html` / `hub-template.html` |
| `scripts/new_course.py` | コースのひな形を作る(既存ファイルは上書きしない) |
| `scripts/check_chapter.py` | 静的関門(構成・問題数と区分・LAB 要素・id 重複・`node --check`・**記法**) |
| `scripts/browser_check.mjs` | 実行時関門(Playwright。例外・360px 横溢れ・KaTeX エラー・スクリーンショット。`SECTIONS=1` で節ごとの画像) |
| `scripts/setup_katex.sh` | クラウドで cdnjs が遮断されているとき、KaTeX をローカルに入れて `KATEX_DIST` を出力する |
| `scripts/selftest.py` | このスキル自身の自己検査(lint が全規則で落とせるか、全プロファイルの雛形生成、course.js)。スキルを編集したら必ず実行 |

以下のコマンドは `<プロジェクト>/.claude/skills/course-build/` に置いた場合のパスです。`~/.claude/skills/course-build/` に置いた場合は読み替えてください。

## 手順

### 0. 企画相談(最初に必ず。ユーザーと合意してから先へ進む)

章立てと「何に紐づけて理解させるか」で教材の価値が決まる。いきなり書き始めない(統計コース試作の反省: 一般教科書の順に書いたため、自分たちの仕事で使われている統計との接点が無かった)。

1. **材料の下調べ**(Explore エージェント 1 体、読み取り専用): 題材が自分たちの資料のどこで使われているか(実験レポート・仕様書・ナレッジベース・論文・装置の出力)を「トピック × 最良の実例 3〜5 件(path:行・数値・教材としての使い道)」で集める。社外題材なら標準的な範囲(出題範囲表・教科書の目次)も。
2. **企画書の草案** `<course>/COURSE-BRIEF.md` を `references/brief-template.md` から作る: 目的と読者、学んだ後にできること、錨(何の実例で理解させるか)、取り込む材料の候補表、章立て案(各章 = 概念 × 自分たちの実例)、試作範囲、置かないもの。
3. **ユーザーに相談する**(AskUserQuestion、1 回で 2〜4 問): 方向性(試験対策 / 自分たちの実例で理解 / 両立)、材料の優先順位、章立ての粒度、試作する章。推奨案を先頭に置く。返答で企画書を確定し、決定を企画書の「決定事項」に日付つきで書く。
4. プロファイルを決める: 資格試験・公開知識 → `exam-cert`、自分たちの資料(装置・システム・実データ・レポート)に紐づける → `own-materials`。
5. 置き場所: 任意のフォルダ(例: `courses/<slug>/`)。

```
python .claude/skills/course-build/scripts/new_course.py courses/<slug> --title "<コース名>" --tag "<TAG>" \
  --profile own-materials --chapters "C01:<章名>" "C02:<章名>" ...
```

`courses/<slug>/README.md` に現状(章の状態・公開 URL・未解決)を書く。方針は COURSE-BRIEF.md が正本。

### 1. 一次資料ダイジェスト(執筆より先。省略不可)

- 一次資料を読み、`authoring/sources/S1_<topic>.md`〜`Sn` に**出典つき**の事実・数値・定義・図の要点を書く(分割の目安はプロファイル)。章の執筆者はここだけを根拠にする。
- 資料間の食い違いは REPORT.md(REPORT.md が無いコースでは README.md)の **食い違い台帳**(`S2-C1`, `S2-C2`, … 章番号と紛れない接頭辞を付ける)に集める。
- `exam-cert`: 出典は節番号・定理番号で参照し、教科書・過去問の本文や図を写さない。

### 2. 章仕様と記号表を確定する

`new_course.py` が `authoring/CHAPTER-SPEC.md`(共通仕様 + プロファイル)を置く。コース固有の追加(読者の式の水準、錨の数値の一覧)を §1 に追記する。
**章をまたぐ記号表**(企画書 §4.5)をここで確定し、`authoring/sources/S2_*` に「章間の記法の約束」として書く。並行執筆の前に決めておかないと δ・σ と s・k のような記号が章ごとに割れる。

### 3. 章を書く(試作 → 全章)

- 1 章 = 1 エージェント(Agent ツール)で並行に書く。**並行起動の前に章数と体数をユーザーに伝えて了承を取る**(光学教材は執筆 13 + レビュー 6 体、統計教材の試作は執筆 3 + レビュー 3 + 監査 1 体)。Workflow ツールはユーザーが明示したときだけ。
- 共通部分は `references/writer-brief.md` を置き換えて scratchpad に置き、章ごとのプロンプトから参照させる。執筆エージェントへの指示に含めるもの: 担当章と前後の章の範囲、`COURSE-BRIEF.md` の該当章(概念 × 実例)、`authoring/CHAPTER-SPEC.md`(特に §2.5 記法)と `sources/` のパス、雛形 `chapters/_template.html`、id 接頭辞(`cNN-`)、**REPORT/README と他章は編集しない**こと、スクリーンショットは scratchpad にだけ保存すること、§5 の自己検査の結果を返すこと。
- 章が関門を通ったら `assets/course-config.js` の該当行から `"todo"` を外し、`summaries` に 1 行要約を書く。

### 4. 関門(自己検査)

```
python .claude/skills/course-build/scripts/check_chapter.py <course>/chapters/C*.html
node .claude/skills/course-build/scripts/browser_check.mjs <scratchpad>/shots <course>/chapters/C*.html <course>/index.html
```

サンドボックスで cdnjs が遮断されていると数式が描画されず TeX の誤りを検出できない。その場合は
`eval "$(sh .claude/skills/course-build/scripts/setup_katex.sh <scratchpad>/katex)"` で `KATEX_DIST` を設定してから browser_check を実行する(cdnjs の要求をローカルから返す)。info の `katex=` が 0 なら数式は未検証。

両方 PASS + 計算の再計算(`authoring/verify/Cxx_verify.py` を残す)+ **節ごとの目視**:
`SECTIONS=1` を付けて browser_check を回し、`<name>-sNN.png` を 1 枚ずつ Read で見る。全体の縮小画像では数式の書体の混在・大きさ・行間は判断できない。
目視の観点: 地の文と数式で同じ記号の書体が揃っているか / 演算子(E, Var, Cov)が立体で統一されているか / 数式が本文より大きすぎないか / 図中のラベルが数式と同じ書体か / 文字の重なり・切れ。

### 5. 独立レビュー

- 共通部分は `references/reviewer-brief.md`。元資料の訂正候補は執筆者・査読者が報告に書き、編集者(主セッション)が `authoring/review/corrections.md` に集約する。
- 執筆者と別のエージェントが章ごとに次を点検する: 出典の追跡 / 計算・物理・数理の再導出 / 証拠のバッジと台帳の一致 / 図と本文の一致 / 教え方の重大な誤り / **記法と組版**(§2.5。節ごとの画像を実際に見る。見ていなければ「目視未実施」と記録する)。記録は `authoring/review/R-<章>.md`。
- 2 章以上なら最後に**章間監査**(同じ事項の記述・記号・定義・記法が章をまたいで食い違っていないか。読み取り専用)を 1 体で行い、修正は 1 人の編集者がまとめて行う。

### 6. 公開

- 入口 `index.html` の到達目標・台帳・一次資料を埋める。
- Artifact で公開する: `file_path` = `index.html`、`files` = `assets/*` と `chapters/C*.html`(`_template.html` は除く)。同じ `file_path` で再公開すると URL が保たれる。
- コースの README/REPORT に Artifact URL と現状(完成章・未完成章・未解決の台帳)を書く。

## 試作から得た教訓(統計コースの試作)

- 章立てを相談せずに書くと、正しくても「自分ごと」にならない教材になる → 手順 0。
- 数理の正しさは独立レビューで担保できたが、記法の揺れ(Cov の書体、地の文のギリシャ文字、等幅の計算ブロック)は誰も見ていなかった → 記法の lint と節ごとの目視を関門に入れた。
- 共通 CSS の不具合は最初の章で出る。試作で直してから全章に進む。
- 並行執筆では章ごとに記号・用語・表記が割れる(章間監査で 18 件)。企画書 §4.5 の記号表を執筆前に決め、章間監査は毎回行う。台帳番号は章番号と紛れない接頭辞にする。
- 元資料の数値は、下調べの要約(二次情報)と元ファイルで食い違うことがある。執筆者・査読者に元ファイルの path:行を必ず開かせる。


## このスキルを編集したとき

`python .claude/skills/course-build/scripts/selftest.py --browser` を実行して ALL PASS を確認する(lint の各規則が実際に落とせること、全プロファイルの雛形が生成できること、course.js が動くこと)。規則を足したら selftest の BAD フィクスチャにも足す。

## 完了報告に書くこと

章ごとの関門結果(check_chapter / browser_check、`katex=` が 0 でないこと)、再計算の一致状況、レビューで直した高重大度の件数、未解決の台帳項目、Artifact URL。満たせなかった仕様要素は「未完成」と明記する。
