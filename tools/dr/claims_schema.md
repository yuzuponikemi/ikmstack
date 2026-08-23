# claims.jsonl スキーマ(主張台帳 = claim ledger)

1 行 = 1 主張(atomic claim)。JSONL(1 行 1 JSON オブジェクト)。
正本データとして git にコミットできる(AGENTS.md 三大原則#1: git=テキスト)。
散文は**この台帳から導出**し、本文中の各数値に `claim_id` を紐づけます。

## フィールド

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `claim_id` | string | ✅ | 台帳内で一意。例 `c001` |
| `subject` | string | ✅ | 実体。例 `A&D EK-610i` |
| `attribute` | string | ✅ | 属性。例 `repeatability (s)` |
| `value_raw` | string | fact/derived で必須 | 出典の表記そのまま。例 `0.01 g` |
| `value_num` | number\|null | 数値主張なら推奨 | 数値部分。例 `0.01` |
| `unit` | string\|null | `value_num` があれば推奨 | 単位。例 `g` |
| `claim_type` | enum | ✅ | `fact` / `inference` / `derived` |
| `risk` | enum | ✅ | `decision_driving`(判断駆動=全数検証必須) / `supporting`(補足=抜き取り) |
| `source_url` | string\|null | `fact` で必須 | 出典 URL |
| `source_accessed` | string\|null | `fact` で必須 | 取得日 `YYYY-MM-DD` |
| `verbatim_quote` | string\|null | `fact` で必須 | 出典本文の**逐語引用**(執筆者の主張。検証者が再取得して照合する) |
| `derivation` | object\|null | `derived` で必須 | `{"formula": "...", "vars": {"s":"c002",...}, "inputs": [...]}`。`vars`(変数名→claim_id)があると `numeric_compare.py` が自動 recompute できる(下記) |
| `citation_axes` | object | ✅ | `{"reachable": bool\|null, "relevant": bool\|null, "supports": bool\|null}`(検証の3軸) |
| `entity_check` | object\|null | 任意(dr-verifier 産物) | `{"resolved": bool, "entity_note": "...", "quantity_note": "..."}`。値が**どの実体/量を指すか**(例: 一般用 vs -K、正味 vs 総質量)。`resolved=false` は要確認(仕様・定義の取り違え型を拾う軸) |
| `question_id` | string\|null | 調査で必須 | 答える下位問いの ID(`questions.jsonl`)。`decision_driving` では実質必須(網羅ゲート K1 が数える) |
| `source_id` | string\|null | 調査で推奨 | `sources.jsonl` への参照。`source_url` は従来どおり残す(dr-verifier が使う) |
| `stance` | enum\|null | 調査で必須 | `supports` / `refutes` / `neutral`。**下位問いの作業仮説に対する立場**(K3 が反証の痕跡として数える)。`citation_axes.supports`(出典が主張本文を裏づけるか)とは別の軸 |
| `verification` | object | ✅ | 下記 |

### `verification` ブロック

| フィールド | 型 | 説明 |
|---|---|---|
| `status` | enum | `unverified` / `verified` / `refuted` / `unreachable` |
| `verifier` | string\|null | 検証した主体(例 `dr-verifier`) |
| `method` | string\|null | `refetch+quote+numeric` / `nli` / `recompute` / `sampled-skip` |
| `verdict_note` | string\|null | 判定理由。`refuted` なら**出典側の実際の値**を書く |
| `checked_at` | string\|null | 検証日 `YYYY-MM-DD` |

## ルール(検証側が前提とする)

- **執筆者の `verbatim_quote` は「主張」であって正ではない。** 検証者(dr-verifier)は `source_url` を
  **自分で再取得**し、quote の実在と数値の厳密一致を確かめてから `verification` を埋める(独立性の担保)。
- **数値は決定論で照合**(桁・単位)。NLI/judge は意味的支持の判定のみ。
- **実体/量の識別**(`entity_check`)も確認する。数値が一致しても**どの実体/量か**を取り違えると破綻する
  (例: 一般用 vs -K、正味 vs 総質量)。`resolved=false` なら数値一致でも `supports` を保留。
- **派生値(`derived`)は `numeric_compare.py` で再計算照合**。`derivation.vars` の変数→claim_id を
  `value_num` に解決し `formula` を評価、丸め表示を考慮して主張値と比較。**「再現しない」は
  (a)出典誤り/(b)台帳の入力リンク誤りの2因**=出典の導出基準を読んで切り分ける。
- `decision_driving` は**全数検証必須**。`supporting` はリスク加重サンプリング(Phase 2)。
- **調査(ディープリサーチ)では台帳を3つ持つ**。この `claims.jsonl` に加えて
  `questions.jsonl`(下位問いと決着条件)と `sources.jsonl`(探索の記録)。スキーマは
  [research_schema.md](research_schema.md)、運用規約は
  [docs/conventions/research.md](../../docs/conventions/research.md)。
  受入ゲート(`dr_gate.py` = 書いたものの正しさ)と網羅ゲート(`dr_coverage.py` = 書かなかった
  ことの穴)の**両方**を通して受入可とする。

## 最小例

```jsonc
{"claim_id":"c001","subject":"A&D EK-610i","attribute":"readability (d)","value_raw":"0.01 g","value_num":0.01,"unit":"g","claim_type":"fact","risk":"decision_driving","source_url":"https://satosokuteiki.com/item/detail/34","source_accessed":"2026-06-29","verbatim_quote":"最小表示 0.01 g","derivation":null,"citation_axes":{"reachable":null,"relevant":null,"supports":null},"verification":{"status":"unverified","verifier":null,"method":null,"verdict_note":null,"checked_at":null}}
```
