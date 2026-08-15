---
# jira: Project-### (Optional, if enabled in config)
experiment_id: E###_<topic>
status: planning          # planning | active | done | paused
period_start: YYYY-MM-DD
period_end:               # 空=継続中(INDEX で "〜" 表示)
summary: 一行要約(experiments/INDEX.md の1行要約に流用される)
---

# レポート: <topic>(現状サマリ)

> この REPORT.md は実験の**現状サマリ＝最初に読む唯一の権威**(リビング文書)。
> 確定事実・現在の結論・未解決を簡潔に保ち、覆った結論は残さない。
> 個別の根拠・数値・図表は一次記録 `reports/E###-R###_<日付>_*.md` を、
> 方針転換の履歴は(長期campaignなら)`DECISIONS.md` を参照。全一覧は `reports/INDEX.md`。
> (1〜2 セッションで終わる小さな検証なら reports/ を作らずこのファイル単体でよい。)
>
> 冒頭の YAML フロントマターが**メタデータの正本**。`experiments/INDEX.md` の行は
> `python3 tools/report_meta.py` がここから生成する(本文に Jira/状態/期間を再掲しない)。

- **結論(1 行)**:

## 結果(確定事実)

確定した結論のみ。各根拠は一次記録へリンクする。
例: 観測 X は `reports/E###-R###_YYYYMMDD_<topic>.md` で確定。
**確定事実と仮説を混ぜない**(仮説・暫定値は下の「考察」へ。語頭に `仮説:` / `暫定:` を付ける)。

## 考察(解釈・仮説)

仮説は支持されたか。意外だった点。限界・注意点。ここは解釈であり確定事実と区別する。

## 次のアクション

- [ ]

## ナレッジベースへの昇格

恒久知識になった内容と昇格先(なければ「なし」と明記):

- 例: Shared_KB `docs2/troubleshooting/xxx.md`(PR #NN)
