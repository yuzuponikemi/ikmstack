#!/bin/sh
# <experiment> -- regenerate figures and auto-generated reports.
#
# Policy (AGENTS.md principle #1): git carries text + generator scripts only, never
# figures. Anyone who wants to read a report with its figures syncs the Drive and
# runs this once to reproduce them locally.
#
#   input  : raw data on the Drive (R1: never take a machine-local path as the
#            source of truth; the only per-machine difference is the mount point)
#   output : _generated/ (plots_*/ and generated .md, gitignored = local only)
#            (R2: keep every output under a single root)
#   usage  : sh experiments/E###_<topic>/regenerate.sh
#            other mount: LAB_DRIVE='/path/to/shared drive/<notebook>' sh .../regenerate.sh
#            afterwards, open a .md under reports/ to preview it with figures
#            (they live in ../_generated/). Share the finished deck via exp-deck.
#
# Exit codes: 0 = every script succeeded or skipped / 1 = at least one failed.
set -u

# --- Drive root --------------------------------------------------------------
# On macOS, Google Drive for desktop mounts at
#   ~/Library/CloudStorage/GoogleDrive-<account>/My Drive/...
# The folder is literally named "My Drive" even on a Japanese system. Workspace
# accounts also get "Shared drives/<drive>/...". Put the real path in
# .lab-config.json (google_drive_root) and override here with $LAB_DRIVE.
# NOTE: the path contains a space -- keep every expansion quoted.
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$script_dir" || exit 1
export MPLBACKEND=Agg   # write figures to files only; never open a window

# Resolved in this order so nothing has to be hand-edited per experiment:
#   1. $LAB_DRIVE                      (per-machine override)
#   2. google_drive_root in the notebook's .lab-config.json  (the single source)
#   3. a placeholder that fails loudly (never silently guesses a path)
# Hardcoding the path here is what left E003/E004 shipping "<account>" forever:
# regenerate.sh only ever ran with LAB_DRIVE set, so the broken default was invisible.
DRIVE_ROOT="${LAB_DRIVE:-}"
if [ -z "$DRIVE_ROOT" ]; then
  # Relative to THIS script, not to the caller's cwd: regenerate.sh is run from
  # the notebook root as often as from the experiment directory.
  for cfg in "$script_dir/../../.lab-config.json" "$script_dir/../.lab-config.json"; do
    [ -f "$cfg" ] || continue
    DRIVE_ROOT=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
r=(d.get('google_drive_root') or '').rstrip('/')
# google_drive_root points at .../experiments; this script appends its own
# 'experiments/<id>' below, so hand back the level above it.
print(r[:-len('/experiments')] if r.endswith('/experiments') else r)
" "$cfg" 2>/dev/null)
    [ -n "$DRIVE_ROOT" ] && break
  done
fi
if [ -z "$DRIVE_ROOT" ]; then
  echo "Drive root unknown: set \$LAB_DRIVE, or put google_drive_root in .lab-config.json." >&2
  exit 1
fi


# --- input = the Drive (R1) --------------------------------------------------
# Point this at wherever this experiment's raw data lives (MANIFEST.md records it).
DATA_ROOT="$DRIVE_ROOT/experiments/<id>/raw"
if [ ! -d "$DATA_ROOT" ]; then
  echo "raw data not found: $DATA_ROOT" >&2
  echo "Sync the Drive, or set LAB_DRIVE to your mount point (see MANIFEST.md)." >&2
  exit 1
fi
# Hand it to the scripts. Each scripts/*.py reads this env var; none of them may
# hardcode a local path.
export EXP_DATA_ROOT="$DATA_ROOT"
echo "input: $DATA_ROOT"

# --- run every generator, all output under _generated/ (R2) ------------------
n_ok=0
n_skipped=0
n_failed=0
ok_list=''
skipped_list=''
failed_list=''
n_seen=0

for script in scripts/*.py; do
  [ -e "$script" ] || continue          # unmatched glob passes the pattern through
  n_seen=$((n_seen + 1))
  name=$(basename "$script")
  echo "> $name"
  python3 -X utf8 "$script"
  # Note: `status` is read-only in zsh, so this variable must not be named that.
  rc=$?
  # exit 2 = SKIP: the input is not collected yet (pre-registration, measurement
  # still running). Keep it distinct from a real failure (AGENTS.md R1).
  if [ "$rc" -eq 0 ]; then
    n_ok=$((n_ok + 1)); ok_list="$ok_list $name"
  elif [ "$rc" -eq 2 ]; then
    n_skipped=$((n_skipped + 1)); skipped_list="$skipped_list $name"
  else
    n_failed=$((n_failed + 1)); failed_list="$failed_list $name"
  fi
done

if [ "$n_seen" -eq 0 ]; then
  echo "warning: no scripts/*.py found under $script_dir -- nothing to regenerate." >&2
fi

echo
echo "=== done: ok $n_ok / skipped $n_skipped / failed $n_failed ==="
if [ "$n_skipped" -gt 0 ]; then
  echo "skipped (input not collected yet):$skipped_list"
fi
if [ "$n_failed" -gt 0 ]; then
  echo "failed (needs investigation):$failed_list" >&2
fi

# --- follow up with the HTML read view -- must run after the figures exist ---
# Skipped (exit 0) when mistune is absent; it must not fail the regeneration.
if [ -f ../../tools/gen_readview.py ]; then
  python3 ../../tools/gen_readview.py .
fi

echo "preview: open a .md under reports/ (figures are in ../_generated/plots_*/)"

# Surface a real failure to the caller (/regen-outputs, CI). Skips are not failures.
[ "$n_failed" -eq 0 ] || exit 1
exit 0
