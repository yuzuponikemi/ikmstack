---
name: dr-audit
description: レポートの事実・数値を独立検証する。主張台帳(claims.jsonl)を検証→判断駆動主張を dr-verifier で出典再取得照合→派生値を recompute→散文↔台帳追跡→受入ゲートまでを一巡する。エージェント生成レポートの数値が出典と合うか・取り違えが無いかを確かめたいとき("レポートを検証して", "数値の裏取りをして", "claim-audit を回して", "出典と突き合わせて")に使う。設計は検証プロセス設計に基づきます。
---

# dr-audit — レポート事実検証の一巡

レポートに含まれる数値や事実を、執筆プロセスの外側から独立して検証し、品質基準を満たしていることを保証します。

> [!IMPORTANT]
> **トークン節約とコンテキスト管理の義務**:
> 親エージェントは、本プロセスにおいて台帳 `claims.jsonl` や検証対象の Markdown レポートを直接 `view_file` 等で読み込んではいけません。必ず独立した一時的な **Subagent (サブエージェント)** を起動し、検証・デバッグ作業を完全に委譲してください。親エージェントのコンテキストには、Subagent が出力した最終的なゲート結果と修正概要のみを記録し、巨大なデータや修正途中のログの流入を防いでください。

> [!IMPORTANT]
> **作業開始前の義務**:
> 本プロセスを実行する前に、必ず詳細な手順、Subagent への指示プロンプトテンプレート、および切り分け基準が記載された以下のリファレンスドキュメントを `view_file` で読み込んでください。
> - [dr-audit 事実検証プロトコル詳細](references/dr_audit_protocol.md)

## 概要と検証手順 (Subagent への指示概要)

1. **台帳の準備・スキーマ検証**:
   - レポートの数値を `claims.jsonl` に書き起こし、スキーマを確認します。
   - `python3 tools/dr/validate_ledger.py <台帳>`

2. **独立検証の実行**:
   - `risk=decision_driving` の主張について `dr-verifier` エージェントを個別に呼び出し、検証結果を台帳に反映します。
   - 補足主張は `python3 tools/dr/sampling_select.py <台帳>` に基づきサンプリング検証します。

3. **派生値と散文の検証**:
   - 派生値再計算: `python3 tools/dr/numeric_compare.py <台帳>`
   - 散文との整合: `python3 tools/dr/ledger_to_prose_check.py <散文> <台帳>`

4. **受入ゲートによる判定 (必須)**:
   - `python3 tools/dr/dr_gate.py <台帳>` を実行し、PASS するまで修正と検証を繰り返します。
