# AGENTS.md — {{NOTEBOOK}}（② 記録層）

AI コーディングエージェント向けの補足規約。**この repo は記録層（②）**。

## 3層運用のどこか

| 層 | 実体 | ここでの扱い |
|---|---|---|
| ① 仕組み（ハーネス） | **ikmstack** | skill・tool・規約の正本。**編集はここでなく ikmstack で** |
| ② 記録（ラボノート） | **{{NOTEBOOK}}（この repo）** | 実験・ログ・tips・決定を書く。ハーネスは持ち込まない |
| ③ プロダクトコード | 各プロダクト repo | ここには置かない。クリーンに保つ |

**リトマス**：「再利用できる仕組みか」→① ikmstack で編集 /「知見・記録か」→ここ /
「出荷ソースか」→③ プロダクト repo。

## 正本は ikmstack

実験ID・命名・レポート/ログの書式・Drive 規約・KB 昇格フローなどハーネスの規約は
**ikmstack/AGENTS.md が正本**。各 skill の `SKILL.md` が手順を持つ。
迷ったら該当 skill（`/exp-new` `/exp-report` `/lab-log` `/dr-audit` `/kb-promote` 等）を使う。

## この repo で守ること（記録層としての最小規約）

- **git はテキスト＋生成スクリプトだけ**。図・生データ・大容量は git に入れず、
  `regenerate.ps1` でローカル再現／正本は Google Drive（`MANIFEST.md` からリンク）。
- **実験は1ディレクトリに閉じる**（`experiments/_template/` をコピーして始める＝`/exp-new`）。
- **確定事実と、意見・仮説・暫定値を混ぜない**（見出し・語頭ラベルで切り分ける）。
- **ハーネス（skill/tool/規約）をここで編集しない**。改善は ikmstack へ。
  `tools/`・`.githooks/` は ikmstack への gitignore された symlink（`./setup --notebook` が張る）。
