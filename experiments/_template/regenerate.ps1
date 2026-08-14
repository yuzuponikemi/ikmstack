#!/usr/bin/env pwsh
# <実験名> — 図・自動レポートの一括再生成
#
# 方針(AGENTS.md 三大原則#1): git には「テキスト + 生成スクリプト」だけを置き、図はコミットしない。
# 図付きレポートを読みたい人は、Drive を同期してこのスクリプトを1回流せばローカルで再現できる。
#
#   入力 : Drive 正本の生データ(R1: PC 固有ローカルパスを入力にしない。差はドライブレターのみ)
#   出力 : _generated/(plots_*/ と自動生成 .md。.gitignore 済 = ローカル専用)(R2: 出力先は1つに揃える)
#   使い方: pwsh experiments/E###_<topic>/regenerate.ps1
#           別ドライブ: pwsh ... regenerate.ps1 -DriveRoot 'H:\Shared drives\...\<notebook>'
#           生成後、reports/ 内の .md を開けば図付きでプレビューできる(図は ../_generated/)。
#           共有用の完成版(図付き)は exp-deck / Drive へ。
param(
    # Drive 上のノートのルート。既定は共有ドライブの正準パス。env LAB_DRIVE でも上書き可。
    [string]$DriveRoot = $(if ($env:LAB_DRIVE) { $env:LAB_DRIVE } else {
        'G:\Shared drives\YourCompany\ExperimentData\<notebook>' })
)

$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot
$env:MPLBACKEND = 'Agg'   # 図はファイル保存のみ(ウィンドウを開かない)

# --- 入力 = Drive 正本(R1)----------------------------------------------------
# この実験の生データが Drive のどこにあるかに合わせて書き換える(MANIFEST.md「データの所在」)。
# 例: 実験フォルダ直下 raw を読む場合 ↓。共有データセットなら shared-datasets\... を指す。
$dataRoot = Join-Path $DriveRoot 'experiments\<id>\raw'
if (-not (Test-Path $dataRoot)) {
    Write-Error "生データ $dataRoot が無い。Drive を同期、別レターなら -DriveRoot 指定(MANIFEST.md)。"; exit 1
}
# スクリプトに渡す(各 scripts/*.py は環境変数 or 引数でこの入力を受ける。ローカルパス直書き禁止)。
$env:EXP_DATA_ROOT = $dataRoot
Write-Host "入力: $dataRoot" -ForegroundColor DarkGray

# --- 図/レポートを生成するスクリプトを順に実行(出力先は _generated/ に揃える)(R2)---------
$scripts = Get-ChildItem -Path 'scripts' -Filter '*.py' | Sort-Object Name

$ok = @(); $fail = @(); $skipped = @()
foreach ($s in $scripts) {
    Write-Host ("▶ {0}" -f $s.Name) -ForegroundColor DarkCyan
    python -X utf8 ("scripts/{0}" -f $s.Name)
    # exit 2 = SKIP: 入力が未取得(事前登録・測定進行中)。本物の失敗と区別する(AGENTS.md R1)。
    # 事前登録解析は、データ欠如時に exit 1(fail) ではなく exit 2(skip) を返すこと。
    if ($LASTEXITCODE -eq 0) { $ok += $s.Name }
    elseif ($LASTEXITCODE -eq 2) { $skipped += $s.Name }
    else { $fail += $s.Name }
}

Write-Host ""
Write-Host ("=== 完了: 成功 {0} / スキップ {1} / 失敗 {2} ===" -f $ok.Count, $skipped.Count, $fail.Count) -ForegroundColor Green
if ($skipped.Count) { Write-Host ("スキップ(データ未取得・事前登録): {0}" -f ($skipped -join ', ')) -ForegroundColor DarkGray }
if ($fail.Count) { Write-Host ("失敗(要調査): {0}" -f ($fail -join ', ')) -ForegroundColor Yellow }
Write-Host "プレビュー: reports/ の .md を開く(図は ../_generated/plots_*/ に再生成済)"
