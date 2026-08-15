#!/bin/sh
# <実験名> — 図・自動レポートの一括再生成
#
# 方針(AGENTS.md 三大原則#1): git には「テキスト + 生成スクリプト」だけを置き、図はコミットしない。
# 図付きレポートを読みたい人は、Drive を同期してこのスクリプトを1回流せばローカルで再現できる。
#
#   入力 : Drive 正本の生データ(R1: PC 固有ローカルパスを入力にしない。差は Drive のマウント先だけ)
#   出力 : _generated/(plots_*/ と自動生成 .md。.gitignore 済 = ローカル専用)(R2: 出力先は1つに揃える)
#   使い方: sh experiments/E###_<topic>/regenerate.sh
#           別マウント: LAB_DRIVE='/path/to/共有ドライブ/<notebook>' sh .../regenerate.sh
#           生成後、reports/ 内の .md を開けば図付きでプレビューできる(図は ../_generated/)。
#           共有用の完成版(図付き)は exp-deck / Drive へ。
set -u

# --- Drive のルート ----------------------------------------------------------
# macOS の Google Drive (Drive for desktop) は既定でここにマウントされる:
#   ~/Library/CloudStorage/GoogleDrive-<アカウント>/共有ドライブ/<ドライブ名>/...
# 旧クライアントや別構成なら /Volumes/GoogleDrive/... のこともある。
# 実際のパスは .lab-config.json の google_drive_root に書き、ここは env で上書きする。
DRIVE_ROOT="${LAB_DRIVE:-$HOME/Library/CloudStorage/GoogleDrive-<account>/共有ドライブ/<drive>/<notebook>}"

cd "$(dirname "$0")" || exit 1
export MPLBACKEND=Agg   # 図はファイル保存のみ(ウィンドウを開かない)

# --- 入力 = Drive 正本(R1)----------------------------------------------------
# この実験の生データが Drive のどこにあるかに合わせて書き換える(MANIFEST.md「データの所在」)。
# 例: 実験フォルダ直下 raw を読む場合 ↓。共有データセットなら shared-datasets/... を指す。
DATA_ROOT="$DRIVE_ROOT/experiments/<id>/raw"
if [ ! -d "$DATA_ROOT" ]; then
  echo "生データ $DATA_ROOT が無い。Drive を同期、別マウントなら LAB_DRIVE を指定(MANIFEST.md)。" >&2
  exit 1
fi
# スクリプトに渡す(各 scripts/*.py は環境変数 or 引数でこの入力を受ける。ローカルパス直書き禁止)。
export EXP_DATA_ROOT="$DATA_ROOT"
echo "入力: $DATA_ROOT"

# --- 図/レポートを生成するスクリプトを順に実行(出力先は _generated/ に揃える)(R2)---------
ok=0; skipped=0; failed=0
ok_list=''; skipped_list=''; failed_list=''

for s in scripts/*.py; do
  [ -e "$s" ] || continue          # マッチ無しのときの glob 素通りを弾く
  name="$(basename "$s")"
  echo "▶ $name"
  python3 -X utf8 "$s"
  status=$?
  # exit 2 = SKIP: 入力が未取得(事前登録・測定進行中)。本物の失敗と区別する(AGENTS.md R1)。
  # 事前登録解析は、データ欠如時に exit 1(fail) ではなく exit 2(skip) を返すこと。
  if [ "$status" -eq 0 ]; then
    ok=$((ok + 1)); ok_list="$ok_list $name"
  elif [ "$status" -eq 2 ]; then
    skipped=$((skipped + 1)); skipped_list="$skipped_list $name"
  else
    failed=$((failed + 1)); failed_list="$failed_list $name"
  fi
done

echo
echo "=== 完了: 成功 $ok / スキップ $skipped / 失敗 $failed ==="
[ "$skipped" -gt 0 ] && echo "スキップ(データ未取得・事前登録):$skipped_list"
[ "$failed" -gt 0 ] && echo "失敗(要調査):$failed_list"

# --- 読みビュー(HTML)を追随生成 — 図の再生成後に呼ぶこと ---------------------
# mistune 未導入ならスキップ扱い(図・レポート本体には影響しない)。
if [ -f ../../tools/gen_readview.py ]; then
  python3 ../../tools/gen_readview.py .
fi

echo "プレビュー: reports/ の .md を開く(図は ../_generated/plots_*/ に再生成済)"
