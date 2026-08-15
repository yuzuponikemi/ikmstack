# ikmstack オンボーディングガイド

> 研究・開発方法論を一元管理する **「① ハーネス層」** リポジトリへようこそ。
> このガイドはナレッジグラフ（`.ua/knowledge-graph.json`）から自動生成しています。
> 解析コミット: `535ea5e` / 生成日: 2026-07-20
>
> ⚠️ **ファイル数・スキル一覧はこの生成時点のもの**で、その後にツール・スキルを追加しています
> （ハーネス自己保守 `policy_gate` / `harness_map`、日次ログ草稿 `log_draft`、撤回集計
> `retractions`、横断シンセシス `synthesis_*`、読みビュー `index_html` / `report_readview`、
> スキル `harness-edit` / `report-checksum` / `readability-review` / `runbook-review` /
> `procedure-new` / `pr-review-doc`）。
> **常に最新の棚卸しは [harness-map.md](harness-map.md)**（`python3 tools/harness_map.py` が生成し
> pre-commit が鮮度を検査）。設計思想は [harness-as-agent-os.md](harness-as-agent-os.md)。
> 本ガイドを作り直すなら `/understand` を回す。

---

## 1. プロジェクト概要

**ikmstack** は、skill・tool・規約を**正典（single source of truth）として保持し、`setup` で各マシンに install** して、記録層（ラボノート）や各プロダクト repo から consume させる「仕組み層」です。gstack の親戚にあたります。**記録そのものは持ちません。**

| 項目 | 内容 |
|------|------|
| 言語 | Markdown, Python, sh, CSS, HTML, JSON |
| フレームワーク | なし（`package.json` / `pyproject.toml` を持たない shell + Python 構成） |
| 規模 | 58 ファイル / 107 ノード / 147 エッジ / 7 層 |
| 依存の密度 | `imports` エッジは 6 本のみ = **疎結合な「規約・仕組み集」** |

### 3層運用モデル（最上位の判断軸）

```
① 仕組み（ハーネス）= ikmstack（この repo）   skill・tool・規約。./setup で install     公開可
② 記録（ラボノート）= ikmnote 等              実験・ログ・tips・決定。ハーネスは持たない  private
③ プロダクトコード  = 各プロダクト repo        出荷ソース。クリーンに保つ                各自
```

**リトマス試験**：「再利用できる仕組みか」→ ① ikmstack ／「知見・記録か」→ ② 記録層 ／「出荷ソースか」→ ③ プロダクト。

---

## 2. アーキテクチャ層（7 層）

このリポジトリはディレクトリ構造がそのまま層境界になっています。

### ① Skills 層 (`layer:skills`) — 14 ファイル
Claude Code スキル本体（`SKILL.md`）・参照ドキュメント・`dr-verifier` サブエージェントを正典として保持する**方法論ハーネスの中核**。install された skill が `/exp-new` → `/exp-report` → `/exp-checkpoint` → `/lab-log` という実験ライフサイクルの「動詞」を提供します。

### ② dr-audit 検証パイプライン (`layer:dr-audit`) — 7 ファイル
AI 生成レポートの数値・主張を出典と突き合わせて**独立検証**する Python パイプライン（ledger 検証・数値比較・散文追跡・受入ゲート・サンプリング）と仕様書。`/dr-audit` の実体。

### ③ exp-deck スライド生成器 (`layer:exp-deck`) — 6 ファイル
`REPORT.md` から共有用 `.pptx` を生成する `deckgen.py` と、ブランドトークン（`tokens.py` / `brand.css`）・サンプル HTML。

### ④ 共通ツール層 (`layer:tools`) — 5 ファイル
`report_meta` / `sidecar` / `strip_nb_outputs` / `sync_claude_settings` / `check_report_figures` など、スキルや pre-commit フックから呼ばれる横断的な Python ユーティリティ。

### ⑤ テンプレート層 (`layer:templates`) — 12 ファイル
実験雛形（`experiments/_template`）と記録層ラボノート雛形（`notebook-template`）。consume 側リポジトリへ複製されるスキャフォールド。

### ⑥ 規約・ドキュメント層 (`layer:documentation`) — 7 ファイル
`AGENTS` / `README` / `CLAUDE` の入口規約と `docs/` 配下の運用規約（reporting・figures-regen・repository-rules・workspace-mechanism）。

### ⑦ Install・設定層 (`layer:setup`) — 7 ファイル
`setup` エントリポイント・pre-commit hook・各種 config template。各マシンへ install する仕組み。

---

## 3. 押さえるべき設計コンセプト

- **symlink install モデル**：skill 本体を各 repo にコピーせず `~/.claude` 配下へシンボリックリンクを張る。ikmstack を1回更新すれば全マシンの skill が同時に最新化される。ハーネスをプロダクトに vendored（同居）させると「どっち編集」「merge 衝突」が構造的に起きるため、install モデルで **ハーネスは1ソース**に保つ。
- **規約を人手でなく機械で強制する**：`.githooks/pre-commit` が図リンク逸脱（`check_report_figures.py`）と INDEX ドリフトを commit 前に止め、`strip_nb_outputs.py` がノートブック出力の混入を防ぐ。
- **図は git に入れない（三大原則 #1）**：`regenerate.sh` が Drive 正本の生データから再生成する。`/regen-outputs` が図付きプレビューを駆動。
- **安全な式評価（AST ホワイトリスト）**：`numeric_compare.py` は `eval()` を使わず、`ast` で許可された演算ノードだけを通して数式を安全に再計算する。
- **デザイントークンの単一ソース**：`tokens.py` が色・フォント・余白を1箇所で定義し `brand.css` を派生生成。pptx と HTML プレビューのブランドを一致させる。

---

## 4. ガイドツアー（推奨学習パス・全10ステップ）

| # | タイトル | 主なファイル |
|---|----------|-------------|
| 1 | プロジェクトの全体像と3層運用 | `README.md` |
| 2 | 規約の正典 AGENTS.md | `AGENTS.md`, `docs/workspace-mechanism.md`, `repository-rules.md` |
| 3 | エントリポイント setup と install | `setup`, `sync_claude_settings.py`, `*.template` |
| 4 | Skills 層 — 実験ライフサイクルの動詞 | `exp-new/exp-report/exp-checkpoint/lab-log` の `SKILL.md` |
| 5 | tools/ 共通ツールと静的検証 | `report_meta.py`, `sidecar.py`, `check_report_figures.py`, `strip_nb_outputs.py`, `pre-commit` |
| 6 | dr-audit ① 台帳検証の基盤 | `claims_schema.md`, `validate_ledger.py`, `numeric_compare.py`, `dr_gate.py` |
| 7 | dr-audit ② 照合と出典再取得 | `sampling_select.py`, `ledger_to_prose_check.py`, `dr-verifier.md`, `dr-audit/SKILL.md` |
| 8 | exp-deck スライド生成器 | `exp-deck/SKILL.md`, `deckgen.py`, `tokens.py`, `brand.css` |
| 9 | テンプレート層と図の再生成 | `PLAN/REPORT/MANIFEST.md`, `regenerate.sh`, `INDEX.md` |
| 10 | 記録層 scaffold と KB 昇格 | `notebook-template/*`, `kb-promote/SKILL.md` |

**流れ**：README → AGENTS（規約） → setup（install） → skills（動詞） → tools（実体） → dr-audit（検証） → exp-deck（出力） → テンプレート → 記録層／KB 昇格 で実験→報告→知識化のループが一周します。

---

## 5. ファイルマップ（層別）

<details>
<summary><b>① Skills 層</b></summary>

- `.claude/skills/exp-new/SKILL.md` — `/exp-new` の定義（実験 scaffold）
- `.claude/skills/exp-report/SKILL.md` (+ `references/exp_report_guide.md`) — `/exp-report`（house-style レポート化）
- `.claude/skills/exp-checkpoint/SKILL.md` (+ `references/checkpoint_procedure.md`) — `/exp-checkpoint`（区切りでの living docs 更新）
- `.claude/skills/lab-log/SKILL.md` — `/lab-log`（日次ログ）
- `.claude/skills/dr-audit/SKILL.md` (+ `references/dr_audit_protocol.md`) — `/dr-audit`（事実検証）
- `.claude/skills/kb-promote/SKILL.md` — `/kb-promote`（確定知見を共有 KB へ）
- `.claude/skills/exp-deck/SKILL.md` (+ `references/deck_design_principles.md`) — `/exp-deck`（スライド生成）
- `.claude/skills/regen-outputs/SKILL.md` (+ `references/regen_guide.md`) — `/regen-outputs`（図の再生成）
- `.claude/agents/dr-verifier.md` — 主張を独立検証するサブエージェント
</details>

<details>
<summary><b>② dr-audit 検証パイプライン</b></summary>

- `tools/dr/validate_ledger.py` — 主張台帳 claims.jsonl のスキーマ・整合性を検証する中核モジュール
- `tools/dr/numeric_compare.py` — 派生値を AST ホワイトリスト評価で再計算し照合する数値検証エンジン
- `tools/dr/ledger_to_prose_check.py` — 本文（散文）と台帳の整合を追跡
- `tools/dr/dr_gate.py` — supported/refuted/unclear を集計する受入ゲート
- `tools/dr/sampling_select.py` — AQL に基づく系統サンプリング CLI
- `tools/dr/claims_schema.md` / `tools/dr/README.md` — スキーマ定義と MVP 説明書
</details>

<details>
<summary><b>③ exp-deck スライド生成器</b></summary>

- `.claude/skills/exp-deck/deckgen.py` — python-pptx で編集可能な PowerPoint を組み立てる中核ジェネレータ
- `.claude/skills/exp-deck/brand/tokens.py` — ブランド定義の単一ソース → `brand.css` を生成
- `brand/brand.css` / `brand/sample.html` / `brand/sample_artifact.html` / `brand/build_sample.py` — ブランドアセット・プレビュー
</details>

<details>
<summary><b>④ 共通ツール層</b></summary>

- `tools/report_meta.py` — frontmatter 解析＋実験/レポート INDEX の検証・自動生成エンジン
- `tools/sidecar.py` — プロダクト repo 実行時に記録先 `sidecar/<slug>/` を git remote から算出
- `tools/check_report_figures.py` — 図リンクの実験ディレクトリ外参照を検査（pre-commit 用）
- `tools/strip_nb_outputs.py` — Jupyter 出力セルを除去（pre-commit / clean filter）
- `tools/sync_claude_settings.py` — lab-config + テンプレートから notebook の settings.json を生成
</details>

<details>
<summary><b>⑤ テンプレート層</b></summary>

- `experiments/_template/{PLAN,REPORT,MANIFEST}.md` — 実験1件の骨格（事前登録・house-style 雛形・関与 repo の SHA）
- `experiments/_template/regenerate.sh` — 図・自動レポートの一括再生成スクリプト
- `experiments/_template/reports/INDEX.md`, `experiments/INDEX.md` — レポート/実験索引ひな形
- `notebook-template/{README,AGENTS,CLAUDE}.md`, `gitignore`, `lab-config.json.template` — 記録層 scaffold
</details>

<details>
<summary><b>⑥ 規約・ドキュメント層</b></summary>

- `AGENTS.md` — 規約の正典（3層運用・三大原則・実験ID・命名・レポート構成）
- `README.md` — ハーネス層の入口・ゼロ再現手順・skill 一覧
- `CLAUDE.md` — Claude 固有の補足（AGENTS.md へのポインタ）
- `docs/workspace-mechanism.md` — 仕組みと設計思想の詳細
- `docs/conventions/{reporting,figures-regen,repository-rules}.md` — 三大原則の詳細規約
</details>

<details>
<summary><b>⑦ Install・設定層</b></summary>

- `setup` — 主エントリポイント（install / --init-notebook / --notebook / --status / --uninstall）
- `.githooks/pre-commit` — INDEX ドリフト・図リンクを commit 前に検査
- `.claude/settings.json.template`, `.lab-config.json.template`, `.gitattributes` — 各種 config template
</details>

---

## 6. コンプレックスホットスポット（慎重に読む箇所）

分布: **complex 4 / moderate 21 / simple 33**。最初に深追いすべきは以下の **complex** 4件です。

| complexity | ファイル | なぜ注意 |
|-----------|---------|---------|
| 🔴 complex | `tools/dr/validate_ledger.py` | dr-audit の基盤。台帳スキーマ検証の中核で、他モジュールが `load_and_validate` / `Issue` に依存 |
| 🔴 complex | `tools/report_meta.py` (400行) | 実験/レポート INDEX を検証・自動生成するメタデータエンジン。`/exp-checkpoint` と pre-commit の心臓部 |
| 🔴 complex | `.claude/skills/exp-deck/deckgen.py` (313行) | python-pptx でスライドを組み立てる生成器。分岐が多い |
| 🔴 complex | `setup` (235行, bash) | install の全モードを担う主エントリポイント。symlink 配線ロジックが集中 |

> **新規参加者へのおすすめ**：まず `README.md` → `AGENTS.md` で規約を掴み、`setup --status` で install 状態を確認してから、ツアー順（skills → tools → dr-audit）に読み進めるのが最短です。complex 4件は「動作を変える前に」腰を据えて読む対象です。

---

## 7. 最初の一歩（クイックスタート）

```bash
# ハーネスを install（skills → ~/.claude/skills、agents → ~/.claude/agents）
cd ~/source/personal/ikmstack && ./setup

# install 状態を確認
./setup --status

# 記録層（ラボノート）を一から作る
./setup --init-notebook ~/source/personal/ikmnote

# 使い始める（記録層で Claude Code を開き）
#   /exp-new  新実験   /lab-log  日次ログ   /exp-report  レポート
```

**ハーネス改善は必ずここ（ikmstack）で行う** — 記録層やプロダクトには持ち込まない。編集後 `./setup` 再実行で symlink 経由で全マシンに反映されます。

---

*このガイドは `/understand-onboard` によりナレッジグラフから生成されました。グラフを更新するには `/understand` を再実行してください。*
