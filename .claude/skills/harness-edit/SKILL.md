---
name: harness-edit
description: Safely create or revise the harness's own source — skills (.claude/skills/*/SKILL.md), AGENTS.md, README.md, docs/conventions/ — under the policy-registry discipline (1 rule = 1 canonical + pinned copies, drift checked by tools/policy_gate.py). Use when adding a new skill, changing a convention/policy, editing AGENTS.md or README, or when the pre-commit policy gate fails ("スキルを作って/直して", "規約を変えたい", "AGENTS.md を編集", "policy gate が落ちた").
---

# harness-edit — ハーネス自身の改訂(meta-skill)

ハーネスのソース(スキル・AGENTS.md・README・conventions)を、正本/写しの規律を壊さずに
新設・改訂するための固定手順。

## 前提(仕組みの3点)

- **正本 = `docs/conventions/policy-registry.json`**(手編集)。各ルールの正本位置・
  操作的キー行(`key_lines`)・写し一覧を持つ。人間可読ビューは
  `docs/conventions/policy-map.md`(`--write-map` で生成。手で編集しない)。
- **写しはピンを持つ**: `<!-- policy:<id>@<digest8> -->`。digest は key_lines の
  sha256 先頭 8hex。正本の操作的内容を変えると digest が変わり、全写しのピンが
  stale になってゲートが列挙する(=伝播の強制)。散文の推敲では digest は変わらない。
- **ゲート = `tools/policy_gate.py`**(pre-commit の関門の一つ — 実際の並びは
  docs/harness-map.md の生成表が正。opt-in =レジストリの存在)。
  C1 正本にキー行がある / C2 写しにピンがある / C3 未登録の写しが無い /
  C4 ピンが新しい / C5 マップが同期、を検査する。

## 手順

0. **worktree に入る**(EnterWorktree。並行セッション規約 — ハーネスのソースは
   全セッションが読むので、メイン checkout の直接編集は事故のもと)。
1. **触るルールを特定する**: `docs/conventions/policy-map.md` を開き、編集対象の
   ファイル/規約がどのルールの正本・写しかを確認する。どのルールにも属さない
   純粋な追記なら 2〜4 は飛ばして 5 へ。
2. **正本を編集する**(写しから直したくなっても、まず正本)。
   - 操作的内容(コマンド・パス・固有句)を変えた場合は、レジストリの `key_lines` も
     合わせて更新する(更新しないと C1 で止まる)。
3. **ピンを伝播する**(key_lines を変えた場合のみ):
   ```
   python3 tools/policy_gate.py --digest <rule-id>   # 新 digest を取得
   ```
   ゲートが列挙する各写しについて、**インライン要約が正本の変更後も正しいかを見てから**
   ピンの digest を書き換える(機械的に digest だけ直さない — レビューがピン更新の対価)。
4. **マップを再生成する**: `python3 tools/policy_gate.py --write-map`
5. **新スキルを作る場合**は雛形に従う:
   - `.claude/skills/<name>/SKILL.md`。frontmatter は `name:`(ケバブ)と `description:`
     (英語、トリガー語句の例を含める。既存スキル参照)。本文は日本語可・~150行目安。
   - 既存規約を再説明する箇所は**3点セット**で書く:
     ①操作行そのもの(コマンド。スキル単体で実行可能に保つ)
     ②1〜2行の最小インライン要約 ③`正本: <file>「<anchor>」` + ピン。
     長い理由説明・表・例は正本側へ。
   - 再説明した規約があれば、レジストリの該当ルール `copies` に登録する。
6. **検証**: `python3 tools/policy_gate.py --all` が PASS すること。
   `python3 tools/policy_gate.py --selftest` はゲート自体を触ったときのみ。
7. **波及先の目視**(ゲートが見ないもの): 変更した規約を**言い換えで**再説明している
   文が無いか、`policy-map.md` の写し一覧のファイルだけ開いて確認する
   (ゲートは key_lines の複製しか検出しない — 意味的ドリフトは人間/LLM の担当)。

## 新ルールを登録するとき

再説明が2ファイル以上に増えた規約は、レジストリに新ルールとして起こす:

1. 正本を1箇所決める(憲法的ルール→AGENTS.md、機械的詳細→docs/conventions/、
   操作手順→該当スキル。迷ったら `docs/conventions/policy-map.md` の既存ルールを参照)。
2. `key_lines` は**操作的文字列のみ**(コマンド・パス・固有句)。散文を鍵にしない
   (照合は全空白除去で行われるので改行・折返しは気にしなくてよい)。
3. `copies` に写しを列挙し、各写しに 3点セット+ピンを付ける。
4. `--write-map` → `--all` で PASS を確認。

## エージェント定義を変えたとき(反映のタイミング)

`.claude/agents/*.md` の **frontmatter(特に `tools:`)の変更は、実行中のセッションには反映されない**。
エージェント定義はセッション開始時に読み込まれるため、`setup` を回して symlink が正しく
更新されていても、**同じセッションで起動したサブエージェントは古い定義のまま動く**。

- 症状: 足したはずのツールが「割り当てられていない」とサブエージェントが報告する。
- 確認: `head -4 ~/.claude/agents/<name>.md` で実体を見る。実体が新しければ、
  それはインストールの失敗ではなく**セッションの寿命**の問題。
- 対処: **新しいセッションで検証する。** 同一セッション内で「直してすぐ試す」ことはできない。
  実例: dr-verifier に `Read` を足した直後、同セッションで再検証を投げたら
  古い定義(WebFetch のみ)で起動し、検証できずに差し戻された。
- したがって**エージェント定義の変更は「効いたことを確認した」と同じセッションでは書けない**。
  記録には「実体は更新済み・実効の確認は次セッション」と正直に書く。

## アンチパターン

- 写しだけ直して正本を放置 → 次の改訂で古い正本が「勝って」しまう。**必ず正本から**。
- digest だけ機械的に更新 → 伝播強制の意味が消える。**写しの要約を見てから**ピンを直す。
- `policy-map.md` を手編集 → 生成物(C5 で止まる)。レジストリを直して `--write-map`。
- ゲートを通すためだけに `allow` に足す → `allow` は「正当にキー行を含むがルールの
  写しではない」ファイル専用(例: チュートリアル)。写しなら copies+ピンにする。

## 関連

- ルールと写しの対応表(生成): `docs/conventions/policy-map.md`
- ハーネス全体の設計思想: `docs/harness-as-agent-os.md`
