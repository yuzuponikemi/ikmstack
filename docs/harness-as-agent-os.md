# ハーネス = エージェント運用 OS(設計思想)

> ikmstack(① ハーネス層)がどういう思想で組まれているかの正本。
> 「何があるか」の棚卸しは [harness-map.md](harness-map.md)(生成)が持つ。
> ここには**なぜそうなっているか**だけを書く(腐る常設ビューを増やさない)。

## ハーネスとは何か

ikmstack は表向き「skill と tool の詰め合わせ」だが、実体は
**エージェント運用 OS** として設計している。層で見るとこうなる:

| 層 | 実体 |
|---|---|
| 憲法 | [AGENTS.md](../AGENTS.md)(三大原則ほか) |
| 詳細規約 | [docs/conventions/](conventions/)(レポート・図・記録ルーティング・ポリシーレジストリ) |
| ワークフロー自動化 | `.claude/skills/`(exp-new / exp-report / exp-checkpoint / lab-log / kb-promote / regen-outputs / exp-deck / dr-audit / harness-edit ほか) |
| 決定論ゲート | `tools/*.py`(原則 stdlib のみ)+ `.githooks/pre-commit` |
| メモリ | ② 記録層(logs / tips / experiments / sidecar)+ KB + gbrain |
| 強制 | git hooks(`core.hooksPath .githooks`)+ `setup` の symlink install |

**3層運用**(① ハーネス / ② 記録 / ③ プロダクト)との関係: この文書が扱うのは ① だけ。
① は道具と規約だけを持ち、記録は一切持たない。② は記録だけを持ち、① を install して
consume する。境界の理由は AGENTS.md「3層運用」を見る。

## 3つの設計遺伝子(全層に繰り返し現れる)

1. **二重帳簿** — machine-truth の正本 + 人間可読の派生物 + 両者を同期させる決定論ゲート。
   例: レポートのフロントマター → `report_meta.py` → INDEX.md /
   claims.jsonl → 散文(dr-audit)/ 生データ+`regenerate.sh` → 図 /
   policy-registry.json → policy-map.md / ソース群 → `harness_map.py` → harness-map.md。
   **生成物は手で編集しない。回せば直る**ものだけが生成部に入れる。
2. **LLM を信頼しない設計(distrust-by-construction)** — LLM の出力・作用は、
   独立に検証できるインターフェースを通じてのみ受け入れる。生成器を改善しても
   factuality は十分には上がらないため、独立検証層は必要条件になる。
   dr-verifier の盲検化(著者の根拠を渡さない)、readability-review / runbook-review の
   隔離レビュー(兄弟文書を見せない)、ゲートの opt-in マーカ
   (無ければ構造的に発火しない = safe-by-construction)もこの遺伝子。
3. **エントロピー最小 vs 追記の緊張** — 三大原則#3。リビング文書は単数・常に最新、
   追記型は R 番号で分離。「現在の正」と「履歴」を混ぜない。

## メタの転回:出力の監査 → 自己の保守

- **第一転回 = 出力の監査**。「エージェントが書いたもの」を独立に検証する層
  (dr-audit / dr-verifier / report-checksum / check_untraceable_numbers)。
  テーゼは**「独立検証できる IF を通じてのみ書き/作用してよい」**。
- **第二転回 = 自己の保守**。監査の対象を「出力」から**ハーネス自身のソースと運用**へ広げる。
  規約が複数箇所に写されると必ずドリフトするので、1ルール=1正本+ピン留めした写しに
  し、ゲートで伝播を強制する(policy-registry.json + `policy_gate.py` + harness-edit)。
  ハーネスの棚卸し自体も生成物にして鮮度をゲートする(`harness_map.py`)。

## 自己保守の入口

- 対応表(どの規約の正本がどこか): [docs/conventions/policy-map.md](conventions/policy-map.md)
- 改訂手順: `.claude/skills/harness-edit/SKILL.md`
- ゲート: `tools/policy_gate.py` / `tools/harness_map.py --check`(ともに pre-commit)
