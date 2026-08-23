---
name: dr-synth
description: Turn the filled research ledgers into a reasoned report — generate the skeleton from questions/sources/claims, write the argument in the order conclusion→grounds→confidence→counter-evidence→open questions, then clear both gates (coverage first, then source verification). This is the write-up half of deep research, not a memo dump. Use when the collection is done and the investigation must become a coherent report ("調査をレポートにまとめて", "論証を組み立てて", "調査結果を整理して", "確度と反証も入れて書いて").
---

# dr-synth — 台帳から論証を組み、散文にする

`/dr-collect` で埋まった3台帳を、**理路の通ったレポート**にする。
メモの寄せ集めと分けるのは、**主張の順序**(結論を先に、根拠を後に)と
**確度・反証・未決着を必ず持つこと**の2点。

## Step 0: 作業ディレクトリとツールを解決(必須)

```bash
cd "$(python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" notebook)"
DR="$(cat ~/.ikmstack/install-path)/tools/dr"
```

詳細は [記録のルーティング規約](../../../docs/conventions/record-routing.md)。
以下 `<exp>` は実験ディレクトリ。

## 手順

### 1. 骨組みを台帳から生成する(手で組み立てない)

```bash
python3 "$DR/dr_outline.py" <exp>/reports/questions.jsonl
```

下位問いごとに「答え・確度・支持/反証の内訳・独立ソース・探したが採らなかったもの」が出る。
**これが散文の素材**で、ここに無いことは書かない(台帳に無い主張を散文で生やさない)。
骨組みは生成物なのでファイルに残さなくてよい(残すなら `_generated/` 配下)。

### 2. 論証の順序を決める

節の順序は固定する。読み手が「結論 → なぜそう言えるか → どれだけ確かか」の順で読めるようにする:

1. **問いと結論** — 主問いを再掲し、答えを先に書く。下位問いごとの答えを1行ずつ。
2. **根拠** — 下位問いごとに、判断駆動の主張と出典。`(claim:cNNN)` マーカを打つ。
3. **確度** — `confidence` を根拠つきで書く。`low`/`medium` を `high` に化粧しない。
4. **反証・留保** — `stance: refutes` / `neutral` の主張をここで扱う。
   **反証を脚注に追いやらない** — 独立した節に置く。
5. **未決着(open question)** — `open` / `abandoned` の下位問いを **ID つきで**書く。
   打ち切りは「決着」と書かず、打ち切った理由(`note`)を書く。
6. **探索範囲** — 何を探して採らなかったか(骨組みの「探したが採らなかったもの」)。
   これが「調べていない」と「調べたが無かった」を読み手に区別させる唯一の材料。

### 3. 書く(house style は既存規約に従う)

- **事実と仮説を混ぜない。** 語頭ラベル(「**確定:**」「**仮説:**」「**要確認:**」)で切り分ける。
  正本: [reporting.md](../../../docs/conventions/reporting.md)「事実と仮説を分ける」
- **判断駆動の数値には `(claim:cNNN)` を執筆時に打つ。** 台帳が先にあるのでコストはほぼゼロ。
  <!-- policy:dr-gate-opt-in@fd4434e1 -->
- **1本で自走的に読めるように書く。** 略語は初出でフルスペル、前提の再共有は「重複」ではない。
  長さの上限は無い。量が増えたら話題ごとに1レポートへ分ける。
- ファイル名は `<exp>/reports/E###-R###_<YYYYMMDD>_<topic>_調査.md`。
  R 番号は `reports/INDEX.md` の最大 R+1。**リビング文書(`REPORT.md` 等)には R を振らない。**
  <!-- policy:report-naming-numbering@eb565f44 -->
- 書式・フロントマターの詳細は `/exp-report` の作法に従う。

### 4. 2つのゲートを順に通す(順序を守る)

```bash
# ① 網羅ゲート — 書かなかったことの穴(先にこちら)
python3 "$DR/dr_coverage.py" <exp>/reports/questions.jsonl --prose <exp>/reports/<レポート>.md

# ② 受入ゲート — 書いた数値の正しさ
python3 "$DR/dr_gate.py" <exp>/reports/claims.jsonl
```

**網羅ゲートを先に通す。** 穴だらけの調査の数値を出典照合しても、
「正しく引用された不完全な結論」になるだけで、費用の掛けどころを間違える。
<!-- policy:dr-coverage-gate@111ff218 -->

K5 が FAIL したら、未決着の問いを **ID つきで**散文に書く(手順2の節5)。
② が FAIL したら、出典の再取得を含むフル検証は `/dr-audit` を回す。

### 5. REPORT.md と INDEX を最新化する

- `REPORT.md`(現状サマリ = 最初に読む唯一の権威)に結論と open question を反映する。
  詳細な根拠は一次記録側に置き、`REPORT.md` は1本に保つ。
- フロントマターを書いて INDEX を再生成する:
  ```bash
  python3 tools/report_meta.py
  ```
  <!-- policy:report-meta-regen@a43c35f7 -->

### 6. 自走性をレビューする(任意だが推奨)

`/readability-review` を回す。調査レポートは外部の固有名詞・専門用語が多く、
自走性が落ちやすい。

## 完了条件

- `dr_coverage.py`(`--prose` つき)が PASS
- `dr_gate.py` が PASS(または判断駆動の未検証が `/dr-audit` 待ちだと明記されている)
- 散文に確度・反証・未決着・探索範囲の節がある
- `REPORT.md` と `reports/INDEX.md` が最新
