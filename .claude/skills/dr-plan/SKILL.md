---
name: dr-plan
description: Decompose one research topic into independently-closable sub-questions with explicit closing conditions, and write them to questions.jsonl so coverage can be checked by machine. This is the front half of deep research — run it before collecting anything. Use when starting an investigation of a topic rather than a measurement ("この件を深く調べたい", "ディープリサーチを始める", "調査の計画を立てて", "問いを分解して", "何を調べれば決着するのか整理して").
---

# dr-plan — 調査の問いを分解し、決着条件を決める

調査(ディープリサーチ)の**最初**に回す。主問いを、**独立に閉じられる下位問い**へ分解し、
それぞれに**決着条件**(何が確認できたら閉じてよいか)を書いて `questions.jsonl` にする。

**なぜ台帳にするか**: 決着条件が散文にしか無いと、網羅したかどうかが自己申告になる。
調査の撤回で最も多いのは誤記述ではなく**探索不足**(`absence-claim`)で、これは
「調べていない」と「調べたが無かった」が外から区別できないことに起因する。
台帳にすると `dr_coverage.py` が機械で数えられる。

## Step 0: 作業ディレクトリとツールを解決(必須)

調査も実験の一種なので**記録層(ノート)の中**に作る:

```bash
cd "$(python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" notebook)"
DR="$(cat ~/.ikmstack/install-path)/tools/dr"
```

以降の相対パスはここから解決する。`notebook 未登録` エラーなら
`./setup --notebook <dir>` を案内する。詳細は
[記録のルーティング規約](../../../docs/conventions/record-routing.md)。

## 前提: 実験ディレクトリがあること

無ければ先に `/exp-new` を回す(調査も `E###_<topic>` の実験として起こす。
専用の器は作らない — 記録層の構造を分岐させない)。以下 `<exp>` は
`experiments/E###_<topic>/` を指す。

## 手順

### 1. 主問い(research question)を1文で書く

`PLAN.md` の「目的」に**問いの形**で書く。「〜について調べる」ではなく
「〜は〜か」と書けるまで絞る。書けないうちは分解に進まない。

### 2. 下位問いに分解する

分解の単位は「**独立に閉じられるか**」。次の型のどれかに落ちるまで割る:

| 型 | 例 | 決着条件の作り方 |
|---|---|---|
| 事実問い | 「Xの仕様値はいくつか」 | 一次資料での確認 |
| 比較問い | 「XとYのどちらが速いか」 | 同条件の測定・比較データ |
| 因果問い | 「Xが速いのはZのためか」 | Z を変えた比較、または機序の一次説明 |
| 存在問い | 「Xの既知の失敗事例はあるか」 | **探索範囲を明示**した上での有無 |

- **存在問いは決着条件に探索範囲を書く**(「どこを探して無ければ『無い』と言うか」)。
  範囲の無い存在問いは決着しない。
- 3〜7問が目安。10問を超えるなら主問いが大きすぎるので、主問いを割って別実験にする。

### 3. 各下位問いに決着条件を書く

**決着条件とは「何が観測・確認できたらこの問いを閉じてよいか」を事前に書いた文**。
書けない問いは、まだ問いとして成立していない — 分解し直すか、決着させない探索と
割り切って `status: exploratory` にする(判断を駆動する問いには使わない)。
<!-- policy:research-question-closing@64ec663f -->

### 4. `questions.jsonl` を書く

`<exp>/reports/questions.jsonl` に1行1問で書く。スキーマの正本は
[research_schema.md](../../../tools/dr/research_schema.md)。着手時点は全て `status: open`:

```jsonc
{"question_id":"Q1","question":"<問い>","closing_condition":"<決着条件>","status":"open","answer":null,"confidence":null,"min_independent_sources":2,"refutation_searched":null,"parent":null,"note":null}
```

- `min_independent_sources` は既定 2。単一の公式仕様で足りる事実問いだけ 1 に落とし、
  **理由を `note` に書く**。
- 空の `sources.jsonl` と `claims.jsonl` も同時に作る(収集フェーズで埋まる):
  ```bash
  : > <exp>/reports/sources.jsonl
  : > <exp>/reports/claims.jsonl
  ```

### 5. スキーマを検証する

```bash
python3 "$DR/validate_research.py" <exp>/reports/questions.jsonl
```

### 6. commit 時ゲートに opt-in する

`<exp>/.dr-gate` に `questions:` を書くと、以降の commit で網羅ゲート(K1〜K4)が回る
(テンプレ: `experiments/_template/dr-gate.example`)。マーカが無い実験は構造的に発火しない。
<!-- policy:dr-gate-opt-in@fd4434e1 -->

```
ledger: reports/claims.jsonl
questions: reports/questions.jsonl
```

### 7. PLAN.md から台帳へリンクする

**下位問いの表を PLAN.md に写さない**(1機能=1権威)。正本は `questions.jsonl` で、
<!-- policy:living-vs-primary@134848f4 -->
`PLAN.md` には主問い・調査方針・台帳へのリンクだけを書く。二重に書くと必ず片方が腐る。

## 完了条件

- `questions.jsonl` が `validate_research.py` を通る
- 全ての下位問いに決着条件がある(`exploratory` を除く)
- `.dr-gate` に `questions:` がある

次は `/dr-collect`(探索と台帳埋め)。
