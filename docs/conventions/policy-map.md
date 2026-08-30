# ポリシーマップ(1ルール=1正本)

ハーネスの規約がどこを正本とし、どのファイルが写し(ピン付き)かの対応表。

> **この表は手で編集しない。** 正本は [policy-registry.json](policy-registry.json)、
> 表は `python3 tools/policy_gate.py --write-map` が生成する(マーカ間のみ書き換わる)。
> 同期は pre-commit の policy_gate が検証する。

<!-- gen:policy-map:start -->

| rule id | ルール | 正本 | 写し(ピン付き) | digest |
|---|---|---|---|---|
| `report-meta-regen` | INDEX は手書きせず report_meta.py で再生成する(実行時強制: tools/report_meta.py --check (pre-commit)) | AGENTS.md「実験のワークフロー」 | docs/conventions/reporting.md<br>.claude/skills/exp-new/SKILL.md<br>.claude/skills/exp-report/SKILL.md<br>.claude/skills/exp-checkpoint/SKILL.md<br>.claude/skills/exp-checkpoint/references/checkpoint_procedure.md<br>.claude/skills/exp-report/references/exp_report_guide.md<br>.claude/skills/dr-synth/SKILL.md | `@a43c35f7` |
| `figures-not-in-git` | 図は git に入れない(三大原則#1、R1〜R3)(実行時強制: tools/check_report_figures.py (pre-commit)) | docs/conventions/figures-regen.md | AGENTS.md<br>.claude/skills/exp-new/SKILL.md<br>.claude/skills/regen-outputs/references/regen_guide.md | `@97b4297f` |
| `report-naming-numbering` | レポート命名 <実験ID>-R### と R 番号の規律(リビング文書に R を振らない) | docs/conventions/reporting.md「レポート命名・R 番号」 | .claude/skills/exp-report/SKILL.md<br>AGENTS.md<br>docs/conventions/repository-rules.md<br>.claude/skills/report-checksum/SKILL.md<br>.claude/skills/exp-checkpoint/references/checkpoint_procedure.md<br>.claude/skills/exp-report/references/exp_report_guide.md<br>.claude/skills/dr-synth/SKILL.md | `@eb565f44` |
| `experiment-id-numbering` | 実験IDの番号は採番済みの最大+1(テンプレをコピーする前に experiments/ を見る) | AGENTS.md「実験 ID と 命名規約」 | .claude/skills/exp-new/SKILL.md | `@df108c26` |
| `frontmatter-schema` | REPORT.md / 一次記録の YAML フロントマター書式(実行時強制: tools/report_meta.py (schema errors fail --check)) | .claude/skills/exp-report/references/exp_report_guide.md「フロントマター」 | AGENTS.md | `@6e2e1a63` |
| `living-vs-primary` | リビング文書 vs 一次記録(1機能=1権威) | docs/conventions/reporting.md | AGENTS.md<br>docs/conventions/research.md<br>.claude/skills/dr-plan/SKILL.md | `@134848f4` |
| `central-todo-scope` | 中央 tasks/TODO.md はマネジメント観点+リポ運営専用(実験の詳細は PLAN/REPORT が正本) | docs/conventions/reporting.md「次の一手の正本」 | — | `@f008b168` |
| `lab-log-format` | 日次ログの置き場と4見出し(目的/やったこと/わかったこと/次にやること) | docs/conventions/repository-rules.md「ログの書式」 | .claude/skills/lab-log/SKILL.md<br>README.md<br>.claude/skills/exp-checkpoint/references/checkpoint_procedure.md | `@a0eca25e` |
| `nb-strip-outputs` | Notebook はセル出力をクリアして保存する(実行時強制: .gitattributes nbstrip filter + tools/strip_nb_outputs.py --check) | docs/conventions/repository-rules.md「Notebook 規約」 | .claude/skills/exp-new/SKILL.md | `@3ca1441e` |
| `kb-promotion` | 確定恒久知識だけ KB へ昇格し REPORT からリンクする | AGENTS.md「知見の昇格(tips → KB)」 | README.md | `@d1b964ea` |
| `dr-gate-opt-in` | 台帳を作った実験は .dr-gate で commit 時検証ゲートに opt-in し、判断駆動数値は執筆時に claim マーカで台帳に紐づける(実行時強制: tools/dr/dr_gate_precommit.py (pre-commit; fires only for opted-in experiments)) | docs/conventions/reporting.md「検証ゲート(.dr-gate)と claim マーカ」 | .claude/skills/dr-audit/references/dr_audit_protocol.md<br>docs/conventions/research.md<br>.claude/skills/dr-plan/SKILL.md<br>.claude/skills/dr-collect/SKILL.md<br>.claude/skills/dr-synth/SKILL.md | `@fd4434e1` |
| `verify-before-sharing` | 検証は平場でなく「外に出す直前」と「まとめとして固定する瞬間」に行う(共有前ゲート)(実行時強制: —(手順。機械強制はしない — 対象は成果物ごとに変わるため)) | docs/conventions/reporting.md「いつ検証するか — 共有前ゲート」 | docs/conventions/research.md | `@38a1a7de` |
| `retraction-record` | 撤回は機械可読に記録する(旧版 superseded_by 必須 / 新版 corrects・retraction_type・discovered_by)(実行時強制: tools/report_meta.py (link resolvability + vocabulary; pre-commit)) | docs/conventions/reporting.md「改訂・撤回の記録」 | .claude/skills/exp-report/SKILL.md<br>.claude/skills/exp-checkpoint/SKILL.md | `@b39a00ca` |
| `new-term-referent-first` | 新語(造語)は初出定義+役割1つで導入する(語より先に指示対象; 検査は readability-review、定着語は terms.yaml へ昇格) | docs/conventions/reporting.md「新語(造語)の導入規律」 | .claude/skills/readability-review/SKILL.md | `@8b08bf1b` |
| `report-input-pinning` | データ由来のレポートは入力(データ/仕様)をピン留めする(再現性・検算の前提) | docs/conventions/reporting.md「データ由来の数値は入力をピン留めする」 | .claude/skills/report-checksum/SKILL.md | `@b32fc5e6` |
| `research-question-closing` | 調査の下位問いは決着条件を先に書く(書けない問いは分解し直す)(実行時強制: tools/dr/dr_coverage.py (K1)) | docs/conventions/research.md「下位問いと決着条件」 | .claude/skills/dr-plan/SKILL.md | `@64ec663f` |
| `source-tier-independence` | 出典は格付けし、孫引きを畳んでから独立本数を数える(vendor 単独で閉じない)(実行時強制: tools/dr/dr_coverage.py (K2)) | docs/conventions/research.md「出典の格付けと独立性」 | .claude/skills/dr-collect/SKILL.md | `@e6b3fc5c` |
| `refutation-search-record` | 反証探索は台帳に記録する(探して見つからなかったことを成果として残す)(実行時強制: tools/dr/dr_coverage.py (K3)) | docs/conventions/research.md「反証探索を記録する」 | .claude/skills/dr-collect/SKILL.md | `@e752a626` |
| `ledger-before-prose` | 調査は台帳を先に埋め、散文は台帳から導出する(事後の書き起こしにしない) | docs/conventions/research.md「台帳を先に作る(散文は台帳から導出する)」 | .claude/skills/dr-collect/SKILL.md | `@deb0a7fb` |
| `dr-coverage-gate` | 調査は網羅ゲート(dr_coverage.py)を受入ゲートより先に通す(実行時強制: tools/dr/dr_coverage.py) | docs/conventions/research.md「網羅ゲート」 | .claude/skills/dr-synth/SKILL.md | `@111ff218` |

<!-- gen:policy-map:end -->
