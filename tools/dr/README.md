# tools/dr — Deep Research 検証ツール (Phase 1 MVP)

エージェント生成レポートの**事実・数値を独立検証**するための決定論スクリプト群。
設計の根拠は、レポートの検証設計に基づいています。

## いまの状態(重要)

**手動運用 + スキル/エージェント昇格済み。グローバル Stop hook は意図的に入れていない。**

- 決定論ツール(本ディレクトリ)は単体で手動実行できる。
- 独立検証者は `.claude/agents/dr-verifier.md`(明示呼び出し=自動発火しない)。
- オーケストレーションは `/dr-audit` スキル(`.claude/skills/dr-audit/SKILL.md`)。
  **受入ゲートはスキルの最後で必ず実行**(skill 内強制)。
- **グローバル Stop hook は `.claude/settings.json` に入れていない。** 理由: Stop hook は
  このリポジトリの**全 Claude セッションで発火**し、未成熟なゲートを入れると普段の作業まで
  「完了ブロック」され事故るのを防ぐため、強制は skill 内ゲートで足ります。

### (opt-in) グローバル hook を入れたい場合

特定運用で全レポート保存をゲートしたいなら、各自の `.claude/settings.local.json` に**自己責任で**:

```jsonc
{
  "hooks": {
    "Stop": [{ "hooks": [{ "type": "command",
      "command": "python tools/dr/dr_gate.py <対象台帳>" }] }]
  }
}
```

> ⚠️ これは**全セッションの完了をブロックしうる**。チーム共有の `settings.json` には入れない。
> まずは `/dr-audit` の skill 内ゲートで運用し、効果が固まってから検討すること。

## スクリプト

| スクリプト | 役割 | 依存 |
|---|---|---|
| `validate_ledger.py` | 主張台帳 `claims.jsonl` のスキーマ・必須列・enum を検証 | stdlib のみ |
| `numeric_compare.py` | 派生値の決定論 recompute(`derivation.vars`+`formula` を評価、丸め考慮で照合) | stdlib のみ |
| `ledger_to_prose_check.py` | 散文↔台帳の追跡(参照の実在・検証済み・**数値ドリフト**・citation_error_rate) | stdlib のみ |
| `sampling_select.py` | リスク加重サンプリング(判断駆動=全数 / 補足=Z1.4 抜き取り選定) | stdlib のみ |
| `dr_gate.py` | 受入ゲート(手動): 判断駆動主張が全数 verified か / 不良率 / 引用整合 | stdlib のみ |

スキーマ定義は [`claims_schema.md`](claims_schema.md)。

> `numeric_compare.py` の mismatch は「派生値が再現しない」を意味するが、原因は
> **(a) 出典の値が誤り / (b) 台帳の入力リンクが誤り** の2因。**出典の導出基準を読んで
> 切り分けてから出典を疑う**（初版で出典を誤って疑った教訓）。

## 手動運用フロー(Phase 1)

```sh
# 1. 台帳のスキーマを検証
python tools/dr/validate_ledger.py <path>/claims.jsonl

# 2. (検証前)受入ゲート → 判断駆動が未検証なので FAIL するのが正しい
python tools/dr/dr_gate.py <path>/claims.jsonl

# 3. 各 decision_driving 主張を dr-verifier(プロンプト)で独立検証し、
#    verification ブロックを埋める。プロンプトは
#    .claude/agents/dr-verifier.md
#    検証者には source_url と value だけ渡す(執筆者の根拠は渡さない=独立性)。

# 4. 再度ゲート → 全 decision_driving が verified なら PASS
python tools/dr/dr_gate.py <path>/claims.jsonl
```


