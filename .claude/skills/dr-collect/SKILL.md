---
name: dr-collect
description: Search for sources against a sub-question ledger and fill the source + claim ledgers as you read — recording rejected sources and their reasons, folding second-hand citations into their originals, snapshotting pages against link rot, and running a mandatory refutation search per question. This is the collection half of deep research; prose comes later. Use when gathering material for an investigation ("調べて集めて", "出典を集める", "調査を進めて", "ソースを当たって", "反証も探して").
---

# dr-collect — 探索して2つの台帳を埋める

`questions.jsonl` の下位問いに対して探索し、`sources.jsonl`(探索の記録)と
`claims.jsonl`(主張)を**読みながら**埋める。**散文はまだ書かない。**

**なぜ台帳が先か**: 散文を先に書くと、網羅の判断材料(何を探して何を採らなかったか)が
最後まで存在しない。台帳を先に作れば、`/dr-audit` は「台帳を作る作業」ではなく
「既にある台帳を検証する作業」になり、`(claim:cNNN)` マーカ付けのコストもほぼゼロになる。
<!-- policy:ledger-before-prose@deb0a7fb -->
<!-- policy:dr-gate-opt-in@fd4434e1 -->

## Step 0: 作業ディレクトリとツールを解決(必須)

```bash
cd "$(python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" notebook)"
DR="$(cat ~/.ikmstack/install-path)/tools/dr"
```

詳細は [記録のルーティング規約](../../../docs/conventions/record-routing.md)。
`questions.jsonl` が無ければ先に `/dr-plan`。以下 `<exp>` は実験ディレクトリ。

## 手順(下位問いごとに1周する)

問いを1つ選び、**1〜5 を最後まで回してから次の問いへ移る**。問いを跨いで探索すると、
どの問いの探索が済んだのか分からなくなる。

### 1. 探索して見つけたものを全部 `sources.jsonl` に書く

- **採らなかったものも書く。** `decision: rejected` + `decision_reason`。
  「該当記述なし」「孫引きで独自データなし」「条件が違う」も立派な結果である。
- `found_via` に**検索クエリそのもの**を書く。後から探索範囲を再現できるのはこれだけ。
- 未読のまま置くものは `decision: pending`(後で必ず解消する)。

### 2. 格付けと孫引きを畳む

`tier` は `primary` / `secondary` / `tertiary` / `vendor`。
**二次情報が別の原典を引いているなら `derived_from` に原典を書く。**
独立本数は `derived_from` で畳んだ後に数えるので、同じ原典を引く3本の記事は独立1本になる。
`vendor`(利害関係者)単独で判断駆動の問いを閉じない。
<!-- policy:source-tier-independence@e6b3fc5c -->

### 3. スナップショットを取る(link rot)

採用した出典は取得時点のページを保存し、Drive の当該実験フォルダ配下
`sources/<source_id>.<ext>` に置く。**git には入れない**(三大原則#1)。
`sources.jsonl` の `snapshot` に相対パスを書く。
取れなかった出典(有料壁・動的ページ)は `snapshot: null` のまま `note` に理由を書く
— **黙って空欄にしない**。

### 4. 読んで `claims.jsonl` に主張を書く

スキーマの正本は [claims_schema.md](../../../tools/dr/claims_schema.md)。調査では次の3つを必ず埋める:

- `question_id` — どの下位問いに答えるか
- `source_id` — `sources.jsonl` への参照(`source_url` も従来どおり残す。dr-verifier が使う)
- `stance` — `supports` / `refutes` / `neutral`。**下位問いの作業仮説に対する立場**
  (`citation_axes.supports` = 出典が主張本文を裏づけるか、とは別の軸)

`fact` は `verbatim_quote`(逐語引用)・`source_url`・`source_accessed` が必須。
判断を駆動する数値は `risk: decision_driving` にする。

### 5. 反証探索(必須)

**支持証拠が揃った時点で止めない。** 作業仮説を**否定する側**を意図的に探し、結果を台帳に残す:

- 「Xは速い」を調べたなら「X 遅い / regression / 期待外れ」を明示的に検索する。
- 見つかれば `stance: refutes` の主張として `claims.jsonl` に書く。
- 見つからなければ、探したこと自体を `sources.jsonl` に
  `decision: rejected` + `found_via`(クエリ) + `decision_reason`(棄却理由)で残す。

**探して見つからなかったことは成果である。** 台帳に残っていない「探したつもり」は、
`absence-claim` 型の撤回として後から必ず返ってくる。
<!-- policy:refutation-search-record@e752a626 -->

## 問いを閉じる

決着条件を満たしたら `questions.jsonl` の当該行を更新する:
`status: closed` / `answer`(1〜2文) / `confidence`(`high`|`medium`|`low`)。

**材料が尽きただけなら `abandoned` にし、`note` に理由を書く。**
打ち切りを決着と偽らない。閉じられない問いは `open` のまま残してよい
— 未決着は散文で開示する(`/dr-synth` が扱う)。

## 検証(この skill の終了時に必ず回す)

```bash
python3 "$DR/validate_research.py" <exp>/reports/
python3 "$DR/dr_coverage.py" <exp>/reports/questions.jsonl
```

網羅ゲートが FAIL するのは**まだ収集が終わっていない**という意味なので、
散文に進まず手順1〜5 に戻る。K2(独立ソース不足)なら別系統の出典を探し、
K3(反証の痕跡なし)なら手順5 をやり直す。

## 完了条件

- `pending` の出典が残っていない
- `closed` の問いが全て K1〜K3 を満たす(`dr_coverage.py` が PASS)
- `open` / `abandoned` の問いは、そのままでよい(次で開示する)

次は `/dr-synth`(台帳から論証を組んで散文にする)。
