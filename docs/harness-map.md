# ハーネス地図(harness map)

このリポジトリの**ハーネス**(= エージェント運用の基盤: 規約・スキル・ゲート・照会DB・メモリ)の
全体像を 1 枚で俯瞰する地図。「変更を重ねるうちに全体像が分からなくなる」ことへの対策で、
**二重帳簿**で維持する:

- **棚卸し(生成部)** — 「何があるか」。機械可読ソース(SKILL.md frontmatter /
  policy-registry.json / .githooks/pre-commit / tools)から
  `python tools/harness_map.py` が決定論で再生成する(マーカ間のみ)。**手で編集しない**。
  鮮度は pre-commit の `python tools/harness_map.py --check` が守る。
- **全体像(手書き部)** — 「なぜ・どう繋がるか」。層図と narrative。機械化できない設計判断なので
  人手/LLM で維持する。**陳腐化を遅らせるため、手書き部には個々の部品名・件数を書かない**
  (部品の名前は生成部だけが持つ。部品を足しても手書き部は原則ノータッチ)。

設計思想の長文は [harness-as-agent-os.md](harness-as-agent-os.md)(3遺伝子: 二重帳簿 /
distrust-by-construction / エントロピー最小)。改訂手順は harness-edit スキル。

## 規模(生成)

<!-- gen:harness-map:summary:start -->

スキル **14** / エージェント **1** / 規約ルール **15**(うち実行時強制 8) / pre-commit 関門 **7** / tools **19**

<!-- gen:harness-map:summary:end -->

## 全体像(手書き — 層と関係だけ)

```mermaid
flowchart TB
    subgraph MEANING["規約層(意味を決める) — 人手/LLM 維持"]
        AGENTS["AGENTS.md(憲法)"]
        CONV["docs/conventions/(詳細規約)"]
        REGISTRY["policy-registry.json(1ルール=1正本の台帳)"]
    end
    subgraph PROC["手順層(やり方を固定する) — 人手/LLM 維持"]
        SKILLS[".claude/skills/(固定手順)"]
    end
    subgraph DET["決定論層(機械が守る)"]
        TOOLS["tools/(生成器・検査器)"]
        HOOK[".githooks/pre-commit(コミット関門)"]
    end
    subgraph RECORD["② 記録層(別リポジトリ = ノート)"]
        EXPS["experiments/(実験・一次記録)"]
        LOGS["logs/ + tips/(日次ログ・暗黙知)"]
        SIDECAR["sidecar/&lt;owner-repo&gt;/(③ プロダクト repo 由来の記録)"]
    end
    EXT["外部正 — Google Drive / KB / ③ プロダクトリポ群"]

    AGENTS -->|規約を参照| SKILLS
    REGISTRY -->|digest ピンで写しを束ねる| SKILLS
    REGISTRY -->|C1〜C5 検査| HOOK
    SKILLS -->|手順が生む| EXPS
    EXPS -->|フロントマター→INDEX 生成| TOOLS
    TOOLS --> HOOK
    EXPS -->|確定知見の昇格(kb-promote)| EXT
    SETUP["setup(① を ~/.claude へ install / ② を配線)"]
    SETUP -.->|symlink で ② に tools/・.githooks/ を貸す| RECORD
```

読み方(更新の流れは 2 本だけ):

1. **仕事をする流れ**: スキル(手順層)が実験・記録(記録層)を生み、tools が INDEX や図を
   生成し、pre-commit(決定論層)が規約とのずれを止める。
2. **ハーネス自体を変える流れ**: 規約層の正本を直す → policy gate が写し(スキル等)への
   伝播を強制する → この地図の棚卸しが自動で追随する。入口は常に harness-edit スキル。

## 決定論で更新できるところ / できないところ(手書き)

**決定論で更新できる(生成物 — 手で編集せず生成器を回す)**:

| 生成物 | 生成器 | ドリフト検出 |
|---|---|---|
| `experiments/INDEX.md`・各 `reports/INDEX.md` | `tools/report_meta.py` | pre-commit |
| `docs/conventions/policy-map.md` | `tools/policy_gate.py --write-map` | pre-commit(C5) |
| 本地図の棚卸しセクション | `tools/harness_map.py` | pre-commit |
| `experiments/INDEX.html`(読みビュー) | `tools/index_html.py` | 派生ビュー(git 管理外) |
| 各レポートの HTML 読みビュー | `tools/report_readview.py` | 派生ビュー(git 管理外) |
| `docs/retractions.md`(撤回の横断集計) | `tools/retractions.py` | フロントマター由来 |
| ① の install 状態(skills/agents の symlink) | `./setup` | `./setup --status` |

**決定論で更新できない(人手/LLM 維持 — 検査は間接的)**:

| 対象 | 維持手段 | ずれの検出(限界) |
|---|---|---|
| 規約の散文の**意味**(AGENTS.md / conventions) | harness-edit(必ず正本から) | policy gate は key_lines の複製しか見ない。言い換えの意味ドリフトは改訂時の目視(harness-edit 手順7) |
| SKILL.md の本文(手順の質) | harness-edit | ゲート無し。使って壊れたら直す |
| 何をルール化するか(registry の増減) | 判断(policy-map.md の基準) | — |
| 本地図の手書き部(層図・narrative) | 手編集 | 層粒度に留めて陳腐化を遅らせる(部品名は書かない) |

境界線の原則: **「ソースが機械可読で、正が一意に定まるもの」だけが生成部に入れる**。
意味・判断・設計はどう頑張っても散文なので、独立レビュー(readability-review /
runbook-review / dr-audit)と改訂手順(harness-edit)で守る。

## 棚卸し(以下すべて生成 — 手で編集しない)

### コミット関門(.githooks/pre-commit)

<!-- gen:harness-map:gates:start -->

| # | 検査コマンド | 何を守るか(フックのコメント1行目) |
|---|---|---|
| 1 | `python tools/report_meta.py --check` | report フロントマター ↔ INDEX.md のドリフトをコミット前に検出する。 |
| 2 | `python tools/check_report_figures.py --check` | 図リンクが再生成出力先(_generated/ 等の gitignored)を指すか検査(三大原則#1 R3)。 |
| 3 | `python tools/check_script_encoding.py` | 実機/計測系 PowerShell のエンコーディング関門。 |
| 4 | `python tools/dr/dr_gate_precommit.py` | 実験ごと opt-in の dr-audit 軽量ゲート。 |
| 5 | `python tools/check_untraceable_numbers.py` | 実験ごと opt-in の「追跡できない数値」リンタ。 |
| 6 | `python tools/policy_gate.py` |  |
| 7 | `python tools/harness_map.py --check` |  |

<!-- gen:harness-map:gates:end -->

### 規約ルール(policy-registry.json)

正本↔写しの詳細対応は [conventions/policy-map.md](conventions/policy-map.md)。
ここでは「実行時に機械が強制するか」の切り分けだけを見る。

<!-- gen:harness-map:rules:start -->

| rule id | ルール | 正本 | 実行時強制(決定論) |
|---|---|---|---|
| `report-meta-regen` | INDEX は手書きせず report_meta.py で再生成する | AGENTS.md | `tools/report_meta.py --check (pre-commit)` |
| `figures-not-in-git` | 図は git に入れない(三大原則#1、R1〜R3) | docs/conventions/figures-regen.md | `tools/check_report_figures.py (pre-commit)` |
| `report-naming-numbering` | レポート命名 FL###-R### と R 番号の規律(リビング文書に R を振らない) | docs/conventions/reporting.md | —(散文。policy gate は写し同期のみ) |
| `frontmatter-schema` | REPORT.md / 一次記録の YAML フロントマター書式 | .claude/skills/exp-report/references/exp_report_guide.md | `tools/report_meta.py (schema errors fail --check)` |
| `living-vs-primary` | リビング文書 vs 一次記録(1機能=1権威) | docs/conventions/reporting.md | —(散文。policy gate は写し同期のみ) |
| `central-todo-scope` | 中央 tasks/TODO.md はマネジメント観点+リポ運営専用(実験の詳細は PLAN/REPORT が正本) | docs/conventions/reporting.md | —(散文。policy gate は写し同期のみ) |
| `lab-log-format` | 日次ログの置き場と4見出し(目的/やったこと/わかったこと/次にやること) | docs/conventions/repository-rules.md | —(散文。policy gate は写し同期のみ) |
| `nb-strip-outputs` | Notebook はセル出力をクリアして保存する | docs/conventions/repository-rules.md | `.gitattributes nbstrip filter + tools/strip_nb_outputs.py --check` |
| `kb-promotion` | 確定恒久知識だけ KB へ昇格し REPORT からリンクする | AGENTS.md | —(散文。policy gate は写し同期のみ) |
| `dr-gate-opt-in` | 台帳を作った実験は .dr-gate で commit 時検証ゲートに opt-in し、判断駆動数値は執筆時に claim マーカで台帳に紐づける | docs/conventions/reporting.md | `tools/dr/dr_gate_precommit.py (pre-commit; fires only for opted-in experiments)` |
| `verify-before-sharing` | 検証は平場でなく「外に出す直前」と「まとめとして固定する瞬間」に行う(共有前ゲート) | docs/conventions/reporting.md | `—(手順。機械強制はしない — 対象は成果物ごとに変わるため)` |
| `retraction-record` | 撤回は機械可読に記録する(旧版 superseded_by 必須 / 新版 corrects・retraction_type・discovered_by) | docs/conventions/reporting.md | `tools/report_meta.py (link resolvability + vocabulary; pre-commit)` |
| `new-term-referent-first` | 新語(造語)は初出定義+役割1つで導入する(語より先に指示対象; 検査は readability-review、定着語は terms.yaml へ昇格) | docs/conventions/reporting.md | —(散文。policy gate は写し同期のみ) |
| `report-input-pinning` | データ由来のレポートは入力(データ/仕様)をピン留めする(再現性・検算の前提) | docs/conventions/reporting.md | —(散文。policy gate は写し同期のみ) |
| `field-script-ascii-bom` | 実機/計測 PowerShell(.ps1)は英語優先・非ASCIIなら UTF-8 BOM 必須(CP932/PS5.1 対策) | AGENTS.md | `tools/check_script_encoding.py (pre-commit; scope experiments/<id>/scripts/**/*.ps1)` |

<!-- gen:harness-map:rules:end -->

### スキル(.claude/skills/)

<!-- gen:harness-map:skills:start -->

| スキル | 一言(description 冒頭) |
|---|---|
| [dr-audit](../.claude/skills/dr-audit/SKILL.md) | レポートの事実・数値を独立検証する。 |
| [exp-checkpoint](../.claude/skills/exp-checkpoint/SKILL.md) | At a milestone for an experiment, bring its uppercase living docs and INDEX up to date and write the log — in… |
| [exp-deck](../.claude/skills/exp-deck/SKILL.md) | Generate a shareable, peer-review-ready slide deck (.pptx) from an experiment's report — restructure REPORT.md… |
| [exp-new](../.claude/skills/exp-new/SKILL.md) | Scaffold a new experiment in this lab repo — copy experiments/_template, record involved repos' commit SHAs in… |
| [exp-report](../.claude/skills/exp-report/SKILL.md) | Author and register an experiment report using the lab house style — header block (type/status/date/data-era/s… |
| [harness-edit](../.claude/skills/harness-edit/SKILL.md) | Safely create or revise the harness's own source — skills (.claude/skills/*/SKILL.md), AGENTS.md, README.md, d… |
| [kb-promote](../.claude/skills/kb-promote/SKILL.md) | Promote settled findings from an experiment to a shared Knowledge Base (KB) — extract confirmed knowledge from… |
| [lab-log](../.claude/skills/lab-log/SKILL.md) | Write or update a daily lab log with the standard headings (目的/やったこと/わかったこと/次にやること), linking related experimen… |
| [pr-review-doc](../.claude/skills/pr-review-doc/SKILL.md) | Turn an implementation PR (application, device software, firmware, etc.) into a self-contained illustrated HTM… |
| [procedure-new](../.claude/skills/procedure-new/SKILL.md) | 手順書を3層トリロジー(① E2E Runbook 実行 / ② Principles & Triage 判断 / ③ Operation Notes 暗黙知)として起こす authoring スキル。 |
| [readability-review](../.claude/skills/readability-review/SKILL.md) | 個別レポートが「その1本だけで読める(自走的=self-contained)」かを独立レビューする。 |
| [regen-outputs](../.claude/skills/regen-outputs/SKILL.md) | Regenerate an experiment's figures and auto-reports locally so reports preview with images — sync raw data fro… |
| [report-checksum](../.claude/skills/report-checksum/SKILL.md) | Build a per-report verification ("検算") notebook that independently re-derives a report's numbers AND the compu… |
| [runbook-review](../.claude/skills/runbook-review/SKILL.md) | E2E Runbook(手順書①実行層)が「その装置・工具を全く知らない人間でも、判断を挟まず物理的に実行できる」原子性(atomicity)を満たすかを独立レビューし、関門(ゲート)にする。 |

<!-- gen:harness-map:skills:end -->

### 道具(tools/)

<!-- gen:harness-map:tools:start -->

| 道具 | 1行説明(docstring/先頭コメント) |
|---|---|
| `tools/check_report_figures.py` | check_report_figures.py — レポートの図リンクが「再生成出力先」を指すか検証(依存なし) |
| `tools/check_script_encoding.py` | check_script_encoding.py - guard field/measurement PowerShell against the |
| `tools/check_untraceable_numbers.py` | check_untraceable_numbers.py -- flag empirical numbers that carry no provenance anchor. |
| `tools/dr/`(6 scripts) | tools/dr — Deep Research 検証ツール (Phase 1 MVP) |
| `tools/gen_readview.py` | gen_readview.py — 読みビュー(HTML)生成の共通ステップ。 |
| `tools/harness_map.py` | harness_map.py — docs/harness-map.md の棚卸し(生成部)を再生成/検証する。 |
| `tools/index_html.py` | index_html.py — experiments/INDEX.html(ソート/フィルタ可能な読みビュー)生成 |
| `tools/log_draft.py` | log_draft.py — その日の commit から日次ログの**草稿**を組む(依存なし) |
| `tools/policy_gate.py` | Policy drift gate: keep harness policy copies in sync with canonicals. |
| `tools/pr_merge_guard.py` | pr_merge_guard.py — PreToolUse guard: PR は draft 作成まで・マージはユーザー承認後。 |
| `tools/provenance_stamp.py` | provenance_stamp.py -- burn provenance into a figure so it travels with it. |
| `tools/report_meta.py` | report_meta.py — experiment / report metadata からの INDEX 生成・検証(依存なし) |
| `tools/report_readview.py` | report_readview.py — 個別レポート(<experiment_id>-R###_*.md)の HTML 読みビュー生成. |
| `tools/retractions.py` | retractions.py — 撤回(retraction)の横断集計を docs/retractions.md に生成する(依存なし) |
| `tools/screenshot.py` | screenshot.py — capture the desktop so an agent can *see* GUI state. |
| `tools/sidecar.py` | sidecar.py — 記録の書き先を文脈から解決する（3層運用のサイドカー経路）。 |
| `tools/strip_nb_outputs.py` | Strip outputs and execution counts from Jupyter notebooks. |
| `tools/sync_claude_settings.py` | sync_claude_settings.py — .lab-config.json の設定値から .claude/settings.json を自動生成・同期するツール |
| `tools/synthesis_extract.py` | synthesis_extract.py — cross-experiment synthesis material extractor (依存なし) |
| `tools/synthesis_topical.py` | synthesis_topical.py — topical proximity between experiments (依存なし) |

<!-- gen:harness-map:tools:end -->
