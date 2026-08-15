# ポリシーマップ(1ルール=1正本)

ハーネスの規約がどこを正本とし、どのファイルが写し(ピン付き)かの対応表。

> **この表は手で編集しない。** 正本は [policy-registry.json](policy-registry.json)、
> 表は `python tools/policy_gate.py --write-map` が生成する(マーカ間のみ書き換わる)。
> 同期は pre-commit の policy_gate が検証する。

<!-- gen:policy-map:start -->

| rule id | ルール | 正本 | 写し(ピン付き) | digest |
|---|---|---|---|---|
| `report-meta-regen` | INDEX は手書きせず report_meta.py で再生成する(実行時強制: tools/report_meta.py --check (pre-commit)) | AGENTS.md「実験のワークフロー」 | docs/conventions/reporting.md | `@8a33397d` |
| `figures-not-in-git` | 図は git に入れない(三大原則#1、R1〜R3)(実行時強制: tools/check_report_figures.py (pre-commit)) | docs/conventions/figures-regen.md | AGENTS.md<br>.claude/skills/exp-new/SKILL.md | `@97b4297f` |
| `report-naming-numbering` | レポート命名 FL###-R### と R 番号の規律(リビング文書に R を振らない) | docs/conventions/reporting.md「レポート命名・R 番号」 | .claude/skills/exp-report/SKILL.md<br>AGENTS.md<br>docs/conventions/repository-rules.md<br>.claude/skills/report-checksum/SKILL.md | `@eb565f44` |
| `frontmatter-schema` | REPORT.md / 一次記録の YAML フロントマター書式(実行時強制: tools/report_meta.py (schema errors fail --check)) | .claude/skills/exp-report/references/exp_report_guide.md「フロントマター」 | AGENTS.md | `@6e2e1a63` |
| `living-vs-primary` | リビング文書 vs 一次記録(1機能=1権威) | docs/conventions/reporting.md | AGENTS.md | `@134848f4` |
| `central-todo-scope` | 中央 tasks/TODO.md はマネジメント観点+リポ運営専用(実験の詳細は PLAN/REPORT が正本) | docs/conventions/reporting.md「次の一手の正本」 | — | `@f008b168` |
| `lab-log-format` | 日次ログの置き場と4見出し(目的/やったこと/わかったこと/次にやること) | docs/conventions/repository-rules.md「ログの書式」 | .claude/skills/lab-log/SKILL.md<br>README.md | `@a0eca25e` |
| `nb-strip-outputs` | Notebook はセル出力をクリアして保存する(実行時強制: .gitattributes nbstrip filter + tools/strip_nb_outputs.py --check) | docs/conventions/repository-rules.md「Notebook 規約」 | .claude/skills/exp-new/SKILL.md<br>README.md | `@3ca1441e` |
| `kb-promotion` | 確定恒久知識だけ KB へ昇格し REPORT からリンクする | AGENTS.md「知見の昇格(tips → KB)」 | README.md | `@d1b964ea` |
| `dr-gate-opt-in` | 台帳を作った実験は .dr-gate で commit 時検証ゲートに opt-in し、判断駆動数値は執筆時に claim マーカで台帳に紐づける(実行時強制: tools/dr/dr_gate_precommit.py (pre-commit; fires only for opted-in experiments)) | docs/conventions/reporting.md「検証ゲート(.dr-gate)と claim マーカ」 | README.md | `@fd4434e1` |
| `verify-before-sharing` | 検証は平場でなく「外に出す直前」と「まとめとして固定する瞬間」に行う(共有前ゲート)(実行時強制: —(手順。機械強制はしない — 対象は成果物ごとに変わるため)) | docs/conventions/reporting.md「いつ検証するか — 共有前ゲート」 | — | `@38a1a7de` |
| `retraction-record` | 撤回は機械可読に記録する(旧版 superseded_by 必須 / 新版 corrects・retraction_type・discovered_by)(実行時強制: tools/report_meta.py (link resolvability + vocabulary; pre-commit)) | docs/conventions/reporting.md「改訂・撤回の記録」 | — | `@b39a00ca` |
| `new-term-referent-first` | 新語(造語)は初出定義+役割1つで導入する(語より先に指示対象; 検査は readability-review、定着語は terms.yaml へ昇格) | docs/conventions/reporting.md「新語(造語)の導入規律」 | .claude/skills/readability-review/SKILL.md | `@8b08bf1b` |
| `report-input-pinning` | データ由来のレポートは入力(データ/仕様)をピン留めする(再現性・検算の前提) | docs/conventions/reporting.md「データ由来の数値は入力をピン留めする」 | .claude/skills/report-checksum/SKILL.md | `@b32fc5e6` |

<!-- gen:policy-map:end -->
