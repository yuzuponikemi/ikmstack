# questions.jsonl / sources.jsonl スキーマ(調査の2台帳)

調査(ディープリサーチ)で `claims.jsonl` と組にして使う2つの台帳。
運用規約の正本は [docs/conventions/research.md](../../docs/conventions/research.md)。
検査は `validate_research.py`(スキーマ)と `dr_coverage.py`(網羅ゲート)。

いずれも JSONL(1行1オブジェクト)。テキストなので git にコミットできる
(AGENTS.md 三大原則#1)。置き場は実験の `reports/` 直下。

---

## questions.jsonl — 下位問いと決着条件

1行 = 1下位問い。調査の骨格で、これが無いと網羅を機械検査できない。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `question_id` | string | ✅ | 台帳内で一意。`Q1`, `Q2`, … |
| `question` | string | ✅ | 下位問いの本文。**1問1論点**にする |
| `closing_condition` | string | ✅(`exploratory` を除く) | **決着条件**。「何が確認できたら閉じてよいか」。書けない問いは分解し直す |
| `status` | enum | ✅ | `open` / `closed` / `abandoned` / `exploratory` |
| `answer` | string\|null | `closed` で必須 | 決着した答え。1〜2文 |
| `confidence` | enum\|null | `closed` で必須 | `high` / `medium` / `low`。低いなら散文でもそう書く |
| `min_independent_sources` | number\|null | 任意(既定 2) | K2 が要求する独立ソース本数。単一の公式仕様で足りる問いは 1 に落としてよい(理由を `note` に) |
| `refutation_searched` | bool\|null | 任意 | 反証を狙った探索をしたか。K3 の痕跡は台帳側で数えるので、これは自己申告の補助に過ぎない |
| `parent` | string\|null | 任意 | 上位の問いの `question_id`(2段分解するとき) |
| `note` | string\|null | 任意 | 打ち切り理由・`min_independent_sources` を下げた理由など |

### status の意味(取り違えない)

- `open` — まだ調査中。**散文には open question として出す**。
- `closed` — 決着条件を満たした。K1〜K3 の検査対象になる。
- `abandoned` — **材料が尽きて打ち切った**。決着ではない。`note` に理由必須。散文には出す。
- `exploratory` — 最初から決着させない探索(地形を見るだけ)。ゲートの対象外。
  逃げ道になりうるので、判断を駆動する問いには使わない。

### 最小例

```jsonc
{"question_id":"Q1","question":"ローカル推論の速度を決める主因は活性パラメータ数か","closing_condition":"活性パラメータ数の異なる3モデル以上で tok/s の順位が活性パラメータ数の逆順と一致し、総パラメータ数とは一致しないことを実測または一次資料で確認できる","status":"closed","answer":"活性パラメータ数が主因。総パラメータ数とは順位が一致しない","confidence":"high","min_independent_sources":2,"refutation_searched":true,"parent":null,"note":null}
```

---

## sources.jsonl — 探索の記録

1行 = 1出典候補。**採用したものだけでなく、見つけたが採らなかったものも書く。**
「探したが無かった」を残せる台帳がこれで、`absence-claim` 型の撤回への唯一の対策になる。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `source_id` | string | ✅ | 台帳内で一意。`s001`, `s002`, … |
| `url` | string | ✅ | 出典 URL(書籍等で URL が無ければ ISBN 等の同定子) |
| `title` | string | ✅ | ページ・文献のタイトル |
| `publisher` | string\|null | 推奨 | 発行元。利害関係の判断に要る |
| `tier` | enum | ✅ | `primary` / `secondary` / `tertiary` / `vendor` |
| `derived_from` | string\|null | ✅(孫引きなら) | 引用元の `source_id` か原典 URL。**独立本数はこれで畳んでから数える** |
| `accessed` | string\|null | 採用時必須 | 取得日 `YYYY-MM-DD` |
| `found_via` | string | ✅ | **どう見つけたか**。検索クエリそのもの / 別出典の参考文献 / 既知 |
| `decision` | enum | ✅ | `adopted`(採用) / `rejected`(棄却) / `pending`(未読) |
| `decision_reason` | string | ✅(`rejected` で) | **なぜ採らなかったか**。「該当記述なし」も立派な結果 |
| `question_ids` | array | ✅ | この出典が関わる下位問いの `question_id` 列(空配列可) |
| `snapshot` | string\|null | 採用時推奨 | Drive 上の保存先相対パス `sources/<source_id>.<ext>` |
| `note` | string\|null | 任意 | 有料壁で取得不可・原典に遡れなかった等 |

### tier の格付け

| tier | 例 |
|---|---|
| `primary` | 原論文・一次統計・規格書・当事者の一次発表・ソースコード |
| `secondary` | 解説記事・レビュー論文・報道 |
| `tertiary` | まとめサイト・百科事典・LLM の出力 |
| `vendor` | 販売元・当事者の宣伝資料(利害関係あり) |

`vendor` 単独で判断駆動の問いを閉じない(research.md「出典の格付けと独立性」)。

### 最小例

```jsonc
{"source_id":"s001","url":"https://example.org/paper","title":"Mixture-of-Experts inference cost","publisher":"Example Lab","tier":"primary","derived_from":null,"accessed":"2026-08-24","found_via":"検索: MoE active parameters inference latency","decision":"adopted","decision_reason":null,"question_ids":["Q1"],"snapshot":"sources/s001.pdf","note":null}
{"source_id":"s002","url":"https://example.com/blog","title":"なぜ MoE は速いのか","publisher":"個人ブログ","tier":"tertiary","derived_from":"s001","accessed":"2026-08-24","found_via":"検索: MoE 速い 理由","decision":"rejected","decision_reason":"s001 の孫引きで独自の測定なし。独立ソースに数えられない","question_ids":["Q1"],"snapshot":null,"note":null}
```

---

## claims.jsonl 側の追加フィールド(調査で使う)

`claims_schema.md` が正本。調査では次の3つを併せて埋める(いずれも既存台帳との後方互換のため任意):

| フィールド | 説明 |
|---|---|
| `question_id` | どの下位問いに答える主張か。**`decision_driving` では実質必須**(K1 が数える) |
| `source_id` | `sources.jsonl` への参照。`source_url` は従来どおり残す(dr-verifier が使う) |
| `stance` | `supports` / `refutes` / `neutral`。下位問いの作業仮説に対する立場(K3 が数える) |

`stance` と `citation_axes.supports` は別の軸である。前者は**主張が問いに対して取る立場**、
後者は**出典が主張本文を裏づけるか**という検証結果。
